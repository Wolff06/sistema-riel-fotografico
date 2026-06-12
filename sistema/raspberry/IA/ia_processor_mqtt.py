# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/raspberry/IA/ia_processor_mqtt.py
#
# OBJETIVO:
# Ejecutar YOLO en Raspberry/servidor externo, activarse por MQTT y publicar
# resultado procesable para ESP32, interfaz y Firebase.
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

# Si este modelo les funciona mejor, pueden cambiar la ruta por esta:
# Modelo-Feb2026/runs/cancer_SinFalsosPositivos/weights/best.pt

BROKER_HOST = "192.168.4.1"
BROKER_PORT = 1884
BROKER_USER = "admin"
BROKER_PASS = "123"

CAMARA_ID = 0
CONFIANZA_MINIMA = 0.45
INTERVALO_PUBLICACION = 2.0
MOSTRAR_VENTANA = True

T_CMD_IA_ESTADO = "sistema/cmd/ia/estado"
T_IA_RESULTADO = "sistema/ia/resultado"
T_ALERTA_ULTIMA = "sistema/alertas/ultima"

ia_activa = False
cliente_mqtt = None


def normalizar_lectura(clase):
    """
    Parametros:
        clase: nombre de clase de YOLO.

    Devuelve:
        herido, ileso, falso o sin_lectura.
    """

    if clase is None:
        return "sin_lectura"

    texto = str(clase).strip().lower()

    if "herido" in texto or "cancer" in texto or "lesion" in texto or "lesión" in texto:
        return "herido"

    if "ileso" in texto or "sano" in texto or "salud" in texto:
        return "ileso"

    if "falso" in texto:
        return "falso"

    return "sin_lectura"


def crear_payload_resultado(clase, confianza):
    """
    Hace:
        Crea JSON estandar para el sistema.
    """

    lectura = normalizar_lectura(clase)
    alerta = lectura == "herido"

    if clase is None:
        clase_texto = "Sin lectura"
    else:
        clase_texto = str(clase)

    return {
        "estado_ia": "activa" if ia_activa else "apagada",
        "lectura": lectura,
        "clase": clase_texto,
        "confianza": round(float(confianza), 3),
        "alerta": alerta,
        "timestamp": datetime.now().isoformat(timespec="seconds")
    }


def publicar_resultado(datos):
    """
    Hace:
        Publica resultado IA y alerta legible por MQTT.
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

    alerta = "{} | {} | confianza: {}".format(texto_alerta, clase, confianza)
    cliente_mqtt.publish(T_ALERTA_ULTIMA, alerta)


def obtener_mejor_deteccion(modelo, frame):
    """
    Hace:
        Ejecuta YOLO y devuelve la deteccion de mayor confianza.
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
    Hace:
        Dibuja resultado en la ventana de OpenCV.
    """

    lectura = normalizar_lectura(clase)

    if lectura == "sin_lectura" or caja is None:
        cv2.putText(frame, "IA: sin lectura confiable", (25, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        return frame

    x1, y1, x2, y2 = map(int, caja)

    if lectura == "herido":
        color = (0, 0, 255)
    elif lectura == "ileso":
        color = (0, 255, 0)
    else:
        color = (0, 255, 255)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    texto = "{} {:.1f}%".format(clase, confianza * 100)
    cv2.putText(frame, texto, (x1, max(30, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    return frame


def on_connect(client, userdata, flags, rc):
    """
    Callback de conexion MQTT.
    """

    if rc == 0:
        print("IA conectada a Mosquitto")
        client.subscribe(T_CMD_IA_ESTADO)
        print("IA suscrita a:", T_CMD_IA_ESTADO)
    else:
        print("Error conectando IA a MQTT. Codigo:", rc)


def on_message(client, userdata, msg):
    """
    Recibe on/off de IA por MQTT.
    """

    global ia_activa

    topico = msg.topic

    try:
        mensaje = msg.payload.decode("utf-8").strip().lower()
    except Exception:
        mensaje = str(msg.payload).strip().lower()

    print("MQTT IA recibido:", topico, mensaje)

    if topico != T_CMD_IA_ESTADO:
        return

    if mensaje in ("on", "activar", "true", "1"):
        ia_activa = True
        datos = {
            "estado_ia": "activa",
            "lectura": "sin_lectura",
            "clase": "Esperando lectura",
            "confianza": 0,
            "alerta": False,
            "timestamp": datetime.now().isoformat(timespec="seconds")
        }
        publicar_resultado(datos)
        print("IA ACTIVADA")

    elif mensaje in ("off", "apagar", "false", "0"):
        ia_activa = False
        datos = {
            "estado_ia": "apagada",
            "lectura": "sin_lectura",
            "clase": "IA apagada",
            "confianza": 0,
            "alerta": False,
            "timestamp": datetime.now().isoformat(timespec="seconds")
        }
        publicar_resultado(datos)
        print("IA APAGADA")


def crear_cliente_mqtt():
    """
    Hace:
        Crea cliente MQTT.
    """

    if mqtt is None:
        raise ImportError("No esta instalado paho-mqtt")

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
    return cliente


def validar_modelo():
    """
    Hace:
        Valida existencia del modelo.
    """

    if YOLO is None:
        raise ImportError("No esta instalado ultralytics")

    if not os.path.exists(MODELO_PATH):
        print("No se encontro el modelo en:")
        print(MODELO_PATH)
        raise FileNotFoundError("Modelo YOLO no encontrado")


def abrir_camara():
    """
    Hace:
        Abre camara OpenCV.
    """

    camara = cv2.VideoCapture(CAMARA_ID)

    if not camara.isOpened():
        print("No se pudo abrir la camara con indice:", CAMARA_ID)
        print("La IA seguira viva en MQTT, pero publicara sin lectura.")
        return None

    print("Camara abierta correctamente")
    return camara


def main():
    """
    Programa principal.
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
    cliente_mqtt.connect(BROKER_HOST, BROKER_PORT, 60)
    cliente_mqtt.loop_start()

    camara = abrir_camara()

    ultimo_envio = 0
    ultima_lectura = None

    print("Procesador IA listo.")
    print("Activa desde interfaz o con MQTT: sistema/cmd/ia/estado = on")

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

            clase, confianza, caja = obtener_mejor_deteccion(modelo, frame)
            lectura = normalizar_lectura(clase)
            ahora = time.time()

            if (ahora - ultimo_envio) >= INTERVALO_PUBLICACION or lectura != ultima_lectura:
                datos = crear_payload_resultado(clase, confianza)
                publicar_resultado(datos)
                ultimo_envio = ahora
                ultima_lectura = lectura

            if MOSTRAR_VENTANA:
                frame = dibujar_resultado(frame, clase, confianza, caja)
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
