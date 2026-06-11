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
        self.mqttBroker = None

    def transicion(self, nuevo_estado):
        print(f"Transicionando a {nuevo_estado}")
        self.estado = nuevo_estado

    def boot(self):
        if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):

            # REALIZAMOS LA CONEXIÓN AL BROKER DE MOSQUITTO
            self.mqttBroker = comms.MQTTLink(comms.config.SERVIDOR_MQTT, 
            comms.config.PUERTO_MQTT, comms.config.USUARIO_MQTT, comms.config.CLAVE_MQTT)
            
            def mi_callback(topico, mensaje):
                topico = topico.decode("utf-8")
                mensaje = mensaje.decode("utf-8")
                if topico == comms.T_CMD_INICIAR_OP:
                    if mensaje == "on":
                        self.transicion(ESTADO_OPERANDO)
                    else:
                        self.transicion(ESTADO_ESPERA)
                elif self.estado == ESTADO_OPERANDO:
                    if topico == comms.T_CMD_LED_ESTADO_AZUL:
                        if mensaje == "on":
                            self._actuadores.encender_led("AZUL")
                        else:
                            self._actuadores.apagar_led("AZUL")
                    else:
                        print("Mensaje recibido en", topico, ":", mensaje)
                else:
                    print("Mensaje recibido en", topico, ":", mensaje)
            
            self.mqttBroker.establecer_conexion_mqtt(callback=mi_callback)

            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO,"Iniciando")
            self.mqttBroker.suscribir(comms.T_CMD_INICIAR_OP)
            self.mqttBroker.suscribir(comms.T_CMD_LED_ESTADO_AZUL)

            # INSTANCIAMOS LAS CLASES DE CONTROL DE HARDWARE (HAL)
            self._sensores = hardware.CajaSensores()
            self._actuadores = hardware.CajaActuadores()
            self._actuadores.señal_lista()
            # llamar a firebase (Registro)
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
            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO,"Esperando instrucciones...")
            self.mqttBroker.esperar_mensajes()


    def operando(self):
        if not comms.verificar_conexion():
            print("Conexión perdida durante operación! Abortando...")
            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO,"Abortando...")
            self.mqttBroker.publicar(comms.T_SISTEMA_ERROR,"Conexión perdida con el servidor.")
            # TODO: Abortar operaciones
            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_OPERANDO)
            else:
                self.transicion(ESTADO_ERROR)
        else:
            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO,"Operando")
            self.mqttBroker.checar_mensajes()
            

    def error(self):
        print("Estado de error")
        #mqttBroker.publicar(comms.T_SISTEMA_ERROR,"Error en el sistema")

