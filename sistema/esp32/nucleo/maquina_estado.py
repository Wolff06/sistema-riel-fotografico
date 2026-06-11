# =============================================================================
# PROYECTO: Sistema de Riel Semicircular Fotográfico 180°

# - OBJETIVO DEL CODIGO -
# Gestionar los estados principales del ESP32, 
# inicializando la conexión WiFi/MQTT y el 
# hardware del sistema, para después supervisar sensores 
# y actuadores según el modo de operación, espera o error.

# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando

# =============================================================================
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
        self._actuadores = None
        self._sensores = None

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
            self._sensores = hardware.CajaSensores()
            self._actuadores = hardware.CajaActuadores()
            self._actuadores.señal_lista()
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
        else:
            distancia = self._sensores.leer_distancia()
            print(distancia+" cm")
            if distancia <= 35:
                self._actuadores.señal_quieta()
            elif distancia >= 85:
                self._actuadores.señal_lista()


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
