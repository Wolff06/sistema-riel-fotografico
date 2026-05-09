# =============================================================================
# PROYECTO: Sistema de Riel Semicircular Fotográfico 180°
# MODULO:   Raspberry/Comunicación
# INTEGRANTES: 
#              Macias Campos Ariadne Lizett 
#              Soto Garnica Ari Adair 
#              Lira Gamiño Luis Fernando 

# DESCRIPCIÓN: 
#
# =============================================================================

# IMPORTACIÓN DE BIBLIOTECAS Y MODULOS PARA EL MANEJO DE COMUNICACIONES MQTT
import paho.mqtt.client as mqtt

# CONFIGURACIÓN DEL BROKER MQTT - MOSQUITTO
broker = "192.168.1.100" # Establecer una dirección local estática

# FUNCIÓN DE CALLBACK PARA LA RECEPCIÓN DE MENSAJES
def on_message(client, userdata, msg):
    print(f"{msg.topic}: {msg.payload.decode()}")

# CONEXIÓN AL BROKER
client = mqtt.Client("python_server")
client.on_message = on_message
client.connect(broker, 1883, 60)

client.subscribe("sensors/#")

# Publicación de comandos para los actuadores
# client.publish("actuators/motor", "ON")

client.loop_forever()
