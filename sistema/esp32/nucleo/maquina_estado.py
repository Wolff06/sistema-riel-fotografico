import time
import network

import comunicacion as comms
import hardware

ESTADO_BOOT = 1
ESTADO_ESPERA = 2
ESTADO_OPERANDO = 3
ESTADO_ERROR = 99

class MaquinaEstado:
    def __init__(self):
        self.estado = ESTADO_BOOT

    def transicion(self, nuevo_estado):
        print(f"Transicionando a {nuevo_estado}")
        self.estado = nuevo_estado

    def boot(self):
        if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):

            # REALIZAMOS LA CONEXIÓN AL BROKER DE MOSQUITTO
            mqttBroker = comms.MQTTLink(comms.config.SERVIDOR_MQTT, 
            comms.config.PUERTO_MQTT, comms.config.USUARIO_MQTT, comms.config.CLAVE_MQTT)
            mqttBroker.establecer_conexion_mqtt()
            # INSTANCIAMOS LAS CLASES DE CONTROL DE HARDWARE (HAL)
            sensores = hardware.CajaSensores()
            actuadores = hardware.CajaSensores()

            self.transicion(ESTADO_ESPERA)
        else:
            self.transicion(ESTADO_ERROR)

    def espera(self):
        if not comms.verificar_conexion():
            print("Conexión perdida en modo espera, reconectando...")
            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_ESPERA)
            else:
                self.transicion(ESTADO_ERROR)

    def operando(self):
        if not comms.verificar_conexion():
            print("Conexión perdida durante operación! Abortando...")
            # TODO: Abortar operaciones
            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_OPERANDO)
            else:
                self.transicion(ESTADO_ERROR)

    def error(self):
        print("Estado de error")
