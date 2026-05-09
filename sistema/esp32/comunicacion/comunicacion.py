# =============================================================================
# PROYECTO: Sistema de Riel Semicircular Fotográfico 180°
# MODULO:   ESP32/Comunicación
# INTEGRANTES: 
#              Macias Campos Ariadne Lizett 
#              Soto Garnica Ari Adair 
#              Lira Gamiño Luis Fernando 

# DESCRIPCIÓN: Modulo de comunicación que maneja la conexión Wi-Fi y las
#              publicaciones de sensores y suscripciones para los actuadores.
#
# =============================================================================


# IMPORTAR BIBLIOTECAS Y MÉTODOS NECESARIOS PARA USAR EL PROTOCOLO MQTT
import network
from umqtt.simple import MQTTClient
import time

# Configuración de la conexión Wi-Fi
ssid = "YOUR_SSID"
password = "YOUR_PASSWORD"
station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)
while not station.isconnected():
    pass

# Configuración del protocolo MQTT
broker = "192.168.1.100"  # Raspberry Pi IP
client = MQTTClient("esp32_client", broker)

# FUNCIÓN DE CALLBACK PARA LOS TÓPICOS DE ACTUADORES
def sub_cb(topic, msg):
    print((topic, msg))
    if topic == b"actuators/motor":
        if msg == b"ON":
            # turn motor on
            pass
        elif msg == b"OFF":
            # turn motor off
            pass

client.set_callback(sub_cb)
client.connect()
client.subscribe(b"actuators/motor")

while True:
    # PUBLICAR VALORES DE LOS SENSORES
    client.publish(b"sensors/temp", b"25.3")
    client.check_msg()  # CONSULTAR MENSAJES RECIBIDOS
    time.sleep(5)
