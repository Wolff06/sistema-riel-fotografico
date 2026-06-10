# =============================================================================
# PROYECTO: Sistema de Riel Semicircular Fotográfico 180°
# INTEGRANTES: 
#              Macias Campos Ariadne Lizett 
#              Soto Garnica Ari Adair 
#              Lira Gamiño Luis Fernando 

# DESCRIPCIÓN: Biblioteca HAL (Hardware Abstraction Layer) en MicroPython para
#              el ESP32. Centraliza el control de todos los periféricos del
#              sistema: sensor PIR, limit switches, motor NEMA 17 (vía TMC2208),
#              LED de estado y buzzer. El programa principal (main.py) interactúa
#              con el hardware únicamente a través de esta biblioteca, sin
#              llamar directamente a machine.Pin o machine.PWM.
# =============================================================================

from machine import Pin, PWM, time_pulse_us
import time
import utime


# =============================================================================
# DEFINICIÓN DE PINES — mapa físico del ESP32
# =============================================================================

# Sensores
PIN_PIR           = 33   # GPIO34 — sensor PIR (solo entrada, sin pull)
PIN_ULTRASONICO_TRIG = 25
PIN_ULTRASONICO_ECHO = 26

ULTRASONICO_TIEMPO_ESPERA = 150 # En milisegundos

# Actuadores de señalización
PIN_LED_ESTADO_ROJO    = 18    # GPIO2  — LED integrado o externo (estado del sistema)
PIN_LED_ESTADO_AMARILLO    = 19    # GPIO2  — LED integrado o externo (estado del sistema)
PIN_LED_ESTADO_AZUL    = 21    # GPIO2  — LED integrado o externo (estado del sistema)
PIN_BUZZER        = 27    # GPIO4  — buzzer pasivo para alertas sonoras

# =============================================================================
# CLASE: CajaSensores
# Gestiona todos los sensores de lectura del sistema.
# =============================================================================

class CajaSensores:
    """
    Clase que encapsula la lectura e interpretación de los 3 sensores del sistema:
      1. Sensor PIR      — detecta presencia humana por calor infrarrojo
    Implementa promedio móvil en el PIR para evitar lecturas falsas.
    """

    # Cantidad de muestras para el promedio móvil del PIR
    MUESTRAS_PIR = 5

    def __init__(self):
        """
        Inicializa los pines de todos los sensores.
        PIR: solo entrada, sin resistencia pull (GPIO34/35 son input-only en ESP32).
        
        """
        self._pir          = Pin(PIN_PIR,       Pin.IN)

        self._ultrasonico_trig = Pin(PIN_ULTRASONICO_TRIG, Pin.OUT, pull=None)
        self._ultrasonico_trig.value(0)
        self._ultrasonico_echo = Pin(PIN_ULTRASONICO_ECHO, Pin.IN, pull=None)
        self._ultrasonico_espera = ULTRASONICO_TIEMPO_ESPERA
        self._ultrasonico_ultima_medida = 0
        self._ultrasonico_ultima_distancia = None

        # Historial de lecturas PIR para promedio móvil
        self._historial_pir = [0] * self.MUESTRAS_PIR
        self._indice_pir    = 0

    # -------------------------------------------------------------------------
    def obtener_presencia(self):
        """
        Parámetros: ninguno.
        Hace: lee el sensor PIR, actualiza el historial de muestras y calcula
              el promedio móvil para estabilizar la detección.
        Devuelve: True si hay presencia humana confirmada (mayoría de muestras
                  positivas), False en caso contrario.
        """
        lectura = self._pir.value()
        self._historial_pir[self._indice_pir] = lectura
        self._indice_pir = (self._indice_pir + 1) % self.MUESTRAS_PIR

        votos_positivos = sum(self._historial_pir)
        return votos_positivos >= (self.MUESTRAS_PIR // 2 + 1)

    # -------------------------------------------------------------------------

    def leer_distancia(self):
        actual = utime.ticks_ms()
        if utime.ticks_diff(actual, self._ultrasonico_ultima_medida) < self._ultrasonico_espera:
            # Regresar última medida
            print("aun no")
            return self._ultrasonico_ultima_distancia

        # Activar disparador
        self._ultrasonico_trig.value(0)
        utime.sleep_us(5)
        self._ultrasonico_trig.value(1)
        utime.sleep_us(10)
        self._ultrasonico_trig.value(0)

        try:
            # Medir duración del pulso de Echo
            duracion = time_pulse_us(self._ultrasonico_echo, 1, 30000)  # timeout 30ms
            if duracion < 0:
                RANGO_MAXIMO_EN_CM = const(500)
                duracion = int(RANGO_MAXIMO_EN_CM * 29.1)
            # Convertir a distancia en CM
            distancia = (duracion / 2) / 29.1
        except OSError:
            # Timeout o medición invalida
            distancia = None

        self._ultrasonico_ultima_medida = actual
        self._ultrasonico_ultima_distancia = distancia
        return distancia


    # -------------------------------------------------------------------------
    def obtener_resumen(self):
        """
        Parámetros: ninguno.
        Hace: consulta simultáneamente todos los sensores del sistema y
              construye un diccionario con el estado completo.
        Devuelve: diccionario con claves 'presencia', 'limite_izq', 'limite_der'.
        """
        return {
            "presencia"   : self.obtener_presencia(),
            "distancia"    : self.leer_distancia()
        }


# =============================================================================
# CLASE: CajaActuadores
# Gestiona todos los actuadores del sistema con comandos de alto nivel.
# =============================================================================

class CajaActuadores:
    """
    Clase que encapsula el control de los 3 actuadores del sistema:
      1. LEDs de estado               — indica el estado del sistema visualmente
      2. Buzzer pasivo               — emite señales sonoras a la persona fotografiada
      3. Servomotores
    """

    # Frecuencia del buzzer en Hz para cada tipo de señal
    FREQ_LISTA    = 1000  # tono agudo: sistema listo
    FREQ_ALERTA   = 400   # tono grave: no moverse / esperar
    FREQ_FIN      = 1500  # tono corto: sesión terminada

    def __init__(self):

        self._led_rojo    = Pin(PIN_LED_ESTADO_ROJO, Pin.OUT, value=0)
        self._led_amarillo    = Pin(PIN_LED_ESTADO_AMARILLO, Pin.OUT, value=0)
        self._led_azul    = Pin(PIN_LED_ESTADO_AZUL, Pin.OUT, value=0)
        self._buzzer = PWM(Pin(PIN_BUZZER), freq=1000, duty=0)  # inicia silencioso

    # -------------------------------------------------------------------------
    # MOTOR — movimiento
    # -------------------------------------------------------------------------


    # -------------------------------------------------------------------------
    # LED — señalización visual
    # -------------------------------------------------------------------------

    def encender_led(self,led):
        """
        Parámetros: nombre del led.
        Hace: enciende el LED de estado (sistema activo / grabando).
        Devuelve: nada.
        """
        if led == "ROJO": 
            self._led_rojo.value(1)
        elif led == "AMARILLO":
            self._led_amarillo.value(1)
        elif led == "AZUL":
            self._led_azul.value(1)

    def apagar_led(self,led):
        """
        Parámetros: ninguno.
        Hace: apaga el LED de estado.
        Devuelve: nada.
        """
        if led == "ROJO": 
            self._led_rojo.value(0)
        elif led == "AMARILLO":
            self._led_amarillo.value(0)
        elif led == "AZUL":
            self._led_azul.value(0)
    

    def apagar_leds(self):
        """
        Parámetros: ninguno.
        Hace: apaga los LEDs de estado.
        Devuelve: nada.
        """
        self._led_rojo.value(0)
        self._led_amarillo.value(0)
        self._led_azul.value(0)
            

    def parpadear_led(self, led, veces=3, intervalo_ms=200):
        """
        Parámetros:
          veces        (int) — cantidad de parpadeos (defecto 3).
          intervalo_ms (int) — duración en ms de cada estado ON/OFF (defecto 200).
        Hace: hace parpadear el LED la cantidad de veces indicada.
        Devuelve: nada.
        """
        for _ in range(veces):
            self.encender_led(led)
            time.sleep_ms(intervalo_ms)
            self.apagar_led(led)
            time.sleep_ms(intervalo_ms)

    # -------------------------------------------------------------------------
    # BUZZER — señalización sonora
    # -------------------------------------------------------------------------

    def señal_lista(self):
        """
        Parámetros: ninguno.
        Hace: emite un pitido agudo corto indicando que el sistema está listo
              y la persona puede colocarse en posición.
        Devuelve: nada.
        """
        self._buzzer.freq(self.FREQ_LISTA)
        self._buzzer.duty(512)   # 50% duty cycle — volumen medio
        time.sleep_ms(300)
        self._buzzer.duty(0)     # silencio

    def señal_quieta(self):
        """
        Parámetros: ninguno.
        Hace: emite un pitido grave largo pidiendo a la persona que no se mueva
              durante el barrido de la cámara.
        Devuelve: nada.
        """
        self._buzzer.freq(self.FREQ_ALERTA)
        self._buzzer.duty(512)
        time.sleep_ms(800)
        self._buzzer.duty(0)

    def señal_fin_sesion(self):
        """
        Parámetros: ninguno.
        Hace: emite dos pitidos ascendentes indicando que la sesión fotográfica
              terminó y la persona puede retirarse.
        Devuelve: nada.
        """
        for freq in (self.FREQ_ALERTA, self.FREQ_FIN):
            self._buzzer.freq(freq)
            self._buzzer.duty(512)
            time.sleep_ms(250)
            self._buzzer.duty(0)
            time.sleep_ms(100)

    # -------------------------------------------------------------------------
    # ESTADO SEGURO — apaga todo
    # -------------------------------------------------------------------------

    def estado_seguro(self):
        """
        Parámetros: ninguno.
        Hace: apaga y detiene TODOS los actuadores en un solo llamado.
              Desactiva el driver del motor (ENABLE en HIGH), apaga LED y buzzer.
              Debe llamarse ante cualquier error, interrupción o al finalizar.
        Devuelve: nada.
        """
        self.apagar_leds()
        self._buzzer.duty(0)       # silenciar buzzer


