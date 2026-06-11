# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# OBJETIVO:
# Exponer en un solo punto las funciones, clases, configuración y tópicos
# necesarios para la comunicación WiFi y MQTT del ESP32.
# =============================================================================

# Se importa el módulo config completo para permitir usar:
# comms.config.SSID
# comms.config.CLAVE
# comms.config.SERVIDOR_MQTT
# comms.config.PUERTO_MQTT
# comms.config.USUARIO_MQTT
# comms.config.CLAVE_MQTT
from . import config

# Funciones de conexión WiFi
from .conexion_wifi import conectar_wifi, verificar_conexion

# Clase de conexión MQTT
from .conexion_mosquitto import MQTTLink

# Tabla de tópicos MQTT
from .comunicacion import *
