# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/raspberry/comunicacion/mqtt_bridge.py
#
# OBJETIVO:
# Conectar la interfaz con Mosquitto. Recibe datos del ESP32 y de la IA,
# actualiza Tkinter y publica comandos hacia ESP32/IA.
# =============================================================================

import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


class MQTTBridge:
    """
    Puente MQTT entre Raspberry, ESP32, IA e interfaz.
    """

    # Datos recibidos desde ESP32.
    T_SISTEMA_ESTADO = "sistema/estado"
    T_SISTEMA_ERROR = "sistema/error"

    T_SENSOR_PIR = "sistema/sensores/pir"
    T_SENSOR_ULTRASONICO = "sistema/sensores/ultrasonico"
    T_SENSOR_JOYSTICK_BASE = "sistema/sensores/joystick_base"
    T_SENSOR_DIRECCION_BASE = "sistema/sensores/direccion_base"

    T_ACTUADOR_BASE_GRADOS = "sistema/actuadores/base/grados"
    T_ACTUADOR_BRAZO_GRADOS = "sistema/actuadores/brazo/grados"

    # Datos publicados por IA.
    T_IA_RESULTADO = "sistema/ia/resultado"
    T_ALERTA_ULTIMA = "sistema/alertas/ultima"

    # Comandos hacia ESP32 / IA.
    T_CMD_INICIAR_OP = "sistema/cmd/iniciar"
    T_CMD_BASE_MOVER = "sistema/cmd/base/mover"
    T_CMD_BRAZO_MOVER = "sistema/cmd/brazo/mover"
    T_CMD_SEGURO = "sistema/cmd/seguro"
    T_CMD_MODO_SISTEMA = "sistema/cmd/modo"
    T_CMD_IA_ESTADO = "sistema/cmd/ia/estado"

    T_CMD_LED_AZUL = "sistema/cmd/led/azul/estado"
    T_CMD_BUZZER = "sistema/cmd/buzzer/senal"

    def __init__(self, vista=None, host="192.168.4.1", puerto=1884, usuario="admin", clave="123", cliente_id="raspberry_interfaz_canma"):
        """
        Parametros:
            vista: instancia de VistaPantalla.
            host: IP de Mosquitto.
            puerto: puerto MQTT.
            usuario: usuario MQTT.
            clave: clave MQTT.
            cliente_id: identificador del cliente.
        """

        if mqtt is None:
            raise ImportError("No esta instalado paho-mqtt. Instala con: python3 -m pip install paho-mqtt")

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
            self.cliente.username_pw_set(username=self.usuario, password=self.clave)

        self.cliente.on_connect = self._on_connect
        self.cliente.on_message = self._on_message
        self.cliente.on_disconnect = self._on_disconnect

    # ------------------------------------------------------------------
    def _crear_cliente_mqtt(self):
        """
        Hace:
            Crea cliente MQTT compatible con paho nuevo y viejo.
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

    # ------------------------------------------------------------------
    def iniciar(self):
        """
        Hace:
            Conecta a Mosquitto e inicia loop en segundo plano.
        """

        print("Conectando a Mosquitto...")
        print("Broker:", self.host)
        print("Puerto:", self.puerto)
        self.cliente.connect(self.host, self.puerto, 60)
        self.cliente.loop_start()

    # ------------------------------------------------------------------
    def detener(self):
        """
        Hace:
            Detiene MQTT.
        """

        try:
            self.cliente.loop_stop()
            self.cliente.disconnect()
        except Exception as error:
            print("Error al detener MQTT:", error)

    # ------------------------------------------------------------------
    def publicar(self, topico, mensaje):
        """
        Parametros:
            topico: topico MQTT.
            mensaje: mensaje a publicar.
        """

        mensaje = str(mensaje)
        print("PUBLICANDO MQTT:", topico, mensaje)

        try:
            self.cliente.publish(topico, mensaje)
        except Exception as error:
            print("Error publicando MQTT:", error)

    # ------------------------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback de conexion.
        """

        if rc == 0:
            self.conectado = True
            print("MQTT conectado correctamente")
            self._suscribir_topicos()
            self._actualizar_vista_seguro(estado_sistema="MQTT conectado")
        else:
            self.conectado = False
            print("Error de conexion MQTT. Codigo:", rc)
            self._actualizar_vista_seguro(estado_sistema="Error MQTT")

    # ------------------------------------------------------------------
    def _on_disconnect(self, client, userdata, rc=None):
        """
        Callback de desconexion.
        """

        self.conectado = False
        print("MQTT desconectado")
        self._actualizar_vista_seguro(estado_sistema="MQTT desconectado")

    # ------------------------------------------------------------------
    def _on_message(self, client, userdata, msg):
        """
        Callback de mensaje recibido.
        """

        topico = msg.topic

        try:
            mensaje = msg.payload.decode("utf-8")
        except Exception:
            mensaje = str(msg.payload)

        tiempo = datetime.now().strftime("%H:%M:%S")
        self.ultimo_mensaje = (topico, mensaje)
        print("[{}] {}: {}".format(tiempo, topico, mensaje))

        if topico == self.T_SISTEMA_ESTADO:
            self._actualizar_vista_seguro(estado_sistema=mensaje)

        elif topico == self.T_SISTEMA_ERROR:
            self._actualizar_vista_seguro(error_sistema=mensaje)

        elif topico == self.T_SENSOR_PIR:
            self._actualizar_vista_seguro(movimiento_usuario=mensaje)

        elif topico == self.T_SENSOR_ULTRASONICO:
            self._actualizar_vista_seguro(distancia_cm=mensaje)

        elif topico == self.T_SENSOR_JOYSTICK_BASE:
            self._actualizar_vista_seguro(joystick_base=mensaje)

        elif topico == self.T_SENSOR_DIRECCION_BASE:
            self._actualizar_vista_seguro(direccion_base=mensaje)

        elif topico == self.T_ACTUADOR_BASE_GRADOS:
            self._actualizar_vista_seguro(grados_camara=mensaje)

        elif topico == self.T_ACTUADOR_BRAZO_GRADOS:
            pass

        elif topico == self.T_IA_RESULTADO:
            self._actualizar_vista_seguro(resultado_ia=mensaje)

        elif topico == self.T_ALERTA_ULTIMA:
            self._actualizar_vista_seguro(alerta_ultima=mensaje)

    # ------------------------------------------------------------------
    def _suscribir_topicos(self):
        """
        Hace:
            Suscribe a topicos de sensores, actuadores, IA y alertas.
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
            self.T_IA_RESULTADO,
            self.T_ALERTA_ULTIMA,
        ]

        for topico in topicos:
            self.cliente.subscribe(topico)
            print("Suscrito a:", topico)

    # ------------------------------------------------------------------
    def _actualizar_vista_seguro(self, **datos):
        """
        Hace:
            Actualiza Tkinter desde el hilo principal usando after.
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

    # ------------------------------------------------------------------
    def enviar_on(self):
        self.publicar(self.T_CMD_MODO_SISTEMA, "sensores")
        self.publicar(self.T_CMD_INICIAR_OP, "on")

    def enviar_off(self):
        self.publicar(self.T_CMD_INICIAR_OP, "off")
        self.publicar(self.T_CMD_MODO_SISTEMA, "reposo")

    def activar_ia(self):
        self.publicar(self.T_CMD_INICIAR_OP, "off")
        self.publicar(self.T_CMD_MODO_SISTEMA, "ia")
        self.publicar(self.T_CMD_IA_ESTADO, "on")

    def desactivar_ia(self):
        self.publicar(self.T_CMD_IA_ESTADO, "off")
        self.publicar(self.T_CMD_MODO_SISTEMA, "reposo")
        self.publicar(self.T_CMD_SEGURO, "on")

    def mover_base(self, angulo):
        self.publicar(self.T_CMD_BASE_MOVER, str(angulo))

    def estado_seguro(self):
        self.publicar(self.T_CMD_SEGURO, "on")

    def probar_led_azul(self):
        self.publicar(self.T_CMD_LED_AZUL, "blink")

    def probar_buzzer(self):
        self.publicar(self.T_CMD_BUZZER, "lista")


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

