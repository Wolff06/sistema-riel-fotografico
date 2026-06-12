# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# ARCHIVO:
# sistema/raspberry/main_interfaz_mqtt.py
#
# OBJETIVO:
# Ejecutar la interfaz gráfica de Raspberry conectada al broker Mosquitto.
# Este archivo une la arquitectura MVC de la interfaz con el puente MQTT.
#
# FLUJO:
# ESP32 → Mosquitto → MQTTBridge → VistaPantalla
# VistaPantalla → MQTTBridge → Mosquitto → ESP32
# =============================================================================
import os
import sys

# =============================================================================
# RUTAS DEL PROYECTO
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUTA_INTERFAZ = os.path.join(BASE_DIR, "interfaz")
RUTA_COMUNICACION = os.path.join(BASE_DIR, "comunicacion")

sys.path.append(RUTA_INTERFAZ)
sys.path.append(RUTA_COMUNICACION)


# =============================================================================
# IMPORTACIÓN DE MÓDULOS
# =============================================================================

from modelo_pantalla import ModeloPantalla
from vista_pantalla import VistaPantalla
from controlador_pantalla import ControladorPantalla
from mqtt_bridge import MQTTBridge


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """
    Inicializa la interfaz CANMA, conecta el puente MQTT y ejecuta Tkinter.
    """

    # -------------------------------------------------------------------------
    # Crear arquitectura MVC de la interfaz
    # -------------------------------------------------------------------------

    modelo = ModeloPantalla()
    vista = VistaPantalla(modelo)
    controlador = ControladorPantalla(modelo, vista)

    # -------------------------------------------------------------------------
    # Crear puente MQTT
    # -------------------------------------------------------------------------

    bridge = MQTTBridge(
        vista=vista,
        host="192.168.4.1",
        puerto=1884,
        usuario="admin",
        clave="123"
    )

    # -------------------------------------------------------------------------
    # Conectar botones de la vista con MQTT
    # -------------------------------------------------------------------------
    # Esto permite que:
    # ON  → publique sistema/cmd/iniciar = on
    # OFF → publique sistema/cmd/iniciar = off
    # Flechas de grados → publiquen sistema/cmd/base/mover
    # Estado seguro → publique sistema/cmd/seguro

    vista.configurar_publicador_mqtt(bridge.publicar)
    modelo.configurar_publicador_mqtt(bridge.publicar)

    # -------------------------------------------------------------------------
    # Iniciar MQTT e interfaz
    # -------------------------------------------------------------------------

    try:
        bridge.iniciar()
        vista.iniciar()

    finally:
        bridge.detener()


# =============================================================================
# EJECUCIÓN
# =============================================================================

if __name__ == "__main__":
    main()
