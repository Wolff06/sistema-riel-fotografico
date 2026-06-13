# -*- coding: utf-8 -*-
# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# INTEGRANTES: Escribir aqui los nombres de los integrantes del equipo
# ARCHIVO: sistema/raspberry/comunicacion/verificar_e2_mqtt.py
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# DESCRIPCION:
# Script de verificacion para la entrega E2. Permite comprobar que Mosquitto
# esta activo, que Python recibe datos del ESP32 con timestamp y que Python
# puede publicar un comando MQTT para mover un actuador fisico en el ESP32.
#
# Este archivo NO modifica la logica principal del proyecto. Es solo una prueba
# independiente para documentar y demostrar la integracion MQTT.
# =============================================================================

import argparse
import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


# =============================================================================
# TABLA DE TOPICOS MQTT USADOS EN E2
# =============================================================================

TOPICOS_PUBLICADOS_POR_ESP32 = [
    "sistema/sensores/pir",
    "sistema/sensores/ultrasonico",
    "sistema/sensores/joystick_base",
    "sistema/sensores/direccion_base",
    "sistema/actuadores/base/grados",
    "sistema/actuadores/brazo/grados",
    "sistema/estado",
    "sistema/error",
    "sistema/alertas/ultima",
]

TOPICOS_COMANDO_HACIA_ESP32 = {
    "modo": "sistema/cmd/modo",
    "iniciar": "sistema/cmd/iniciar",
    "seguro": "sistema/cmd/seguro",
    "base": "sistema/cmd/base/mover",
    "brazo": "sistema/cmd/brazo/mover",
    "buzzer": "sistema/cmd/buzzer/senal",
    "led_azul": "sistema/cmd/led/azul/estado",
}


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def obtener_timestamp():
    """
    Recibe:
        Nada.

    Hace:
        Obtiene la fecha y hora local en formato legible.

    Devuelve:
        Cadena con timestamp en formato AAAA-MM-DD HH:MM:SS.
    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def crear_cliente(cliente_id):
    """
    Recibe:
        cliente_id: nombre del cliente MQTT de Python.

    Hace:
        Crea un cliente compatible con versiones nuevas y anteriores de paho-mqtt.

    Devuelve:
        Objeto cliente MQTT.
    """

    try:
        return mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=cliente_id
        )
    except Exception:
        try:
            return mqtt.Client(client_id=cliente_id)
        except Exception:
            return mqtt.Client(cliente_id)


def imprimir_tabla_topicos():
    """
    Recibe:
        Nada.

    Hace:
        Imprime la tabla de topicos usados para demostrar la entrega E2.

    Devuelve:
        Nada.
    """

    print("\n========== TABLA DE TOPICOS E2 ==========")
    print("\nPublicacion ESP32 -> Raspberry/Python")
    for topico in TOPICOS_PUBLICADOS_POR_ESP32:
        print(" -", topico)

    print("\nSuscripcion ESP32 <- Raspberry/Python")
    for nombre, topico in TOPICOS_COMANDO_HACIA_ESP32.items():
        print(" -", nombre + ":", topico)


def publicar_comando_prueba(cliente, angulo_base):
    """
    Recibe:
        cliente: cliente MQTT conectado.
        angulo_base: angulo que se enviara al servo de la base.

    Hace:
        Publica un comando de prueba hacia el ESP32. El actuador que debe
        responder fisicamente es el servomotor de la base.

    Devuelve:
        Nada.
    """

    topico = TOPICOS_COMANDO_HACIA_ESP32["base"]
    mensaje = str(angulo_base)
    print("\n[{}] Enviando comando de prueba: {} = {}".format(
        obtener_timestamp(),
        topico,
        mensaje
    ))
    cliente.publish(topico, mensaje)


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

def main():
    """
    Recibe:
        Argumentos por consola.

    Hace:
        Se conecta a Mosquitto, se suscribe a los topicos publicados por el
        ESP32, imprime cada dato recibido con timestamp y opcionalmente publica
        un comando para mover la base.

    Devuelve:
        Nada.
    """

    if mqtt is None:
        print("No esta instalado paho-mqtt.")
        print("Instala con: python3 -m pip install paho-mqtt")
        return

    parser = argparse.ArgumentParser(
        description="Verificacion E2 MQTT para el proyecto CANMA"
    )
    parser.add_argument("--host", default="192.168.4.1", help="IP del broker Mosquitto")
    parser.add_argument("--puerto", default=1884, type=int, help="Puerto del broker Mosquitto")
    parser.add_argument("--usuario", default="admin", help="Usuario MQTT")
    parser.add_argument("--clave", default="123", help="Clave MQTT")
    parser.add_argument("--duracion", default=60, type=int, help="Segundos de escucha")
    parser.add_argument(
        "--enviar-comando",
        action="store_true",
        help="Publica un comando de prueba hacia el servo de la base"
    )
    parser.add_argument("--angulo", default=90, type=int, help="Angulo de prueba para la base")
    args = parser.parse_args()

    imprimir_tabla_topicos()

    cliente = crear_cliente("verificador_e2_canma")

    if args.usuario:
        cliente.username_pw_set(username=args.usuario, password=args.clave)

    comando_enviado = {"valor": False}

    def al_conectar(client, userdata, flags, rc):
        if rc == 0:
            print("\n[{}] Broker Mosquitto conectado correctamente".format(obtener_timestamp()))
            for topico in TOPICOS_PUBLICADOS_POR_ESP32:
                client.subscribe(topico)
                print("[{}] Suscrito a {}".format(obtener_timestamp(), topico))
        else:
            print("\n[{}] Error conectando a Mosquitto. Codigo: {}".format(obtener_timestamp(), rc))

    def al_recibir_mensaje(client, userdata, msg):
        try:
            mensaje = msg.payload.decode("utf-8")
        except Exception:
            mensaje = str(msg.payload)

        print("[{}] {} = {}".format(obtener_timestamp(), msg.topic, mensaje))

    def al_desconectar(client, userdata, rc=None):
        print("\n[{}] MQTT desconectado".format(obtener_timestamp()))

    cliente.on_connect = al_conectar
    cliente.on_message = al_recibir_mensaje
    cliente.on_disconnect = al_desconectar

    print("\nConectando a Mosquitto en {}:{}".format(args.host, args.puerto))
    cliente.connect(args.host, args.puerto, 60)
    cliente.loop_start()

    inicio = time.time()

    try:
        while time.time() - inicio < args.duracion:
            if args.enviar_comando and not comando_enviado["valor"]:
                time.sleep(2)
                publicar_comando_prueba(cliente, args.angulo)
                comando_enviado["valor"] = True
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nPrueba detenida por el usuario")

    finally:
        cliente.loop_stop()
        cliente.disconnect()
        print("\nPrueba E2 finalizada")


if __name__ == "__main__":
    main()
