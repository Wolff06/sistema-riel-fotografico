"""
OBJETIVO: Servidor MQTT en Python 3 para el sistema de riel semicircular
          fotográfico. Recibe y almacena telemetría de todos los sensores
          con timestamps, expone una interfaz de consola interactiva para
          publicar comandos a todos los actuadores (motor NEMA 17, LED y
          buzzer) y registra toda la actividad en archivo de log.
INTEGRANTES: Macias Campos Ariadne Lizett
             Soto Garnica Ari Adair
             Lira Gamiño Luis Fernando
PROYECTO: Sistema de Riel Semicircular Fotográfico 180°
"""

import json
import time
import threading
import logging
from datetime import datetime
from dataclasses import dataclass, field
import paho.mqtt.client as mqtt   # pip install paho-mqtt


# =============================================================================
# CONFIGURACIÓN DEL BROKER
# =============================================================================

BROKER_HOST = "localhost"   # Cambiar a la IP del broker si es remoto
BROKER_PORT = 1883
CLIENT_ID   = "servidor_python_riel"
KEEP_ALIVE  = 60


# =============================================================================
# TABLA COMPLETA DE TÓPICOS MQTT
# Mapeo 100% de dispositivos del sistema (sensores y actuadores)
# =============================================================================

# ── PUBLICACIÓN: ESP32 → Servidor ───────────────────────────────────────────
T_SENSOR_PIR         = "riel/sensores/pir"
T_SENSOR_LIM_IZQ     = "riel/sensores/limite_izq"
T_SENSOR_LIM_DER     = "riel/sensores/limite_der"
T_MOTOR_POSICION     = "riel/actuadores/motor/posicion"
T_SISTEMA_ESTADO     = "riel/sistema/estado"
T_SISTEMA_ERROR      = "riel/sistema/error"

# ── SUSCRIPCIÓN: Servidor → ESP32 ───────────────────────────────────────────
T_CMD_MOTOR_MOVER    = "riel/cmd/motor/mover"
T_CMD_MOTOR_INICIO   = "riel/cmd/motor/inicio"
T_CMD_LED_ESTADO     = "riel/cmd/led/estado"
T_CMD_LED_PARPADEAR  = "riel/cmd/led/parpadear"
T_CMD_BUZZER         = "riel/cmd/buzzer/señal"
T_CMD_SEGURO         = "riel/cmd/seguro"

# Todos los tópicos de telemetría que el servidor debe escuchar
TOPICOS_TELEMETRIA = [
    T_SENSOR_PIR,
    T_SENSOR_LIM_IZQ,
    T_SENSOR_LIM_DER,
    T_MOTOR_POSICION,
    T_SISTEMA_ESTADO,
    T_SISTEMA_ERROR,
]


# =============================================================================
# CONFIGURACIÓN DE LOGGING
# Escribe en consola y en archivo de log con timestamp
# =============================================================================

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("riel_telemetria.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("ServidorRiel")


# =============================================================================
# CLASE: EstadoSistema
# Almacena el último estado conocido de todos los dispositivos con timestamp
# =============================================================================

@dataclass
class EstadoSistema:
    """
    Objeto de datos que refleja el estado actual del sistema de riel.
    Cada campo se actualiza al recibir el tópico correspondiente.
    El timestamp indica cuándo fue la última actualización recibida.
    """
    pir_presencia   : bool  = False
    limite_izquierdo: bool  = False
    limite_derecho  : bool  = False
    posicion_grados : float = 0.0
    estado_sistema  : str   = "DESCONOCIDO"
    ultimo_error    : str   = ""
    timestamps      : dict  = field(default_factory=dict)  # topico → datetime

    def actualizar(self, topico: str, valor):
        """Actualiza el campo correspondiente y registra el timestamp."""
        self.timestamps[topico] = datetime.now()
        if topico == T_SENSOR_PIR:
            self.pir_presencia = bool(int(valor))
        elif topico == T_SENSOR_LIM_IZQ:
            self.limite_izquierdo = bool(int(valor))
        elif topico == T_SENSOR_LIM_DER:
            self.limite_derecho = bool(int(valor))
        elif topico == T_MOTOR_POSICION:
            self.posicion_grados = float(valor)
        elif topico == T_SISTEMA_ESTADO:
            self.estado_sistema = str(valor)
        elif topico == T_SISTEMA_ERROR:
            self.ultimo_error = str(valor)

    def mostrar(self):
        """Imprime un resumen formateado del estado actual del sistema."""
        sep = "─" * 52
        print(f"\n{sep}")
        print(f"  TELEMETRÍA DEL SISTEMA DE RIEL  —  {datetime.now():%H:%M:%S}")
        print(sep)
        print(f"  PIR (presencia)    : {'✔ DETECTADA' if self.pir_presencia else '✘ Sin presencia'}")
        print(f"  Límite izquierdo   : {'⚠ ACTIVO' if self.limite_izquierdo else 'Libre'}")
        print(f"  Límite derecho     : {'⚠ ACTIVO' if self.limite_derecho else 'Libre'}")
        print(f"  Posición motor     : {self.posicion_grados:>7.2f}°")
        print(f"  Estado sistema     : {self.estado_sistema}")
        if self.ultimo_error:
            print(f"  ⚠ Último error     : {self.ultimo_error}")
        print(sep)


# =============================================================================
# CLASE: ServidorMQTT
# Gestiona la conexión, callbacks y publicación de comandos
# =============================================================================

class ServidorMQTT:
    """
    Servidor MQTT que recibe telemetría de la ESP32 y publica comandos a
    los actuadores. Usa paho-mqtt con callbacks asíncronos en hilo separado.
    """

    def __init__(self):
        self._estado = EstadoSistema()
        self._cliente = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
        self._conectado = threading.Event()

        # Asignar callbacks del ciclo de vida MQTT
        self._cliente.on_connect    = self._on_connect
        self._cliente.on_disconnect = self._on_disconnect
        self._cliente.on_message    = self._on_message

    # -------------------------------------------------------------------------
    # CALLBACKS DEL CLIENTE MQTT
    # -------------------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback invocado al establecer conexión con el broker.
        rc=0 indica éxito. Suscribe a todos los tópicos de telemetría.
        """
        if rc == 0:
            log.info(f"Conectado al broker {BROKER_HOST}:{BROKER_PORT}")
            self._conectado.set()
            # Suscribir a todos los tópicos de telemetría en una sola llamada
            suscripciones = [(t, 1) for t in TOPICOS_TELEMETRIA]
            client.subscribe(suscripciones)
            log.info(f"Suscrito a {len(TOPICOS_TELEMETRIA)} tópicos de telemetría.")
        else:
            log.error(f"Error de conexión al broker. Código: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback invocado al perder la conexión. Registra el evento."""
        self._conectado.clear()
        log.warning(f"Desconectado del broker. Código: {rc}. Reintentando...")

    def _on_message(self, client, userdata, mensaje):
        """
        Callback principal de mensajes entrantes.
        Decodifica el tópico y payload, actualiza el EstadoSistema y
        registra la telemetría con timestamp en el log.
        """
        topico  = mensaje.topic
        payload = mensaje.payload.decode("utf-8").strip()
        ts      = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Actualizar estado interno del sistema
        self._estado.actualizar(topico, payload)

        # Registrar en log con timestamp (cada mensaje de telemetría)
        log.info(f"[{ts}] {topico:45s} → {payload}")

    # -------------------------------------------------------------------------
    # PUBLICACIÓN DE COMANDOS A ACTUADORES
    # -------------------------------------------------------------------------

    def cmd_mover_motor(self, angulo: float, velocidad: int = 600):
        """
        Publica un comando para mover el motor NEMA 17 un ángulo dado.
        Parámetros:
          angulo    — grados a mover (+derecha, -izquierda).
          velocidad — µs entre pulsos STEP (menor = más rápido; mín. recomendado: 400).
        """
        payload = json.dumps({"angulo": angulo, "velocidad": velocidad})
        self._cliente.publish(T_CMD_MOTOR_MOVER, payload, qos=1)
        log.info(f"CMD motor/mover → ángulo={angulo}°, velocidad={velocidad}µs")

    def cmd_homing(self):
        """Publica comando de homing: mueve el carrito al extremo izquierdo."""
        self._cliente.publish(T_CMD_MOTOR_INICIO, "go", qos=1)
        log.info("CMD motor/inicio → homing ejecutado")

    def cmd_led(self, estado: str):
        """
        Controla el LED de estado.
        estado: "on" | "off" | "blink"
        """
        if estado not in ("on", "off", "blink"):
            log.warning(f"Estado de LED no válido: '{estado}'")
            return
        self._cliente.publish(T_CMD_LED_ESTADO, estado, qos=1)
        log.info(f"CMD led/estado → {estado}")

    def cmd_parpadear_led(self, veces: int = 3, intervalo_ms: int = 200):
        """Publica comando de parpadeo con parámetros personalizados."""
        payload = json.dumps({"veces": veces, "intervalo_ms": intervalo_ms})
        self._cliente.publish(T_CMD_LED_PARPADEAR, payload, qos=1)
        log.info(f"CMD led/parpadear → veces={veces}, intervalo={intervalo_ms}ms")

    def cmd_buzzer(self, señal: str):
        """
        Activa una señal del buzzer.
        señal: "lista" | "quieta" | "fin"
        """
        if señal not in ("lista", "quieta", "fin"):
            log.warning(f"Señal de buzzer no válida: '{señal}'")
            return
        self._cliente.publish(T_CMD_BUZZER, señal, qos=1)
        log.info(f"CMD buzzer/señal → {señal}")

    def cmd_estado_seguro(self):
        """Publica comando de emergencia: apaga todos los actuadores de inmediato."""
        self._cliente.publish(T_CMD_SEGURO, "STOP", qos=1)
        log.warning("CMD seguro → ESTADO SEGURO ACTIVADO (todos los actuadores apagados)")

    # -------------------------------------------------------------------------
    # INICIAR Y LOOP
    # -------------------------------------------------------------------------

    def iniciar(self):
        """
        Conecta al broker y lanza el loop de red en un hilo de fondo.
        Bloquea hasta confirmar la conexión o agotar el tiempo de espera.
        Devuelve: True si la conexión fue exitosa.
        """
        self._cliente.connect(BROKER_HOST, BROKER_PORT, KEEP_ALIVE)
        self._cliente.loop_start()   # hilo de red no bloqueante

        if self._conectado.wait(timeout=10):
            return True
        log.error("Tiempo de espera agotado. Verifique que el broker esté activo.")
        return False

    def detener(self):
        """Desconecta limpiamente del broker y detiene el hilo de red."""
        self._cliente.loop_stop()
        self._cliente.disconnect()
        log.info("Servidor MQTT detenido.")

    def obtener_estado(self) -> EstadoSistema:
        """Devuelve el objeto de estado actual para consulta externa."""
        return self._estado


# =============================================================================
# INTERFAZ DE CONSOLA INTERACTIVA
# =============================================================================

MENU = """
╔══════════════════════════════════════════════════════╗
║   CONTROL RIEL SEMICIRCULAR FOTOGRÁFICO 180°         ║
╠══════════════════════════════════════════════════════╣
║  [1] Mover motor (ángulo personalizado)              ║
║  [2] Homing (ir a posición 0°)                       ║
║  [3] LED encender / apagar / blink                   ║
║  [4] LED parpadeo personalizado                      ║
║  [5] Buzzer: señal lista                             ║
║  [6] Buzzer: señal quieta                            ║
║  [7] Buzzer: señal fin de sesión                     ║
║  [8] ESTADO SEGURO (apagar todo)                     ║
║  [9] Mostrar telemetría actual                       ║
║  [0] Salir                                           ║
╚══════════════════════════════════════════════════════╝
"""

def consola_interactiva(servidor: ServidorMQTT):
    """
    Bucle de consola que permite al operador enviar comandos manualmente.
    Corre en el hilo principal mientras el loop MQTT corre en segundo plano.
    """
    print(MENU)
    while True:
        try:
            opcion = input("Selecciona opción: ").strip()

            if opcion == "1":
                angulo = float(input("  Ángulo en grados (+ derecha / - izquierda): "))
                vel    = input("  Velocidad µs [Enter = 600]: ").strip()
                velocidad = int(vel) if vel else 600
                servidor.cmd_mover_motor(angulo, velocidad)

            elif opcion == "2":
                servidor.cmd_homing()

            elif opcion == "3":
                estado = input("  Estado (on/off/blink): ").strip().lower()
                servidor.cmd_led(estado)

            elif opcion == "4":
                veces     = int(input("  Número de parpadeos: ") or "3")
                intervalo = int(input("  Intervalo ms entre parpadeos: ") or "200")
                servidor.cmd_parpadear_led(veces, intervalo)

            elif opcion == "5":
                servidor.cmd_buzzer("lista")

            elif opcion == "6":
                servidor.cmd_buzzer("quieta")

            elif opcion == "7":
                servidor.cmd_buzzer("fin")

            elif opcion == "8":
                confirmacion = input("  ⚠ Confirmar estado seguro (s/n): ").lower()
                if confirmacion == "s":
                    servidor.cmd_estado_seguro()

            elif opcion == "9":
                servidor.obtener_estado().mostrar()

            elif opcion == "0":
                print("Cerrando servidor...")
                break

            else:
                print("  Opción no válida.")

        except (ValueError, KeyboardInterrupt):
            print("\n  Entrada cancelada. Escribe '0' para salir.")


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    servidor = ServidorMQTT()

    if not servidor.iniciar():
        print("ERROR: No se pudo conectar al broker. Verifica la IP y que Mosquitto esté activo.")
        exit(1)

    try:
        consola_interactiva(servidor)
    finally:
        servidor.detener()

