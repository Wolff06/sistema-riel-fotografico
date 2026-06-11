# -*- coding: utf-8 -*-
# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
#
# ARCHIVO:
# sistema/raspberry/IA/ia_processor_mqtt.py
#
# OBJETIVO:
# Ejecutar el modelo YOLO en Raspberry o servidor externo, esperar la orden
# MQTT para activar o apagar la IA, procesar la camara y publicar un resultado
# que pueda ser leido por la interfaz, Firebase y ESP32.
#
# FLUJO:
# Interfaz -> MQTT -> IA
# IA -> MQTT -> ESP32 / Interfaz / Firebase
# =============================================================================

import os
import cv2
import json
import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


# =============================================================================
# CONFIGURACION GENERAL
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODELO_PATH = os.path.join(
    BASE_DIR,
    "Modelo-Feb2026",
    "runs",
    "cancer",
    "train_v1",
    "weights",
    "best.pt"
)

BROKER_HOST = "192.168.4.1"
BROKER_PORT = 1884
BROKER_USER = "admin"
BROKER_PASS = "123"

CAMARA_ID = 0

CONFIANZA_MINIMA = 0.45
INTERVALO_PUBLICACION = 2.0

MOSTRAR_VENTANA = True


# =============================================================================
# TOPICOS MQTT
# =============================================================================

T_CMD_IA_ESTADO = "sistema/cmd/ia/estado"

T_IA_RESULTADO = "sistema/ia/resultado"
T_ALERTA_ULTIMA = "sistema/alertas/ultima"


# =============================================================================
# VARIABLES GLOBALES
# =============================================================================

ia_activa = False
cliente_mqtt = None


# =============================================================================
# FUNCIONES DE IA
# =============================================================================

def normalizar_lectura(clase):
    """
    Parametros:
        clase: nombre de clase entregado por YOLO.

    Hace:
        Convierte el nombre del modelo a una lectura simple para el sistema.

    Devuelve:
        herido, ileso, falso o sin_lectura.
    """

    if clase is None:
        return "sin_lectura"

    texto = str(clase).strip().lower()

    if "herido" in texto:
        return "herido"

    if "ileso" in texto:
        return "ileso"

    if "sano" in texto:
        return "ileso"

    if "falso" in texto:
        return "falso"

    return "sin_lectura"


def crear_payload_resultado(clase, confianza):
    """
    Parametros:
        clase: clase detectada.
        confianza: confianza del modelo.

    Hace:
        Crea un diccionario estandar para publicar el resultado de IA.

    Devuelve:
        Diccionario con resultado.
    """

    lectura = normalizar_lectura(clase)

    alerta = False

    if lectura == "herido":
        alerta = True

    if clase is None:
        clase_texto = "Sin lectura"
    else:
        clase_texto = str(clase)

    datos = {
        "estado_ia": "activa" if ia_activa else "apagada",
        "lectura": lectura,
        "clase": clase_texto,
        "confianza": round(float(confianza), 3),
        "alerta": alerta,
        "timestamp": datetime.now().isoformat(timespec="seconds")
    }

    return datos


def publicar_resultado(datos):
    """
    Parametros:
        datos: diccionario con resultado de IA.

    Hace:
        Publica el resultado de IA por MQTT y tambien una alerta legible.

    Devuelve:
        Nada.
    """

    if cliente_mqtt is None:
        return

    mensaje_json = json.dumps(datos, ensure_ascii=False)

    print("PUBLICANDO IA:", mensaje_json)

    cliente_mqtt.publish(T_IA_RESULTADO, mensaje_json)

    lectura = datos.get("lectura", "sin_lectura")
    clase = datos.get("clase", "Sin lectura")
    confianza = datos.get("confianza", 0)

    if lectura == "herido":
        texto_alerta = "IA: posible hallazgo visual detectado"
    elif lectura == "ileso":
        texto_alerta = "IA: lectura sin alerta visual"
    elif lectura == "falso":
        texto_alerta = "IA: deteccion marcada como falso positivo"
    else:
        texto_alerta = "IA: sin lectura confiable"

    mensaje_alerta = "{} | {} | confianza: {}".format(
        texto_alerta,
        clase,
        confianza
    )

    cliente_mqtt.publish(T_ALERTA_ULTIMA, mensaje_alerta)


def obtener_mejor_deteccion(modelo, frame):
    """
    Parametros:
        modelo: modelo YOLO cargado.
        frame: imagen capturada por camara.

    Hace:
        Ejecuta YOLO y toma la deteccion con mayor confianza.

    Devuelve:
        clase, confianza y caja.
    """

    resultados = modelo.predict(
        source=frame,
        conf=CONFIANZA_MINIMA,
        verbose=False,
        stream=False
    )

    mejor_clase = None
    mejor_confianza = 0
    mejor_caja = None

    for resultado in resultados:
        if resultado.boxes is None:
            continue

        if len(resultado.boxes) == 0:
            continue

        cajas = resultado.boxes.xyxy.cpu().numpy()
        confianzas = resultado.boxes.conf.cpu().numpy()
        clases = resultado.boxes.cls.cpu().numpy().astype(int)

        for caja, confianza, clase_id in zip(cajas, confianzas, clases):
            if confianza > mejor_confianza:
                mejor_confianza = confianza
                mejor_clase = modelo.names[int(clase_id)]
                mejor_caja = caja

    return mejor_clase, mejor_confianza, mejor_caja


def dibujar_resultado(frame, clase, confianza, caja):
    """
    Parametros:
        frame: imagen de camara.
        clase: clase detectada.
        confianza: confianza del modelo.
        caja: coordenadas de deteccion.

    Hace:
        Dibuja el resultado principal en pantalla.

    Devuelve:
        Frame con anotaciones.
    """

    lectura = normalizar_lectura(clase)

    if lectura == "sin_lectura" or caja is None:
        cv2.putText(
            frame,
            "IA: sin lectura confiable",
            (25, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        return frame

    x1, y1, x2, y2 = map(int, caja)

    if lectura == "herido":
        color = (0, 0, 255)
    elif lectura == "ileso":
        color = (0, 255, 0)
    else:
        color = (0, 255, 255)

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        color,
        2
    )

    texto = "{} {:.1f}%".format(
        clase,
        confianza * 100
    )

    cv2.putText(
        frame,
        texto,
        (x1, max(30, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2
    )

    return frame


# =============================================================================
# MQTT
# =============================================================================

def crear_cliente_mqtt():
    """
    Hace:
        Crea el cliente MQTT compatible con versiones nuevas y viejas de paho.

    Devuelve:
        Cliente MQTT.
    """

    if mqtt is None:
        raise ImportError(
            "No esta instalado paho-mqtt. Instala con: python3 -m pip install paho-mqtt"
        )

    try:
        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id="canma_ia_processor"
        )
    except Exception:
        try:
            cliente = mqtt.Client(client_id="canma_ia_processor")
        except Exception:
            cliente = mqtt.Client("canma_ia_processor")

    cliente.username_pw_set(
        username=BROKER_USER,
        password=BROKER_PASS
    )

    cliente.on_connect = on_connect
    cliente.on_message = on_message
    cliente.on_disconnect = on_disconnect

    return cliente


def on_connect(client, userdata, flags, rc):
    """
    Hace:
        Se ejecuta cuando la IA se conecta al broker MQTT.
    """

    if rc == 0:
        print("IA conectada a Mosquitto")
        client.subscribe(T_CMD_IA_ESTADO)
        print("IA suscrita a:", T_CMD_IA_ESTADO)
    else:
        print("Error conectando IA a MQTT. Codigo:", rc)


def on_disconnect(client, userdata, rc=None):
    """
    Hace:
        Se ejecuta cuando la IA se desconecta del broker.
    """

    print("IA desconectada de MQTT")


def on_message(client, userdata, msg):
    """
    Hace:
        Recibe comandos MQTT para activar o apagar la IA.
    """

    global ia_activa

    topico = msg.topic

    try:
        mensaje = msg.payload.decode("utf-8").strip().lower()
    except Exception:
        mensaje = str(msg.payload).strip().lower()

    print("MQTT IA recibido:", topico, mensaje)

    if topico == T_CMD_IA_ESTADO:
        if mensaje in ("on", "activar", "true", "1"):
            ia_activa = True
            print("IA ACTIVADA")

            datos = {
                "estado_ia": "activa",
                "lectura": "sin_lectura",
                "clase": "Esperando lectura",
                "confianza": 0,
                "alerta": False,
                "timestamp": datetime.now().isoformat(timespec="seconds")
            }

            publicar_resultado(datos)

        elif mensaje in ("off", "apagar", "false", "0"):
            ia_activa = False
            print("IA APAGADA")

            datos = {
                "estado_ia": "apagada",
                "lectura": "sin_lectura",
                "clase": "IA apagada",
                "confianza": 0,
                "alerta": False,
                "timestamp": datetime.now().isoformat(timespec="seconds")
            }

            publicar_resultado(datos)

        else:
            print("Comando IA no reconocido:", mensaje)


# =============================================================================
# VALIDACIONES
# =============================================================================

def validar_modelo():
    """
    Hace:
        Verifica que exista el modelo entrenado.

    Devuelve:
        Nada.
    """

    if YOLO is None:
        raise ImportError(
            "No esta instalado ultralytics. Instala con: python3 -m pip install ultralytics"
        )

    if not os.path.exists(MODELO_PATH):
        print("No se encontro el modelo en:")
        print(MODELO_PATH)
        print("")
        print("Revisa que exista:")
        print("Modelo-Feb2026/runs/cancer/train_v1/weights/best.pt")
        raise FileNotFoundError("Modelo YOLO no encontrado")


def abrir_camara():
    """
    Hace:
        Abre la camara con OpenCV.

    Devuelve:
        Objeto de camara o None.
    """

    camara = cv2.VideoCapture(CAMARA_ID)

    if not camara.isOpened():
        print("No se pudo abrir la camara con indice:", CAMARA_ID)
        print("La IA seguira viva en MQTT, pero publicara sin lectura.")
        return None

    print("Camara abierta correctamente")
    return camara


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

def main():
    """
    Hace:
        Carga modelo, conecta MQTT, abre camara y procesa frames solo cuando
        la IA este activa.
    """

    global cliente_mqtt

    print("Iniciando procesador IA CANMA")
    print("Ruta del modelo:")
    print(MODELO_PATH)

    validar_modelo()

    print("Cargando modelo YOLO...")
    modelo = YOLO(MODELO_PATH)
    print("Modelo cargado correctamente")

    cliente_mqtt = crear_cliente_mqtt()

    print("Conectando IA a MQTT...")
    print("Broker:", BROKER_HOST)
    print("Puerto:", BROKER_PORT)

    cliente_mqtt.connect(BROKER_HOST, BROKER_PORT, 60)
    cliente_mqtt.loop_start()

    camara = abrir_camara()

    ultimo_envio = 0
    ultima_lectura = None

    print("")
    print("Procesador IA listo.")
    print("Para activar IA:")
    print("mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t sistema/cmd/ia/estado -m on")
    print("")
    print("Para apagar IA:")
    print("mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t sistema/cmd/ia/estado -m off")
    print("")
    print("Para salir presiona Ctrl+C o Q en la ventana de camara.")

    try:
        while True:
            if not ia_activa:
                time.sleep(0.2)
                continue

            if camara is None:
                datos = crear_payload_resultado(None, 0)
                publicar_resultado(datos)
                time.sleep(INTERVALO_PUBLICACION)
                continue

            ret, frame = camara.read()

            if not ret:
                datos = crear_payload_resultado(None, 0)
                publicar_resultado(datos)
                time.sleep(INTERVALO_PUBLICACION)
                continue

            clase, confianza, caja = obtener_mejor_deteccion(
                modelo,
                frame
            )

            lectura = normalizar_lectura(clase)

            ahora = time.time()

            if (ahora - ultimo_envio) >= INTERVALO_PUBLICACION or lectura != ultima_lectura:
                datos = crear_payload_resultado(
                    clase,
                    confianza
                )

                publicar_resultado(datos)

                ultimo_envio = ahora
                ultima_lectura = lectura

            if MOSTRAR_VENTANA:
                frame = dibujar_resultado(
                    frame,
                    clase,
                    confianza,
                    caja
                )

                cv2.imshow("CANMA - IA MQTT", frame)

                tecla = cv2.waitKey(1) & 0xFF

                if tecla == ord("q"):
                    break

    except KeyboardInterrupt:
        print("Cerrando procesador IA...")

    finally:
        if camara is not None:
            camara.release()

        if MOSTRAR_VENTANA:
            cv2.destroyAllWindows()

        if cliente_mqtt is not None:
            cliente_mqtt.loop_stop()
            cliente_mqtt.disconnect()

        print("IA finalizada")


if __name__ == "__main__":
    main()
