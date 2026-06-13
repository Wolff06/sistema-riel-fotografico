# -*- coding: utf-8 -*-
# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/raspberry/firebase/firebase_gateway.py
#
# OBJETIVO:
# Escuchar los datos reales publicados por MQTT y guardarlos en Firebase
# Firestore con timestamp, sin modificar la logica actual del ESP32, la IA ni
# la interfaz. Este puente se ejecuta aparte y solo registra datos cuando esta
# activo.

# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# PRIVACIDAD:
# No sube fotografias ni video a Firebase. Solo guarda metadatos: lectura IA,
# clase, confianza, sensores, estado del sistema y comandos de actuadores.
# =============================================================================

import json
import os
import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    firebase_admin = None
    credentials = None
    firestore = None


# =============================================================================
# CONFIGURACION GENERAL
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BROKER_HOST = os.environ.get("CANMA_MQTT_HOST", "192.168.4.1")
BROKER_PORT = int(os.environ.get("CANMA_MQTT_PORT", "1884"))
BROKER_USER = os.environ.get("CANMA_MQTT_USER", "admin")
BROKER_PASS = os.environ.get("CANMA_MQTT_PASS", "123")

# Ruta recomendada para la llave de servicio. No se debe subir a GitHub.
RUTA_CREDENCIAL_FIREBASE = os.environ.get(
    "CANMA_FIREBASE_CRED",
    os.path.join(BASE_DIR, "credenciales", "firebase_key.json")
)

# Para cuidar creditos, el estado actual se escribe como maximo cada N segundos.
# Para demostracion puede usarse 5 o 10. Para uso continuo se recomienda 30.
INTERVALO_ESTADO_SEGUNDOS = int(os.environ.get("CANMA_FIREBASE_INTERVALO_ESTADO", "30"))

# La deteccion IA historica se guarda como maximo una vez por hora.
INTERVALO_IA_HISTORICO_SEGUNDOS = int(os.environ.get("CANMA_FIREBASE_INTERVALO_IA", "3600"))

# La foto/video no se sube. Este valor se deja fijo para evidenciar privacidad.
SUBIR_IMAGENES_FIREBASE = False


# =============================================================================
# TOPICOS MQTT DEL PROYECTO
# =============================================================================

T_SISTEMA_ESTADO = "sistema/estado"
T_SISTEMA_ERROR = "sistema/error"

T_SENSOR_PIR = "sistema/sensores/pir"
T_SENSOR_ULTRASONICO = "sistema/sensores/ultrasonico"
T_SENSOR_JOYSTICK_BASE = "sistema/sensores/joystick_base"
T_SENSOR_DIRECCION_BASE = "sistema/sensores/direccion_base"

T_ACTUADOR_BASE_GRADOS = "sistema/actuadores/base/grados"
T_ACTUADOR_BRAZO_GRADOS = "sistema/actuadores/brazo/grados"

T_IA_RESULTADO = "sistema/ia/resultado"
T_ALERTA_ULTIMA = "sistema/alertas/ultima"

T_CMD_INICIAR_OP = "sistema/cmd/iniciar"
T_CMD_BASE_MOVER = "sistema/cmd/base/mover"
T_CMD_BRAZO_MOVER = "sistema/cmd/brazo/mover"
T_CMD_SEGURO = "sistema/cmd/seguro"
T_CMD_MODO_SISTEMA = "sistema/cmd/modo"
T_CMD_IA_ESTADO = "sistema/cmd/ia/estado"

# Topico opcional para guardar manualmente la ultima deteccion IA.
T_CMD_FIREBASE_GUARDAR_IA = "sistema/cmd/firebase/guardar_ia"

TOPICOS_SUSCRIPCION = [
    T_SISTEMA_ESTADO,
    T_SISTEMA_ERROR,
    T_SENSOR_PIR,
    T_SENSOR_ULTRASONICO,
    T_SENSOR_JOYSTICK_BASE,
    T_SENSOR_DIRECCION_BASE,
    T_ACTUADOR_BASE_GRADOS,
    T_ACTUADOR_BRAZO_GRADOS,
    T_IA_RESULTADO,
    T_ALERTA_ULTIMA,
    T_CMD_INICIAR_OP,
    T_CMD_BASE_MOVER,
    T_CMD_BRAZO_MOVER,
    T_CMD_SEGURO,
    T_CMD_MODO_SISTEMA,
    T_CMD_IA_ESTADO,
    T_CMD_FIREBASE_GUARDAR_IA,
]


# =============================================================================
# ESTADO EN MEMORIA
# =============================================================================

estado_actual = {
    "sistema": "Sin conexion",
    "error": None,
    "sensores": {
        "pir": None,
        "ultrasonico_cm": None,
        "joystick_base": None,
        "direccion_base": "CENTRO",
    },
    "actuadores": {
        "base_grados": None,
        "brazo_grados": None,
    },
    "ia": {
        "estado_ia": "apagada",
        "lectura": "sin_lectura",
        "clase": "Sin lectura",
        "confianza": 0,
        "alerta": False,
        "timestamp": None,
    },
    "alerta_ultima": "Sin alertas",
    "privacidad": {
        "imagenes_en_firebase": False,
        "nota": "Solo se guardan metadatos; no se almacenan imagenes identificables.",
    },
}

ultima_escritura_estado = 0
ultimo_guardado_ia = 0
ultimo_snapshot_sensores = 0
ultima_alerta_texto = None

cliente_firestore = None
cliente_mqtt = None


# =============================================================================
# UTILIDADES
# =============================================================================

def ahora_iso():
    """
    Recibe:
        Nada.

    Hace:
        Genera fecha y hora local en formato ISO.

    Devuelve:
        Cadena con fecha y hora local.
    """

    return datetime.now().isoformat(timespec="seconds")


def convertir_numero(valor):
    """
    Recibe:
        valor: texto o numero recibido por MQTT.

    Hace:
        Intenta convertir el dato a numero flotante.

    Devuelve:
        Numero flotante o None si no se puede convertir.
    """

    try:
        texto = str(valor).strip()
        if texto.lower() in ("", "none", "null"):
            return None
        return float(texto)
    except Exception:
        return None


def convertir_booleano(valor):
    """
    Recibe:
        valor: texto, numero o booleano recibido por MQTT.

    Hace:
        Interpreta valores comunes de verdadero/falso.

    Devuelve:
        True, False o el valor original si no se puede interpretar.
    """

    if isinstance(valor, bool):
        return valor

    texto = str(valor).strip().lower()
    if texto in ("true", "1", "si", "sí", "on", "presencia", "detectado"):
        return True
    if texto in ("false", "0", "no", "off", "sin_presencia"):
        return False

    return valor


def parsear_json_seguro(texto):
    """
    Recibe:
        texto: mensaje MQTT en formato texto.

    Hace:
        Intenta leer el texto como JSON.

    Devuelve:
        Diccionario si el texto es JSON valido; None en caso contrario.
    """

    try:
        datos = json.loads(texto)
        if isinstance(datos, dict):
            return datos
    except Exception:
        pass

    return None


def inicializar_firebase():
    """
    Recibe:
        Nada.

    Hace:
        Inicializa firebase-admin con una llave de servicio local.

    Devuelve:
        Cliente de Firestore.
    """

    if firebase_admin is None:
        raise ImportError("Falta firebase-admin. Instala con: python3 -m pip install firebase-admin")

    if not os.path.exists(RUTA_CREDENCIAL_FIREBASE):
        raise FileNotFoundError(
            "No se encontro la credencial Firebase en: {}\n"
            "Coloca tu archivo firebase_key.json ahi o define CANMA_FIREBASE_CRED.".format(
                RUTA_CREDENCIAL_FIREBASE
            )
        )

    if not firebase_admin._apps:
        credencial = credentials.Certificate(RUTA_CREDENCIAL_FIREBASE)
        firebase_admin.initialize_app(credencial)

    return firestore.client()


def crear_cliente_mqtt():
    """
    Recibe:
        Nada.

    Hace:
        Crea un cliente MQTT compatible con versiones nuevas y antiguas de paho.

    Devuelve:
        Cliente MQTT configurado.
    """

    if mqtt is None:
        raise ImportError("Falta paho-mqtt. Instala con: python3 -m pip install paho-mqtt")

    try:
        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id="canma_firebase_gateway"
        )
    except Exception:
        cliente = mqtt.Client(client_id="canma_firebase_gateway")

    if BROKER_USER:
        cliente.username_pw_set(BROKER_USER, BROKER_PASS)

    cliente.on_connect = on_connect
    cliente.on_message = on_message
    return cliente


# =============================================================================
# ESCRITURAS EN FIRESTORE
# =============================================================================

def escribir_estado_actual(forzar=False):
    """
    Recibe:
        forzar: True para escribir aunque no haya pasado el intervalo.

    Hace:
        Guarda un unico documento con el estado actual del sistema. Esto permite
        monitoreo en tiempo real sin crear miles de documentos.

    Devuelve:
        True si se escribio en Firestore; False si se omitio por ahorro.
    """

    global ultima_escritura_estado

    if cliente_firestore is None:
        return False

    ahora = time.time()
    if not forzar and ahora - ultima_escritura_estado < INTERVALO_ESTADO_SEGUNDOS:
        return False

    payload = dict(estado_actual)
    payload["timestamp_local"] = ahora_iso()
    payload["timestamp_servidor"] = firestore.SERVER_TIMESTAMP

    cliente_firestore.collection("estado_actual").document("sistema").set(payload, merge=True)
    ultima_escritura_estado = ahora
    print("Firebase estado_actual/sistema actualizado")
    return True


def registrar_evento(tipo, datos=None, forzar=False):
    """
    Recibe:
        tipo: nombre del tipo de evento.
        datos: informacion adicional del evento.
        forzar: reservado para compatibilidad; permite distinguir guardados manuales.

    Hace:
        Crea un documento historico en la coleccion eventos.

    Devuelve:
        ID del documento creado o None si no se pudo guardar.
    """

    if cliente_firestore is None:
        return None

    if datos is None:
        datos = {}

    documento = {
        "tipo": tipo,
        "datos": datos,
        "forzado": bool(forzar),
        "timestamp_local": ahora_iso(),
        "timestamp_servidor": firestore.SERVER_TIMESTAMP,
        "privacidad": "No contiene imagenes ni video; solo metadatos.",
    }

    referencia = cliente_firestore.collection("eventos").add(documento)
    print("Firebase evento registrado:", tipo)
    return referencia


def registrar_alerta(texto, datos=None):
    """
    Recibe:
        texto: descripcion de la alerta.
        datos: datos complementarios, por ejemplo resultado IA.

    Hace:
        Guarda una alerta en la coleccion alertas para mostrar las ultimas 5.

    Devuelve:
        Nada.
    """

    if cliente_firestore is None:
        return

    if datos is None:
        datos = {}

    documento = {
        "mensaje": str(texto),
        "datos": datos,
        "timestamp_local": ahora_iso(),
        "timestamp_servidor": firestore.SERVER_TIMESTAMP,
        "privacidad": "No contiene imagenes ni video; solo metadatos.",
    }

    cliente_firestore.collection("alertas").add(documento)
    print("Firebase alerta registrada:", texto)


def guardar_ia_historica(forzar=False):
    """
    Recibe:
        forzar: True para guardar manualmente aunque no haya pasado una hora.

    Hace:
        Guarda el ultimo resultado de IA como evento historico. Por defecto se
        limita a una vez por hora para cuidar las escrituras gratuitas.

    Devuelve:
        True si guardo el evento; False si lo omitio por ahorro.
    """

    global ultimo_guardado_ia

    ahora = time.time()
    if not forzar and ahora - ultimo_guardado_ia < INTERVALO_IA_HISTORICO_SEGUNDOS:
        return False

    datos_ia = estado_actual.get("ia", {})
    registrar_evento("ia_resultado", datos_ia, forzar=forzar)
    ultimo_guardado_ia = ahora
    return True


def guardar_snapshot_sensores(forzar=False):
    """
    Recibe:
        forzar: True para guardar manualmente aunque no haya pasado una hora.

    Hace:
        Guarda una fotografia de datos, no de imagen: sensores, actuadores,
        estado general e IA.

    Devuelve:
        True si guardo el evento; False si lo omitio por ahorro.
    """

    global ultimo_snapshot_sensores

    ahora = time.time()
    if not forzar and ahora - ultimo_snapshot_sensores < 3600:
        return False

    datos = {
        "sistema": estado_actual.get("sistema"),
        "sensores": estado_actual.get("sensores", {}),
        "actuadores": estado_actual.get("actuadores", {}),
        "ia": estado_actual.get("ia", {}),
    }
    registrar_evento("snapshot_sensores", datos, forzar=forzar)
    ultimo_snapshot_sensores = ahora
    return True


# =============================================================================
# MQTT
# =============================================================================

def on_connect(client, userdata, flags, rc):
    """
    Recibe:
        client, userdata, flags, rc: parametros del callback MQTT.

    Hace:
        Suscribe el gateway a topicos reales del proyecto.

    Devuelve:
        Nada.
    """

    if rc == 0:
        print("Gateway Firebase conectado a Mosquitto")
        for topico in TOPICOS_SUSCRIPCION:
            client.subscribe(topico)
            print("Suscrito a:", topico)
        escribir_estado_actual(forzar=True)
    else:
        print("Error conectando Gateway Firebase a MQTT. Codigo:", rc)


def on_message(client, userdata, msg):
    """
    Recibe:
        client, userdata, msg: mensaje MQTT recibido.

    Hace:
        Actualiza el estado en memoria y registra eventos seleccionados en
        Firebase sin modificar la logica existente del sistema.

    Devuelve:
        Nada.
    """

    global ultima_alerta_texto

    topico = msg.topic
    try:
        mensaje = msg.payload.decode("utf-8")
    except Exception:
        mensaje = str(msg.payload)

    print("MQTT -> Firebase:", topico, mensaje)

    if topico == T_SISTEMA_ESTADO:
        estado_actual["sistema"] = mensaje

    elif topico == T_SISTEMA_ERROR:
        estado_actual["error"] = mensaje
        registrar_evento("error_sistema", {"mensaje": mensaje})
        registrar_alerta("Error del sistema: {}".format(mensaje), {"origen": "ESP32"})

    elif topico == T_SENSOR_PIR:
        estado_actual["sensores"]["pir"] = convertir_booleano(mensaje)

    elif topico == T_SENSOR_ULTRASONICO:
        estado_actual["sensores"]["ultrasonico_cm"] = convertir_numero(mensaje)

    elif topico == T_SENSOR_JOYSTICK_BASE:
        estado_actual["sensores"]["joystick_base"] = convertir_numero(mensaje)

    elif topico == T_SENSOR_DIRECCION_BASE:
        estado_actual["sensores"]["direccion_base"] = mensaje

    elif topico == T_ACTUADOR_BASE_GRADOS:
        estado_actual["actuadores"]["base_grados"] = convertir_numero(mensaje)

    elif topico == T_ACTUADOR_BRAZO_GRADOS:
        estado_actual["actuadores"]["brazo_grados"] = convertir_numero(mensaje)

    elif topico == T_IA_RESULTADO:
        datos_ia = parsear_json_seguro(mensaje)
        if datos_ia is None:
            datos_ia = {
                "estado_ia": "desconocida",
                "lectura": "sin_lectura",
                "clase": mensaje,
                "confianza": 0,
                "alerta": False,
                "timestamp": ahora_iso(),
            }

        datos_ia.setdefault("alerta", datos_ia.get("lectura") == "herido")
        estado_actual["ia"] = datos_ia
        guardar_ia_historica(forzar=False)

        lectura = str(datos_ia.get("lectura", "sin_lectura")).lower()
        if lectura == "herido":
            texto_alerta = "IA detecto posible seno herido"
            registrar_alerta(texto_alerta, datos_ia)
            registrar_evento("alerta_ia", datos_ia)

    elif topico == T_ALERTA_ULTIMA:
        estado_actual["alerta_ultima"] = mensaje
        if mensaje != ultima_alerta_texto:
            ultima_alerta_texto = mensaje
            registrar_alerta(mensaje, {"origen": "IA/MQTT"})

    elif topico in (T_CMD_BASE_MOVER, T_CMD_BRAZO_MOVER, T_CMD_SEGURO, T_CMD_INICIAR_OP, T_CMD_MODO_SISTEMA, T_CMD_IA_ESTADO):
        registrar_evento("comando_actuador", {"topico": topico, "mensaje": mensaje})

    elif topico == T_CMD_FIREBASE_GUARDAR_IA:
        guardar_ia_historica(forzar=True)
        guardar_snapshot_sensores(forzar=True)
        registrar_alerta("Guardado manual de ultima deteccion IA", estado_actual.get("ia", {}))

    guardar_snapshot_sensores(forzar=False)
    escribir_estado_actual(forzar=False)


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

def main():
    """
    Recibe:
        Nada.

    Hace:
        Inicia el puente MQTT -> Firebase.

    Devuelve:
        Nada.
    """

    global cliente_firestore, cliente_mqtt

    print("Iniciando Gateway Firebase CANMA")
    print("Credencial Firebase:", RUTA_CREDENCIAL_FIREBASE)
    print("Broker MQTT:", BROKER_HOST, BROKER_PORT)
    print("Intervalo estado:", INTERVALO_ESTADO_SEGUNDOS, "segundos")
    print("Intervalo IA historico:", INTERVALO_IA_HISTORICO_SEGUNDOS, "segundos")
    print("Subida de imagenes a Firebase:", SUBIR_IMAGENES_FIREBASE)

    cliente_firestore = inicializar_firebase()
    cliente_mqtt = crear_cliente_mqtt()

    cliente_mqtt.connect(BROKER_HOST, BROKER_PORT, 60)

    try:
        cliente_mqtt.loop_forever()
    except KeyboardInterrupt:
        print("Cerrando Gateway Firebase...")
    finally:
        try:
            escribir_estado_actual(forzar=True)
        except Exception:
            pass
        try:
            cliente_mqtt.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
