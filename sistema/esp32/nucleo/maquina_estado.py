# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# - OBJETIVO DEL CÓDIGO -
# Gestionar los estados principales del ESP32, inicializando la conexión WiFi,
# la conexión MQTT y el hardware del sistema. También supervisa sensores,
# controla actuadores mediante la HAL y publica datos reales hacia Mosquitto.
#
# - INTEGRANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
# =============================================================================

import time
import ujson

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

        # Control de publicación para no saturar MQTT
        self._ultimo_envio_ms = 0
        self._intervalo_envio_ms = 500

        # Tópicos adicionales.
        # Si ya existen en comunicacion/__init__.py, usa esos.
        # Si no existen, usa estos valores por defecto.
        self.T_SENSOR_JOYSTICK_BASE = getattr(
            comms,
            "T_SENSOR_JOYSTICK_BASE",
            "canma/sensores/joystick_base"
        )

        self.T_SENSOR_DIRECCION_BASE = getattr(
            comms,
            "T_SENSOR_DIRECCION_BASE",
            "canma/sensores/direccion_base"
        )

        self.T_ACTUADOR_BASE_GRADOS = getattr(
            comms,
            "T_ACTUADOR_BASE_GRADOS",
            "canma/actuadores/base_grados"
        )

        self.T_CMD_BASE_MOVER = getattr(
            comms,
            "T_CMD_BASE_MOVER",
            "canma/cmd/base/mover"
        )

    # -------------------------------------------------------------------------
    def transicion(self, nuevo_estado):
        """
        Parámetros:
            nuevo_estado: estado al que se desea cambiar.

        Hace:
            Cambia el estado interno de la máquina de estados.

        Devuelve:
            Nada.
        """
        print("Transicionando a", nuevo_estado)
        self.estado = nuevo_estado

    # -------------------------------------------------------------------------
    def boot(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Conecta el ESP32 a WiFi, conecta al broker MQTT, configura los
            callbacks, inicializa sensores y actuadores mediante la HAL.

        Devuelve:
            Nada.
        """

        if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):

            # Instanciar hardware primero para que el callback pueda usarlo
            self._sensores = hardware.CajaSensores()
            self._actuadores = hardware.CajaActuadores()

            # Posición inicial segura de la base
            self._actuadores.mover_base(90)

            # Conexión al broker Mosquitto
            self.mqttBroker = comms.MQTTLink(
                comms.config.SERVIDOR_MQTT,
                comms.config.PUERTO_MQTT,
                comms.config.USUARIO_MQTT,
                comms.config.CLAVE_MQTT
            )

            def mi_callback(topico, mensaje):
                """
                Callback MQTT.
                Recibe comandos desde Mosquitto y ejecuta acciones mediante HAL.
                """

                topico = topico.decode("utf-8") if isinstance(topico, bytes) else topico
                mensaje = mensaje.decode("utf-8") if isinstance(mensaje, bytes) else mensaje

                print("MQTT recibido:", topico, "=", mensaje)

                # Comando para iniciar o detener operación
                if topico == comms.T_CMD_INICIAR_OP:
                    if mensaje == "on":
                        self.transicion(ESTADO_OPERANDO)
                    else:
                        self.transicion(ESTADO_ESPERA)

                # Comando para LED azul
                elif topico == comms.T_CMD_LED_ESTADO_AZUL:
                    if mensaje == "on":
                        self._actuadores.encender_led("AZUL")
                    else:
                        self._actuadores.apagar_led("AZUL")

                # Comando remoto para mover la base
                elif topico == self.T_CMD_BASE_MOVER:
                    self._procesar_comando_base(mensaje)

                else:
                    print("Tópico no manejado:", topico)

            self.mqttBroker.establecer_conexion_mqtt(callback=mi_callback)

            # Publicaciones iniciales
            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO, "Iniciando")
            self.mqttBroker.publicar(comms.T_SENSOR_PIR, "false")
            self.mqttBroker.publicar(comms.T_SENSOR_ULTRASONICO, "null")
            self.mqttBroker.publicar(self.T_SENSOR_JOYSTICK_BASE, "0")
            self.mqttBroker.publicar(self.T_SENSOR_DIRECCION_BASE, "CENTRO")
            self.mqttBroker.publicar(self.T_ACTUADOR_BASE_GRADOS, "90")

            # Suscripciones MQTT
            self.mqttBroker.suscribir(comms.T_CMD_INICIAR_OP)
            self.mqttBroker.suscribir(comms.T_CMD_LED_ESTADO_AZUL)
            self.mqttBroker.suscribir(self.T_CMD_BASE_MOVER)

            # Señal física de inicio
            self._actuadores.señal_lista()

            self.transicion(ESTADO_ESPERA)

        else:
            self.transicion(ESTADO_ERROR)

    # -------------------------------------------------------------------------
    def espera(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Mantiene el sistema en espera. Sigue publicando sensores, pero no
            mueve la base con joystick hasta entrar en estado OPERANDO.

        Devuelve:
            Nada.
        """

        if not comms.verificar_conexion():
            print("Conexión perdida en modo espera, reconectando...")

            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_ESPERA)
            else:
                self.transicion(ESTADO_ERROR)

        else:
            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO, "Esperando instrucciones")

            # Publicar sensores aunque esté en espera
            self._publicar_datos_sensores()

            # Escuchar mensajes MQTT
            self.mqttBroker.checar_mensajes()

    # -------------------------------------------------------------------------
    def operando(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Lee sensores, mueve la base según el joystick, publica los datos
            por MQTT y escucha comandos remotos.

        Devuelve:
            Nada.
        """

        if not comms.verificar_conexion():
            print("Conexión perdida durante operación. Abortando...")

            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO, "Abortando")
            self.mqttBroker.publicar(comms.T_SISTEMA_ERROR, "Conexión perdida con el servidor")

            self._actuadores.estado_seguro()

            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_OPERANDO)
            else:
                self.transicion(ESTADO_ERROR)

        else:
            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO, "Operando")

            # Leer joystick desde la HAL
            direccion = self._sensores.obtener_direccion_joystick_base()

            # Mover la base desde la HAL
            self._actuadores.mover_base_por_direccion(
                direccion,
                paso=1,
                minimo=0,
                maximo=180
            )

            # Publicar sensores y posición de base
            self._publicar_datos_sensores()

            # Escuchar comandos MQTT
            self.mqttBroker.checar_mensajes()

    # -------------------------------------------------------------------------
    def error(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Coloca el sistema en estado seguro y publica error si MQTT existe.

        Devuelve:
            Nada.
        """

        print("Estado de error")

        if self._actuadores is not None:
            self._actuadores.estado_seguro()

        if self.mqttBroker is not None:
            self.mqttBroker.publicar(comms.T_SISTEMA_ESTADO, "ERROR")
            self.mqttBroker.publicar(comms.T_SISTEMA_ERROR, "Error en el sistema")

    # -------------------------------------------------------------------------
    def _publicar_datos_sensores(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Publica por MQTT las lecturas actuales de sensores y actuadores.
            Usa un intervalo para no saturar la red.

        Devuelve:
            Nada.
        """

        actual = time.ticks_ms()

        if time.ticks_diff(actual, self._ultimo_envio_ms) < self._intervalo_envio_ms:
            return

        self._ultimo_envio_ms = actual

        presencia = self._sensores.obtener_presencia()
        distancia = self._sensores.leer_distancia()
        joystick = self._sensores.leer_joystick_base()
        direccion = self._sensores.obtener_direccion_joystick_base()
        angulo_base = self._actuadores.obtener_posicion_base()

        # Convertir valores a texto para MQTT
        presencia_txt = "true" if presencia else "false"
        distancia_txt = "null" if distancia is None else str(round(distancia, 2))

        self.mqttBroker.publicar(comms.T_SENSOR_PIR, presencia_txt)
        self.mqttBroker.publicar(comms.T_SENSOR_ULTRASONICO, distancia_txt)
        self.mqttBroker.publicar(self.T_SENSOR_JOYSTICK_BASE, str(joystick))
        self.mqttBroker.publicar(self.T_SENSOR_DIRECCION_BASE, direccion)
        self.mqttBroker.publicar(self.T_ACTUADOR_BASE_GRADOS, str(angulo_base))

        print(
            "PIR:", presencia_txt,
            "| Distancia:", distancia_txt,
            "| Joystick:", joystick,
            "| Dirección:", direccion,
            "| Base:", angulo_base
        )

    # -------------------------------------------------------------------------
    def _procesar_comando_base(self, mensaje):
        """
        Parámetros:
            mensaje: texto recibido por MQTT. Puede ser un número como "90"
                     o un JSON como {"angulo": 90}.

        Hace:
            Interpreta el ángulo solicitado y mueve la base mediante la HAL.

        Devuelve:
            Nada.
        """

        try:
            # Intentar interpretar como JSON
            if mensaje.startswith("{"):
                datos = ujson.loads(mensaje)
                angulo = int(datos.get("angulo", 90))
            else:
                angulo = int(mensaje)

            angulo_final = self._actuadores.mover_base(angulo)

            self.mqttBroker.publicar(
                self.T_ACTUADOR_BASE_GRADOS,
                str(angulo_final)
            )

            print("Base movida por MQTT a:", angulo_final)

        except Exception as error:
            print("Error al mover base por MQTT:", error)

            self.mqttBroker.publicar(
                comms.T_SISTEMA_ERROR,
                "Comando de base inválido"
            )
