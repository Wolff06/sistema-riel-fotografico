# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# ARCHIVO:
# sistema/raspberry/comunicacion/mqtt_bridge.py
#
# OBJETIVO:
# Conectar la interfaz de Raspberry con el broker Mosquitto.
# Este archivo recibe datos MQTT publicados por el ESP32 y actualiza la interfaz.
# También permite que la interfaz publique comandos MQTT hacia el ESP32.
#
# FLUJO:
# ESP32 → Mosquitto → mqtt_bridge.py → vista_pantalla.py
# vista_pantalla.py → mqtt_bridge.py → Mosquitto → ESP32
# =============================================================================

import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


class MQTTBridge:
    """
    Clase encargada de la comunicación MQTT entre Raspberry y ESP32.

    Responsabilidades:
      - Conectarse al broker Mosquitto.
      - Suscribirse a los tópicos publicados por el ESP32.
      - Actualizar la interfaz de forma segura.
      - Publicar comandos cuando la interfaz lo solicite.
    """

    # =========================================================================
    # TÓPICOS QUE RECIBE LA RASPBERRY DESDE EL ESP32
    # =========================================================================

    T_SISTEMA_ESTADO = "sistema/estado"
    T_SISTEMA_ERROR = "sistema/error"

    T_SENSOR_PIR = "sistema/sensores/pir"
    T_SENSOR_ULTRASONICO = "sistema/sensores/ultrasonico"
    T_SENSOR_JOYSTICK_BASE = "sistema/sensores/joystick_base"
    T_SENSOR_DIRECCION_BASE = "sistema/sensores/direccion_base"

    T_ACTUADOR_BASE_GRADOS = "sistema/actuadores/base/grados"
    T_ACTUADOR_BRAZO_GRADOS = "sistema/actuadores/brazo/grados"

    # =========================================================================
    # TÓPICOS QUE LA RASPBERRY PUBLICA HACIA EL ESP32
    # =========================================================================

    T_CMD_INICIAR_OP = "sistema/cmd/iniciar"
    T_CMD_BASE_MOVER = "sistema/cmd/base/mover"
    T_CMD_BRAZO_MOVER = "sistema/cmd/brazo/mover"
    T_CMD_SEGURO = "sistema/cmd/seguro"

    T_CMD_LED_AZUL = "sistema/cmd/led/azul/estado"
    T_CMD_BUZZER = "sistema/cmd/buzzer/senal"

    def __init__(
        self,
        vista=None,
        host="192.168.4.1",
        puerto=1884,
        usuario="admin",
        clave="123",
        cliente_id="raspberry_interfaz_canma"
    ):
        """
        Parámetros:
            vista: instancia de VistaPantalla.
            host: IP del broker Mosquitto.
            puerto: puerto MQTT.
            usuario: usuario MQTT.
            clave: contraseña MQTT.
            cliente_id: identificador del cliente MQTT.

        Hace:
            Prepara el cliente MQTT, pero no se conecta todavía.

        Devuelve:
            Nada.
        """

        if mqtt is None:
            raise ImportError(
                "No está instalado paho-mqtt. Instala con: "
                "python3 -m pip install paho-mqtt"
            )

        self.vista = vista
        self.host = host
        self.puerto = puerto
        self.usuario = usuario
        self.clave = clave
        self.cliente_id = cliente_id

        self.conectado = False
        self.ultimo_mensaje = None

        self.cliente = self._crear_cliente_mqtt()

        if self.usuario:
            self.cliente.username_pw_set(
                username=self.usuario,
                password=self.clave
            )

        self.cliente.on_connect = self._on_connect
        self.cliente.on_message = self._on_message
        self.cliente.on_disconnect = self._on_disconnect

    # =========================================================================
    # CREACIÓN Y CONTROL DEL CLIENTE MQTT
    # =========================================================================

    def _crear_cliente_mqtt(self):
        """
        Hace:
            Crea el cliente MQTT de forma compatible con versiones recientes
            y antiguas de paho-mqtt.

        Devuelve:
            Cliente MQTT.
        """

        try:
            return mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                client_id=self.cliente_id
            )
        except Exception:
            try:
                return mqtt.Client(client_id=self.cliente_id)
            except Exception:
                return mqtt.Client(self.cliente_id)

    def iniciar(self):
        """
        Hace:
            Conecta al broker Mosquitto y arranca el loop MQTT en segundo plano.

        Devuelve:
            Nada.
        """

        print("Conectando a Mosquitto...")
        print("Broker:", self.host)
        print("Puerto:", self.puerto)

        self.cliente.connect(self.host, self.puerto, 60)
        self.cliente.loop_start()

    def detener(self):
        """
        Hace:
            Detiene el loop MQTT y desconecta el cliente.

        Devuelve:
            Nada.
        """

        try:
            self.cliente.loop_stop()
            self.cliente.disconnect()
        except Exception as error:
            print("Error al detener MQTT:", error)

    def publicar(self, topico, mensaje):
        """
        Parámetros:
            topico: tópico MQTT.
            mensaje: mensaje a publicar.

        Hace:
            Publica un comando hacia el broker Mosquitto.

        Devuelve:
            Nada.
        """

        mensaje = str(mensaje)

        print("PUBLICANDO MQTT:", topico, mensaje)

        try:
            self.cliente.publish(topico, mensaje)
        except Exception as error:
            print("Error publicando MQTT:", error)

    # =========================================================================
    # CALLBACKS MQTT
    # =========================================================================

    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback ejecutado cuando Raspberry se conecta al broker.

        rc = 0 significa conexión correcta.
        """

        if rc == 0:
            self.conectado = True
            print("MQTT conectado correctamente")

            self._suscribir_topicos()

            self._actualizar_vista_seguro(
                estado_sistema="MQTT conectado"
            )

        else:
            self.conectado = False
            print("Error de conexión MQTT. Código:", rc)

            self._actualizar_vista_seguro(
                estado_sistema="Error MQTT"
            )

    def _on_disconnect(self, client, userdata, rc=None):
        """
        Callback ejecutado cuando se pierde la conexión MQTT.
        """

        self.conectado = False
        print("MQTT desconectado")

        self._actualizar_vista_seguro(
            estado_sistema="MQTT desconectado"
        )

    def _on_message(self, client, userdata, msg):
        """
        Callback ejecutado cuando llega un mensaje MQTT.

        Hace:
            Interpreta el tópico recibido y actualiza la interfaz.
        """

        topico = msg.topic

        try:
            mensaje = msg.payload.decode("utf-8")
        except Exception:
            mensaje = str(msg.payload)

        tiempo = datetime.now().strftime("%H:%M:%S")
        self.ultimo_mensaje = (topico, mensaje)

        print(f"[{tiempo}] {topico}: {mensaje}")

        # ---------------------------------------------------------------------
        # Estado general del sistema.
        # ---------------------------------------------------------------------

        if topico == self.T_SISTEMA_ESTADO:
            self._actualizar_vista_seguro(
                estado_sistema=mensaje
            )

        elif topico == self.T_SISTEMA_ERROR:
            self._actualizar_vista_seguro(
                error_sistema=mensaje
            )

        # ---------------------------------------------------------------------
        # Sensores.
        # ---------------------------------------------------------------------

        elif topico == self.T_SENSOR_PIR:
            self._actualizar_vista_seguro(
                movimiento_usuario=mensaje
            )

        elif topico == self.T_SENSOR_ULTRASONICO:
            self._actualizar_vista_seguro(
                distancia_cm=mensaje
            )

        elif topico == self.T_SENSOR_JOYSTICK_BASE:
            self._actualizar_vista_seguro(
                joystick_base=mensaje
            )

        elif topico == self.T_SENSOR_DIRECCION_BASE:
            self._actualizar_vista_seguro(
                direccion_base=mensaje
            )

        # ---------------------------------------------------------------------
        # Posiciones de actuadores.
        # ---------------------------------------------------------------------

        elif topico == self.T_ACTUADOR_BASE_GRADOS:
            self._actualizar_vista_seguro(
                grados_camara=mensaje
            )

        elif topico == self.T_ACTUADOR_BRAZO_GRADOS:
            # Por ahora la interfaz muestra los grados de la cámara/base.
            # Si después agregan tarjeta del brazo, aquí se puede actualizar.
            pass

    # =========================================================================
    # SUSCRIPCIONES
    # =========================================================================

    def _suscribir_topicos(self):
        """
        Hace:
            Suscribe la Raspberry a todos los tópicos necesarios del ESP32.

        Devuelve:
            Nada.
        """

        topicos = [
            self.T_SISTEMA_ESTADO,
            self.T_SISTEMA_ERROR,
            self.T_SENSOR_PIR,
            self.T_SENSOR_ULTRASONICO,
            self.T_SENSOR_JOYSTICK_BASE,
            self.T_SENSOR_DIRECCION_BASE,
            self.T_ACTUADOR_BASE_GRADOS,
            self.T_ACTUADOR_BRAZO_GRADOS,
        ]

        for topico in topicos:
            self.cliente.subscribe(topico)
            print("Suscrito a:", topico)

        # También se puede escuchar todo para depuración:
        # self.cliente.subscribe("sistema/#")

    # =========================================================================
    # ACTUALIZACIÓN SEGURA DE TKINTER
    # =========================================================================

    def _actualizar_vista_seguro(self, **datos):
        """
        Parámetros:
            datos: argumentos que se enviarán a vista.actualizar_datos_esp32().

        Hace:
            Actualiza la interfaz usando pantalla.after() para evitar errores
            por actualizar Tkinter desde el hilo de MQTT.

        Devuelve:
            Nada.
        """

        if self.vista is None:
            return

        if not hasattr(self.vista, "actualizar_datos_esp32"):
            return

        try:
            self.vista.pantalla.after(
                0,
                lambda datos=datos: self.vista.actualizar_datos_esp32(**datos)
            )
        except Exception as error:
            print("Error actualizando la vista:", error)

    # =========================================================================
    # MÉTODOS ÚTILES PARA USAR DESDE OTRAS PARTES
    # =========================================================================

    def enviar_on(self):
        """
        Solicita al ESP32 entrar en estado OPERANDO.
        """

        self.publicar(self.T_CMD_INICIAR_OP, "on")

    def enviar_off(self):
        """
        Solicita al ESP32 volver a estado ESPERA.
        """

        self.publicar(self.T_CMD_INICIAR_OP, "off")

    def mover_base(self, angulo):
        """
        Solicita al ESP32 mover la base al ángulo indicado.
        """

        self.publicar(self.T_CMD_BASE_MOVER, str(angulo))

    def estado_seguro(self):
        """
        Solicita al ESP32 activar estado seguro.
        """

        self.publicar(self.T_CMD_SEGURO, "on")

    def probar_led_azul(self):
        """
        Enciende LED azul como prueba.
        """

        self.publicar(self.T_CMD_LED_AZUL, "blink")

    def probar_buzzer(self):
        """
        Activa buzzer como prueba.
        """

        self.publicar(self.T_CMD_BUZZER, "lista")


# =============================================================================
# PRUEBA DIRECTA DEL BRIDGE
# =============================================================================

if __name__ == "__main__":
    bridge = MQTTBridge()

    try:
        bridge.iniciar()
        print("Bridge MQTT iniciado. Presiona Ctrl+C para salir.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Cerrando bridge MQTT...")

    finally:
        bridge.detener()
