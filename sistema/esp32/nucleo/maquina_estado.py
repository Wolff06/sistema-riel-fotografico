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


# =============================================================================
# ESTADOS DEL SISTEMA
# =============================================================================

ESTADO_BOOT = 1
ESTADO_ESPERA = 2
ESTADO_OPERANDO = 3
ESTADO_ERROR = 99


# =============================================================================
# CLASE: MaquinaEstado
# =============================================================================

class MaquinaEstado:
    """
    Controla el ciclo principal del ESP32.

    Responsabilidades:
      - Conectar WiFi.
      - Conectar MQTT.
      - Instanciar sensores y actuadores mediante HAL.
      - Publicar datos reales por MQTT.
      - Recibir comandos MQTT para actuadores.
      - Cambiar entre BOOT, ESPERA, OPERANDO y ERROR.
    """

    def __init__(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Inicializa las variables principales de la máquina de estados.

        Devuelve:
            Nada.
        """

        self.estado = ESTADO_BOOT

        self._actuadores = None
        self._sensores = None
        self.mqttBroker = None

        # Control de publicación para no saturar MQTT
        self._ultimo_envio_ms = 0
        self._intervalo_envio_ms = 500

        # Control para no publicar estado repetido demasiadas veces
        self._ultimo_estado_publicado = None

    # -------------------------------------------------------------------------
    def transicion(self, nuevo_estado):
        """
        Parámetros:
            nuevo_estado: estado al que se desea cambiar.

        Hace:
            Cambia el estado interno del sistema.

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
            Conecta el ESP32 a WiFi, conecta MQTT, configura callback,
            inicializa sensores y actuadores mediante la HAL, publica valores
            iniciales y se suscribe a comandos.

        Devuelve:
            Nada.
        """

        if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):

            # Instanciar hardware primero para que el callback pueda usarlo.
            self._sensores = hardware.CajaSensores()
            self._actuadores = hardware.CajaActuadores()

            # Posición inicial segura de la base.
            self._actuadores.mover_base(90)

            # Conexión al broker Mosquitto.
            self.mqttBroker = comms.MQTTLink(
                comms.config.SERVIDOR_MQTT,
                comms.config.PUERTO_MQTT,
                comms.config.USUARIO_MQTT,
                comms.config.CLAVE_MQTT
            )

            self.mqttBroker.establecer_conexion_mqtt(callback=self._callback_mqtt)

            # Suscripciones MQTT.
            self._suscribir_comandos()

            # Publicaciones iniciales.
            self._publicar_estado("Iniciando")
            self._publicar_valores_iniciales()

            # Señal física de inicio.
            self._ejecutar_senal("lista")

            self.transicion(ESTADO_ESPERA)
            self._publicar_estado("Esperando instrucciones")

        else:
            self.transicion(ESTADO_ERROR)

    # -------------------------------------------------------------------------
    def espera(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Mantiene el sistema en espera. Publica sensores, escucha comandos
            MQTT y no mueve la base con joystick hasta entrar en OPERANDO.

        Devuelve:
            Nada.
        """

        if not comms.verificar_conexion():
            print("Conexión perdida en modo espera, reconectando...")

            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_ESPERA)
                self._publicar_estado("Esperando instrucciones")
            else:
                self.transicion(ESTADO_ERROR)

        else:
            self._publicar_estado("Esperando instrucciones")
            self._publicar_datos_sensores()
            self._checar_mqtt()

    # -------------------------------------------------------------------------
    def operando(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Lee sensores, mueve la base según el joystick, publica datos por
            MQTT y escucha comandos remotos.

        Devuelve:
            Nada.
        """

        if not comms.verificar_conexion():
            print("Conexión perdida durante operación. Abortando...")

            self._publicar_estado("Abortando")
            self._publicar_error("Conexión perdida con el servidor")

            if self._actuadores is not None:
                self._actuadores.estado_seguro()

            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_OPERANDO)
                self._publicar_estado("Operando")
            else:
                self.transicion(ESTADO_ERROR)

        else:
            self._publicar_estado("Operando")

            # Leer joystick desde la HAL.
            direccion = self._sensores.obtener_direccion_joystick_base()

            # Mover base desde la HAL.
            self._actuadores.mover_base_por_direccion(
                direccion,
                paso=1,
                minimo=0,
                maximo=180
            )

            # Publicar sensores y posición de base.
            self._publicar_datos_sensores()

            # Escuchar comandos MQTT.
            self._checar_mqtt()

    # -------------------------------------------------------------------------
    def error(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Coloca el sistema en estado seguro y publica el error si MQTT existe.

        Devuelve:
            Nada.
        """

        print("Estado de error")

        if self._actuadores is not None:
            self._actuadores.estado_seguro()

        self._publicar_estado("ERROR")
        self._publicar_error("Error en el sistema")

    # -------------------------------------------------------------------------
    def _callback_mqtt(self, topico, mensaje):
        """
        Parámetros:
            topico: tópico MQTT recibido.
            mensaje: mensaje recibido por MQTT.

        Hace:
            Interpreta comandos entrantes y ejecuta acciones usando la HAL.

        Devuelve:
            Nada.
        """

        topico = self._decodificar(topico)
        mensaje = self._decodificar(mensaje).strip()

        print("MQTT recibido:", topico, "=", mensaje)

        # ---------------------------------------------------------------------
        # Comando para iniciar o detener operación.
        # ---------------------------------------------------------------------
        if topico == comms.T_CMD_INICIAR_OP:
            self._procesar_comando_inicio(mensaje)

        # ---------------------------------------------------------------------
        # Comandos de servos.
        # ---------------------------------------------------------------------
        elif topico == comms.T_CMD_BASE_MOVER:
            self._procesar_comando_servo("base", mensaje)

        elif topico == comms.T_CMD_BRAZO_MOVER:
            self._procesar_comando_servo("brazo", mensaje)

        elif topico == comms.T_CMD_SERVO_MOVER:
            # Tópico viejo: por compatibilidad mueve la base.
            self._procesar_comando_servo("base", mensaje)

        # ---------------------------------------------------------------------
        # Comandos de LED individuales.
        # ---------------------------------------------------------------------
        elif topico == comms.T_CMD_LED_ESTADO_AZUL:
            self._procesar_comando_led("AZUL", mensaje)

        elif topico == comms.T_CMD_LED_ESTADO_AMARILLO:
            self._procesar_comando_led("AMARILLO", mensaje)

        elif topico == comms.T_CMD_LED_ESTADO_ROJO:
            self._procesar_comando_led("ROJO", mensaje)

        elif topico == comms.T_CMD_LED_PARPADEAR:
            self._procesar_comando_led_parpadear(mensaje)

        # ---------------------------------------------------------------------
        # Buzzer.
        # ---------------------------------------------------------------------
        elif topico == comms.T_CMD_BUZZER:
            self._procesar_comando_buzzer(mensaje)

        # ---------------------------------------------------------------------
        # Estado seguro.
        # ---------------------------------------------------------------------
        elif topico == comms.T_CMD_SEGURO:
            self._activar_estado_seguro()

        else:
            print("Tópico no manejado:", topico)

    # -------------------------------------------------------------------------
    def _suscribir_comandos(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Suscribe el ESP32 a todos los tópicos de comando necesarios.

        Devuelve:
            Nada.
        """

        self.mqttBroker.suscribir(comms.T_CMD_INICIAR_OP)

        self.mqttBroker.suscribir(comms.T_CMD_BASE_MOVER)
        self.mqttBroker.suscribir(comms.T_CMD_BRAZO_MOVER)
        self.mqttBroker.suscribir(comms.T_CMD_SERVO_MOVER)

        self.mqttBroker.suscribir(comms.T_CMD_LED_ESTADO_AZUL)
        self.mqttBroker.suscribir(comms.T_CMD_LED_ESTADO_AMARILLO)
        self.mqttBroker.suscribir(comms.T_CMD_LED_ESTADO_ROJO)
        self.mqttBroker.suscribir(comms.T_CMD_LED_PARPADEAR)

        self.mqttBroker.suscribir(comms.T_CMD_BUZZER)
        self.mqttBroker.suscribir(comms.T_CMD_SEGURO)

    # -------------------------------------------------------------------------
    def _publicar_valores_iniciales(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Publica valores iniciales para que Raspberry/interfaz tengan un
            estado conocido desde el arranque.

        Devuelve:
            Nada.
        """

        self._publicar(comms.T_SENSOR_PIR, "false")
        self._publicar(comms.T_SENSOR_ULTRASONICO, "null")
        self._publicar(comms.T_SENSOR_JOYSTICK_BASE, "0")
        self._publicar(comms.T_SENSOR_DIRECCION_BASE, "CENTRO")
        self._publicar(comms.T_ACTUADOR_BASE_GRADOS, "90")
        self._publicar(comms.T_ACTUADOR_BRAZO_GRADOS, "90")

    # -------------------------------------------------------------------------
    def _publicar_datos_sensores(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Publica por MQTT las lecturas actuales de sensores y posiciones de
            actuadores. Usa intervalo para no saturar la red.

        Devuelve:
            Nada.
        """

        actual = time.ticks_ms()

        if time.ticks_diff(actual, self._ultimo_envio_ms) < self._intervalo_envio_ms:
            return

        self._ultimo_envio_ms = actual

        resumen = self._sensores.obtener_resumen()

        presencia = resumen.get("presencia", False)
        distancia = resumen.get("distancia_cm", None)
        joystick = resumen.get("joystick_base", 0)
        direccion = resumen.get("direccion_base", "CENTRO")

        angulo_base = self._actuadores.obtener_posicion_base()

        # El brazo puede estar preparado aunque no se use en la demo.
        try:
            angulo_brazo = self._actuadores.obtener_posicion_brazo()
        except Exception:
            angulo_brazo = 90

        presencia_txt = "true" if presencia else "false"
        distancia_txt = "null" if distancia is None else str(round(distancia, 2))

        self._publicar(comms.T_SENSOR_PIR, presencia_txt)
        self._publicar(comms.T_SENSOR_ULTRASONICO, distancia_txt)
        self._publicar(comms.T_SENSOR_JOYSTICK_BASE, str(joystick))
        self._publicar(comms.T_SENSOR_DIRECCION_BASE, direccion)
        self._publicar(comms.T_ACTUADOR_BASE_GRADOS, str(angulo_base))
        self._publicar(comms.T_ACTUADOR_BRAZO_GRADOS, str(angulo_brazo))

        print(
            "PIR:", presencia_txt,
            "| Distancia:", distancia_txt,
            "| Joystick:", joystick,
            "| Dirección:", direccion,
            "| Base:", angulo_base,
            "| Brazo:", angulo_brazo
        )

    # -------------------------------------------------------------------------
    def _procesar_comando_inicio(self, mensaje):
        """
        Parámetros:
            mensaje: texto del comando de inicio.

        Hace:
            Cambia entre estado OPERANDO y ESPERA.

        Devuelve:
            Nada.
        """

        mensaje = mensaje.lower()

        if mensaje in ("on", "iniciar", "true", "1"):
            self.transicion(ESTADO_OPERANDO)
            self._publicar_estado("Operando")

        elif mensaje in ("off", "detener", "false", "0"):
            self.transicion(ESTADO_ESPERA)
            self._publicar_estado("Esperando instrucciones")

        else:
            self._publicar_error("Comando de inicio inválido")

    # -------------------------------------------------------------------------
    def _procesar_comando_servo(self, servomotor, mensaje):
        """
        Parámetros:
            servomotor: "base" o "brazo".
            mensaje: ángulo como texto o JSON.

        Hace:
            Interpreta el ángulo recibido y mueve el servomotor indicado usando
            la HAL.

        Devuelve:
            Nada.
        """

        try:
            angulo = self._extraer_angulo(mensaje)

            if servomotor == "base":
                angulo_final = self._actuadores.mover_base(angulo)
                self._publicar(comms.T_ACTUADOR_BASE_GRADOS, str(angulo_final))
                print("Base movida por MQTT a:", angulo_final)

            elif servomotor == "brazo":
                angulo_final = self._actuadores.mover_brazo(angulo)
                self._publicar(comms.T_ACTUADOR_BRAZO_GRADOS, str(angulo_final))
                print("Brazo movido por MQTT a:", angulo_final)

            else:
                self._publicar_error("Servomotor no reconocido")

        except Exception as error:
            print("Error al mover servo por MQTT:", error)
            self._publicar_error("Comando de servo inválido")

    # -------------------------------------------------------------------------
    def _procesar_comando_led(self, led, mensaje):
        """
        Parámetros:
            led: "ROJO", "AMARILLO" o "AZUL".
            mensaje: "on", "off" o "blink".

        Hace:
            Controla el LED indicado usando la HAL.

        Devuelve:
            Nada.
        """

        mensaje = mensaje.lower()

        if mensaje == "on":
            self._actuadores.encender_led(led)

        elif mensaje == "off":
            self._actuadores.apagar_led(led)

        elif mensaje == "blink":
            self._actuadores.parpadear_led(led)

        else:
            self._publicar_error("Comando de LED inválido")

    # -------------------------------------------------------------------------
    def _procesar_comando_led_parpadear(self, mensaje):
        """
        Parámetros:
            mensaje: JSON con led, veces e intervalo_ms.

        Hace:
            Parpadea el LED solicitado.

        Devuelve:
            Nada.
        """

        try:
            datos = ujson.loads(mensaje)

            led = datos.get("led", "AZUL")
            veces = int(datos.get("veces", 3))
            intervalo_ms = int(datos.get("intervalo_ms", 200))

            self._actuadores.parpadear_led(led, veces, intervalo_ms)

        except Exception as error:
            print("Error al parpadear LED:", error)
            self._publicar_error("Comando de parpadeo inválido")

    # -------------------------------------------------------------------------
    def _procesar_comando_buzzer(self, mensaje):
        """
        Parámetros:
            mensaje: "lista", "quieta" o "fin".

        Hace:
            Ejecuta señales sonoras usando la HAL.

        Devuelve:
            Nada.
        """

        mensaje = mensaje.lower()

        if mensaje == "lista":
            self._ejecutar_senal("lista")

        elif mensaje == "quieta":
            self._ejecutar_senal("quieta")

        elif mensaje == "fin":
            self._ejecutar_senal("fin")

        else:
            self._publicar_error("Comando de buzzer inválido")

    # -------------------------------------------------------------------------
    def _activar_estado_seguro(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Coloca los actuadores en estado seguro y vuelve a ESPERA.

        Devuelve:
            Nada.
        """

        if self._actuadores is not None:
            self._actuadores.estado_seguro()

        self.transicion(ESTADO_ESPERA)
        self._publicar_estado("Estado seguro")

    # -------------------------------------------------------------------------
    def _extraer_angulo(self, mensaje):
        """
        Parámetros:
            mensaje: texto simple o JSON.

        Hace:
            Extrae un ángulo desde:
              - "90"
              - {"angulo": 90}

        Devuelve:
            Ángulo entero entre 0 y 180.
        """

        mensaje = mensaje.strip()

        if mensaje.startswith("{"):
            datos = ujson.loads(mensaje)
            angulo = int(datos.get("angulo", 90))
        else:
            angulo = int(mensaje)

        if angulo < 0:
            angulo = 0

        if angulo > 180:
            angulo = 180

        return angulo

    # -------------------------------------------------------------------------
    def _ejecutar_senal(self, tipo):
        """
        Parámetros:
            tipo: "lista", "quieta" o "fin".

        Hace:
            Ejecuta señales del buzzer. Soporta nombres con ñ y nombres sin ñ,
            por si después agregan alias en dispositivos.py.

        Devuelve:
            Nada.
        """

        if self._actuadores is None:
            return

        if tipo == "lista":
            metodo = getattr(self._actuadores, "senal_lista", None)

            if metodo is None:
                metodo = getattr(self._actuadores, "señal_lista", None)

            if metodo is not None:
                metodo()

        elif tipo == "quieta":
            metodo = getattr(self._actuadores, "senal_quieta", None)

            if metodo is None:
                metodo = getattr(self._actuadores, "señal_quieta", None)

            if metodo is not None:
                metodo()

        elif tipo == "fin":
            metodo = getattr(self._actuadores, "senal_fin_sesion", None)

            if metodo is None:
                metodo = getattr(self._actuadores, "señal_fin_sesion", None)

            if metodo is not None:
                metodo()

    # -------------------------------------------------------------------------
    def _publicar_estado(self, estado):
        """
        Parámetros:
            estado: texto del estado.

        Hace:
            Publica el estado solo si cambió, para evitar saturar MQTT.

        Devuelve:
            Nada.
        """

        if estado != self._ultimo_estado_publicado:
            self._ultimo_estado_publicado = estado
            self._publicar(comms.T_SISTEMA_ESTADO, estado)

    # -------------------------------------------------------------------------
    def _publicar_error(self, mensaje):
        """
        Parámetros:
            mensaje: descripción del error.

        Hace:
            Publica un error por MQTT.

        Devuelve:
            Nada.
        """

        self._publicar(comms.T_SISTEMA_ERROR, mensaje)

    # -------------------------------------------------------------------------
    def _publicar(self, topico, mensaje):
        """
        Parámetros:
            topico: tópico MQTT.
            mensaje: mensaje a publicar.

        Hace:
            Publica por MQTT si el broker ya fue creado.

        Devuelve:
            Nada.
        """

        if self.mqttBroker is not None:
            try:
                self.mqttBroker.publicar(topico, str(mensaje))
            except Exception as error:
                print("Error publicando MQTT:", error)

    # -------------------------------------------------------------------------
    def _checar_mqtt(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Revisa mensajes pendientes del broker MQTT.

        Devuelve:
            Nada.
        """

        if self.mqttBroker is not None:
            try:
                self.mqttBroker.checar_mensajes()
            except Exception as error:
                print("Error revisando mensajes MQTT:", error)

    # -------------------------------------------------------------------------
    def _decodificar(self, dato):
        """
        Parámetros:
            dato: bytes o texto.

        Hace:
            Convierte bytes a string UTF-8 cuando sea necesario.

        Devuelve:
            Texto decodificado.
        """

        if isinstance(dato, bytes):
            return dato.decode("utf-8")

        return str(dato)
