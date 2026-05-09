"""
OBJETIVO: Módulo de comunicación MQTT para ESP32 en MicroPython.
          Publica telemetría de todos los sensores del riel semicircular y
          se suscribe a comandos para todos los actuadores, delegando
          SIEMPRE la ejecución a la HAL (dispositivos.py). Ninguna línea
          de este archivo accede directamente a machine.Pin o machine.PWM.
INTEGRANTES: Macias Campos Ariadne Lizett
             Soto Garnica Ari Adair
             Lira Gamiño Luis Fernando
PROYECTO: Sistema de Riel Semicircular Fotográfico 180°
"""

import time
import json
import network
from umqtt.simple import MQTTClient

# Importar la HAL — única interfaz con el hardware físico
from dispositivos import CajaSensores, CajaActuadores, VELOCIDAD_NORMAL, VELOCIDAD_LENTA


# =============================================================================
# CONFIGURACIÓN DE RED Y BROKER
# =============================================================================

WIFI_SSID     = "TU_RED_WIFI"          # Nombre de la red Wi-Fi
WIFI_PASSWORD = "TU_CONTRASENA"        # Contraseña de la red Wi-Fi

BROKER_HOST   = "192.168.1.100"        # IP del broker MQTT (ej. Raspberry Pi con Mosquitto)
BROKER_PORT   = 1883                   # Puerto MQTT estándar (sin TLS)
CLIENT_ID     = "riel_esp32"           # ID único del cliente en el broker
KEEP_ALIVE_S  = 60                     # Intervalo keep-alive en segundos

# Reintentos de reconexión antes de reiniciar el sistema
MAX_REINTENTOS_WIFI   = 20
MAX_REINTENTOS_BROKER = 5


# =============================================================================
# TABLA DE TÓPICOS MQTT
# Jerarquía: riel/<subsistema>/<dispositivo>/<acción>
# =============================================================================

# --- PUBLICACIÓN (ESP32 → Broker → Servidor Python) -------------------------
T_SENSOR_PIR         = "riel/sensores/pir"           # bool: presencia detectada
T_SENSOR_LIM_IZQ     = "riel/sensores/limite_izq"    # bool: fin de carrera izquierdo
T_SENSOR_LIM_DER     = "riel/sensores/limite_der"    # bool: fin de carrera derecho
T_MOTOR_POSICION     = "riel/actuadores/motor/posicion"  # float: grados actuales
T_SISTEMA_ESTADO     = "riel/sistema/estado"         # str: IDLE / BARRIENDO / HOMING / ERROR
T_SISTEMA_ERROR      = "riel/sistema/error"          # str: descripción del error

# --- SUSCRIPCIÓN (Servidor Python → Broker → ESP32) -------------------------
T_CMD_MOTOR_MOVER    = "riel/cmd/motor/mover"        # JSON: {"angulo": float, "velocidad": int}
T_CMD_MOTOR_INICIO   = "riel/cmd/motor/inicio"       # cualquier payload: ejecuta homing
T_CMD_LED_ESTADO     = "riel/cmd/led/estado"         # str: "on" | "off" | "blink"
T_CMD_LED_PARPADEAR  = "riel/cmd/led/parpadear"      # JSON: {"veces": int, "intervalo_ms": int}
T_CMD_BUZZER         = "riel/cmd/buzzer/señal"       # str: "lista" | "quieta" | "fin"
T_CMD_SEGURO         = "riel/cmd/seguro"             # cualquier payload: estado_seguro()


# =============================================================================
# CLASE: GestorMQTT
# Maneja conexión, publicación y suscripción. Llama solo a la HAL.
# =============================================================================

class GestorMQTT:
    """
    Encapsula toda la lógica MQTT del sistema de riel fotográfico.
    La clase instancia internamente CajaSensores y CajaActuadores para que
    ningún código externo manipule el hardware directamente.
    """

    def __init__(self):
        """Inicializa la HAL, el cliente MQTT y el estado del sistema."""
        # Instanciar HAL — único punto de contacto con el hardware
        self._sensores   = CajaSensores()
        self._actuadores = CajaActuadores()

        # Cliente MQTT (se configura después de conectar Wi-Fi)
        self._cliente = None

        # Estado actual de la máquina de estados del sistema
        self._estado_sistema = "IDLE"

        # Contadores para telemetría no bloqueante
        self._ultimo_envio_ms = 0
        self._intervalo_envio_ms = 500   # publicar sensores cada 500 ms

    # -------------------------------------------------------------------------
    # CONEXIÓN WI-FI
    # -------------------------------------------------------------------------

    def conectar_wifi(self):
        """
        Intenta conectar a la red Wi-Fi usando las credenciales configuradas.
        Espera hasta MAX_REINTENTOS_WIFI veces antes de declarar error.
        Devuelve: True si conectó, False en caso contrario.
        """
        sta = network.WLAN(network.STA_IF)
        sta.active(True)

        if sta.isconnected():
            print("[WiFi] Ya conectado:", sta.ifconfig()[0])
            return True

        sta.connect(WIFI_SSID, WIFI_PASSWORD)
        print(f"[WiFi] Conectando a '{WIFI_SSID}'", end="")

        for _ in range(MAX_REINTENTOS_WIFI):
            if sta.isconnected():
                print("\n[WiFi] IP:", sta.ifconfig()[0])
                return True
            print(".", end="")
            time.sleep(1)

        print("\n[WiFi] ERROR: No se pudo conectar.")
        return False

    # -------------------------------------------------------------------------
    # CONEXIÓN AL BROKER MQTT
    # -------------------------------------------------------------------------

    def conectar_broker(self):
        """
        Crea el cliente MQTT, asigna el callback de mensajes entrantes y
        se conecta al broker. Suscribe a todos los tópicos de comandos.
        Devuelve: True si conectó correctamente, False en caso de error.
        """
        try:
            self._cliente = MQTTClient(
                client_id   = CLIENT_ID,
                server      = BROKER_HOST,
                port        = BROKER_PORT,
                keepalive   = KEEP_ALIVE_S
            )
            # Registrar callback antes de conectar
            self._cliente.set_callback(self._callback_mensaje)
            self._cliente.connect()

            # Suscribir a todos los tópicos de comandos con QoS 1
            topicos_cmd = [
                T_CMD_MOTOR_MOVER,
                T_CMD_MOTOR_INICIO,
                T_CMD_LED_ESTADO,
                T_CMD_LED_PARPADEAR,
                T_CMD_BUZZER,
                T_CMD_SEGURO,
            ]
            for topico in topicos_cmd:
                self._cliente.subscribe(topico)
                print(f"[MQTT] Suscrito a: {topico}")

            print(f"[MQTT] Conectado al broker {BROKER_HOST}:{BROKER_PORT}")
            self._publicar_estado("IDLE")
            return True

        except Exception as e:
            print(f"[MQTT] ERROR al conectar broker: {e}")
            return False

    # -------------------------------------------------------------------------
    # CALLBACK DE MENSAJES ENTRANTES
    # Recibe comandos del servidor Python y los delega a la HAL.
    # -------------------------------------------------------------------------

    def _callback_mensaje(self, topico, payload):
        """
        Parámetros:
          topico  (bytes) — tópico MQTT del mensaje recibido.
          payload (bytes) — cuerpo del mensaje en bytes.
        Hace: decodifica el tópico, parsea el payload y llama al método
              correspondiente de la HAL. NUNCA accede a hardware directamente.
        Devuelve: nada.
        """
        topico  = topico.decode("utf-8")
        payload = payload.decode("utf-8").strip()
        print(f"[CMD] {topico} → '{payload}'")

        try:
            # --- Comando: mover motor un ángulo ---
            if topico == T_CMD_MOTOR_MOVER:
                # Payload esperado: {"angulo": 45.0, "velocidad": 600}
                datos = json.loads(payload)
                angulo    = float(datos.get("angulo", 0))
                velocidad = int(datos.get("velocidad", VELOCIDAD_NORMAL))

                self._publicar_estado("BARRIENDO")
                self._actuadores.mover_angulo(angulo, velocidad)

                # Publicar nueva posición tras el movimiento
                pos = self._actuadores.obtener_posicion_grados()
                self._cliente.publish(T_MOTOR_POSICION, str(pos))
                self._publicar_estado("IDLE")

            # --- Comando: homing (ir al extremo izquierdo) ---
            elif topico == T_CMD_MOTOR_INICIO:
                self._publicar_estado("HOMING")
                self._actuadores.ir_a_inicio()
                self._cliente.publish(T_MOTOR_POSICION, "0.0")
                self._publicar_estado("IDLE")

            # --- Comando: control del LED ---
            elif topico == T_CMD_LED_ESTADO:
                if payload == "on":
                    self._actuadores.encender_led()
                elif payload == "off":
                    self._actuadores.apagar_led()
                elif payload == "blink":
                    # Parpadeo con parámetros por defecto (3 veces, 200 ms)
                    self._actuadores.parpadear_led()

            # --- Comando: parpadeo con parámetros personalizados ---
            elif topico == T_CMD_LED_PARPADEAR:
                # Payload esperado: {"veces": 5, "intervalo_ms": 150}
                datos      = json.loads(payload)
                veces      = int(datos.get("veces", 3))
                intervalo  = int(datos.get("intervalo_ms", 200))
                self._actuadores.parpadear_led(veces, intervalo)

            # --- Comando: señal de buzzer ---
            elif topico == T_CMD_BUZZER:
                if payload == "lista":
                    self._actuadores.señal_lista()
                elif payload == "quieta":
                    self._actuadores.señal_quieta()
                elif payload == "fin":
                    self._actuadores.señal_fin_sesion()

            # --- Comando: estado seguro de emergencia ---
            elif topico == T_CMD_SEGURO:
                # Detiene TODO el hardware de forma segura
                self._actuadores.estado_seguro()
                self._publicar_estado("IDLE")
                print("[HAL] Estado seguro aplicado a todos los actuadores.")

        except Exception as e:
            # Publicar el error al servidor para trazabilidad
            self._cliente.publish(T_SISTEMA_ERROR, f"Callback error en '{topico}': {e}")
            print(f"[ERROR] {e}")

    # -------------------------------------------------------------------------
    # PUBLICACIÓN DE TELEMETRÍA DE SENSORES
    # -------------------------------------------------------------------------

    def _publicar_sensores(self):
        """
        Lee todos los sensores vía HAL y publica sus valores al broker.
        Utiliza un timestamp de milisegundos para control de frecuencia.
        Devuelve: nada.
        """
        # Leer todos los sensores en una sola llamada a la HAL
        resumen = self._sensores.obtener_resumen()

        # Publicar cada sensor en su tópico correspondiente
        self._cliente.publish(T_SENSOR_PIR,     "1" if resumen["presencia"]   else "0")
        self._cliente.publish(T_SENSOR_LIM_IZQ, "1" if resumen["limite_izq"]  else "0")
        self._cliente.publish(T_SENSOR_LIM_DER, "1" if resumen["limite_der"]  else "0")

        # Posición del motor como dato de estado del actuador
        pos = self._actuadores.obtener_posicion_grados()
        self._cliente.publish(T_MOTOR_POSICION, str(pos))

    def _publicar_estado(self, estado):
        """
        Publica el estado general del sistema (IDLE, BARRIENDO, HOMING, ERROR).
        También actualiza el atributo interno para coherencia del objeto.
        """
        self._estado_sistema = estado
        self._cliente.publish(T_SISTEMA_ESTADO, estado)
        print(f"[ESTADO] {estado}")

    # -------------------------------------------------------------------------
    # LOOP PRINCIPAL — no bloqueante
    # -------------------------------------------------------------------------

    def loop(self):
        """
        Ejecuta el ciclo principal de comunicación MQTT de forma no bloqueante.
        1. Comprueba mensajes entrantes del broker.
        2. Publica telemetría de sensores según el intervalo configurado.
        Devuelve: nada. Debe llamarse repetidamente desde main.py.
        """
        # Verificar mensajes pendientes (no bloqueante)
        self._cliente.check_msg()

        # Publicar sensores solo cuando pase el intervalo configurado
        ahora_ms = time.ticks_ms()
        if time.ticks_diff(ahora_ms, self._ultimo_envio_ms) >= self._intervalo_envio_ms:
            self._publicar_sensores()
            self._ultimo_envio_ms = ahora_ms

    # -------------------------------------------------------------------------
    # INICIALIZACIÓN COMPLETA (Wi-Fi + Broker)
    # -------------------------------------------------------------------------

    def iniciar(self):
        """
        Método de conveniencia para inicializar todo el sistema de comunicación.
        Secuencia: Wi-Fi → Broker → Señal sonora de listo → Loop.
        Devuelve: True si el sistema inició correctamente, False en caso contrario.
        """
        if not self.conectar_wifi():
            self._actuadores.estado_seguro()
            return False

        intentos = 0
        while intentos < MAX_REINTENTOS_BROKER:
            if self.conectar_broker():
                # Señal de inicio exitoso (HAL)
                self._actuadores.parpadear_led(3, 150)
                self._actuadores.señal_lista()
                return True
            intentos += 1
            time.sleep(2)

        self._actuadores.estado_seguro()
        return False


# =============================================================================
# PUNTO DE ENTRADA — para prueba directa del módulo
# =============================================================================

if __name__ == "__main__":
    gestor = GestorMQTT()

    if gestor.iniciar():
        print("[MQTT] Sistema listo. Iniciando loop principal...")
        while True:
            try:
                gestor.loop()
                time.sleep_ms(50)   # pequeño delay para estabilidad del scheduler
            except OSError as e:
                # Reconexión ante caída de red
                print(f"[MQTT] Conexión perdida: {e}. Reconectando...")
                time.sleep(3)
                gestor.iniciar()
    else:
        print("[MQTT] ERROR CRÍTICO: No se pudo iniciar el sistema.")

