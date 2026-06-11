# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# ARCHIVO:
# sistema/raspberry/IA/ia_processor_mqtt.py
#
# OBJETIVO:
# Ejecutar el modelo YOLO en Raspberry/servidor externo, recibir por MQTT
# la orden de activar o apagar la IA, analizar la cámara y publicar un resultado
# procesable para el resto del sistema.
#
# FLUJO:
# Interfaz → MQTT → ia_processor_mqtt.py
# ia_processor_mqtt.py → MQTT → ESP32 / interfaz
# =============================================================================

import os
import cv2
import json
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from ultralytics import YOLO


# =============================================================================
# CONFIGURACIÓN GENERAL
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


# =============================================================================
# TÓPICOS MQTT
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
# FUNCIONES DE CLASIFICACIÓN
# =============================================================================

def normalizar_lectura(clase):
    """
    Parámetros:
        clase: nombre de clase entregado por YOLO.

    Hace:
        Convierte el nombre del modelo a una lectura simple para el sistema.

    Devuelve:
        "herido", "ileso", "falso" o "sin_lectura".
    """

    if clase is None:
        return "sin_lectura"

    texto = str(clase).strip().lower()

    if "herido" in texto:
        return "herido"

    if "ileso" in texto or "sano" in texto:
        return "ileso"

    if "falso" in texto:
        return "falso"

    return "sin_lectura"


def crear_payload_resultado(clase, confianza):
    """
    Parámetros:
        clase: clase detectada por YOLO.
        confianza: confianza del modelo.

    Hace:
        Crea un JSON estándar para que ESP32, interfaz y Firebase puedan leerlo.

    Devuelve:
        Diccionario con resultado IA.
    """

    lectura = normalizar_lectura(clase)

    alerta = lectura == "herido"

    return {
        "estado_ia": "activa" if ia_activa else "apagada",
        "lectura": lectura,
        "clase": "Sin lectura" if clase is None else str(clase),
        "confianza": round(float(confianza), 3),
        "alerta": alerta,
        "timestamp": datetime.now().isoformat(timespec="seconds")
    }


def publicar_resultado(datos):
    """
    Parámetros:
        datos: diccionario con resultado IA.

    Hace:
        Publica el resultado de IA y una alerta legible por MQTT.

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
        alerta = "IA: posible hallazgo visual detectado"
    elif lectura == "ileso":
        alerta = "IA: lectura sin alerta visual"
    elif lectura == "falso":
        alerta = "IA: detección marcada como falso positivo"
    else:
        alerta = "IA: sin lectura confiable"

    texto_alerta = f"{alerta} | {clase} | confianza: {confianza}"

    cliente_mqtt.publish(T_ALERTA_ULTIMA, texto_alerta)


def obtener_mejor_deteccion(modelo, frame):
    """
    Parámetros:
        modelo: modelo YOLO cargado.
        frame: imagen capturada por cámara.

    Hace:
        Ejecuta YOLO y toma la detección con mayor confianza.

    Devuelve:
        clase, confianza, caja.
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
        if resultado.boxes is None or len(resultado.boxes) == 0:
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
    Parámetros:
        frame: imagen de cámara.
        clase: clase detectada.
        confianza: confianza del modelo.
        caja: coordenadas de detección.

    Hace:
        Dibuja la detección principal en pantalla.

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

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    texto = f"{clase} {confianza * 100:.1f}%"

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
        print("Error conectando IA a MQTT. Código:", rc)


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


def crear_cliente_mqtt():
    """
    Hace:
        Crea y conecta el cliente MQTT de la IA.

    Devuelve:
        Cliente MQTT conectado.
    """

    try:
        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id="canma_ia_processor"
        )
    except Exception:
        cliente = mqtt.Client(client_id="canma_ia_processor")

    cliente.username_pw_set(BROKER_USER, BROKER_PASS)
    cliente.on_connect = on_connect
    cliente.on_message = on_message

    cliente.connect(BROKER_HOST, BROKER_PORT, 60)
    cliente.loop_start()

    return cliente


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

def main():
    """
    Hace:
        Carga el modelo YOLO, abre la cámara y procesa frames solo cuando
        la IA esté activa por MQTT.
    """

    global cliente_mqtt

    print("Cargando modelo IA...")
    print("Ruta del modelo:", MODELO_PATH)

    modelo = YOLO(MODELO_PATH)

    cliente_mqtt = crear_cliente_mqtt()

    camara = cv2.VideoCapture(CAMARA_ID)

    if not camara.isOpened():
        print("No se pudo abrir la cámara.")
        print("La IA seguirá conectada a MQTT, pero publicará sin lectura.")
        camara = None

    ultimo_envio = 0
    ultima_lectura = None

    print("Procesador IA listo.")
    print("Para activar IA publica: sistema/cmd/ia/estado = on")
    print("Para apagar IA publica: sistema/cmd/ia/estado = off")

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

        clase, confianza, caja = obtener_mejor_deteccion(modelo, frame)
        lectura = normalizar_lectura(clase)

        frame = dibujar_resultado(frame, clase, confianza, caja)

        ahora = time.time()

        if (ahora - ultimo_envio) >= INTERVALO_PUBLICACION or lectura != ultima_lectura:
            datos = crear_payload_resultado(clase, confianza)
            publicar_resultado(datos)

            ultimo_envio = ahora
            ultima_lectura = lectura

        cv2.imshow("CANMA - IA MQTT", frame)

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord("q"):
            break

    if camara is not None:
        camara.release()

    cv2.destroyAllWindows()

    cliente_mqtt.loop_stop()
    cliente_mqtt.disconnect()


if __name__ == "__main__":
    main()
