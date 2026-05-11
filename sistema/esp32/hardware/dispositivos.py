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

from machine import Pin, PWM
import time


# =============================================================================
# DEFINICIÓN DE PINES — mapa físico del ESP32
# =============================================================================

# Sensores
PIN_PIR           = 34   # GPIO34 — sensor PIR (solo entrada, sin pull)
PIN_LIMIT_IZQ     = 35   # GPIO35 — limit switch extremo izquierdo (solo entrada)
PIN_LIMIT_DER     = 32   # GPIO32 — limit switch extremo derecho

# Motor NEMA 17 vía TMC2208 (modo STEP/DIR standalone)
PIN_STEP          = 26   # GPIO26 — pulsos de paso
PIN_DIR           = 27   # GPIO27 — dirección (HIGH = derecha, LOW = izquierda)
PIN_ENABLE        = 14   # GPIO14 — habilitar driver (LOW = activo, HIGH = apagado)

# Actuadores de señalización
PIN_LED_ESTADO    = 2    # GPIO2  — LED integrado o externo (estado del sistema)
PIN_BUZZER        = 4    # GPIO4  — buzzer pasivo para alertas sonoras

# Parámetros mecánicos del sistema
PASOS_POR_REV     = 200  # pasos por revolución del NEMA 17 (1.8° por paso)
MICROPASOS        = 8    # microstepping configurado en TMC2208 (MS1=HIGH, MS2=LOW)
DIENTES_POLEA     = 20   # dientes de la polea GT2
PASO_BANDA_MM     = 2    # paso de la banda GT2 en milímetros
RADIO_RIEL_MM     = 370  # radio del riel semicircular en milímetros (~37 cm)

# Cálculo: mm por paso del sistema
# Circunferencia polea = dientes × paso_banda = 20 × 2 = 40 mm por vuelta
# Pasos reales por vuelta = pasos_rev × micropasos = 200 × 8 = 1600
# MM por paso = 40 / 1600 = 0.025 mm/paso
MM_POR_PASO       = (DIENTES_POLEA * PASO_BANDA_MM) / (PASOS_POR_REV * MICROPASOS)

# Velocidad por defecto (microsegundos entre pulsos STEP — menor = más rápido)
VELOCIDAD_NORMAL  = 600   # µs — velocidad de barrido normal
VELOCIDAD_LENTA   = 1200  # µs — velocidad para acercarse a limit switch


# =============================================================================
# CLASE: CajaSensores
# Gestiona todos los sensores de lectura del sistema.
# =============================================================================

class CajaSensores:
    """
    Clase que encapsula la lectura e interpretación de los 3 sensores del sistema:
      1. Sensor PIR      — detecta presencia humana por calor infrarrojo
      2. Limit switch izquierdo — detecta fin de carrera lado izquierdo
      3. Limit switch derecho   — detecta fin de carrera lado derecho
    Implementa promedio móvil en el PIR para evitar lecturas falsas.
    """

    # Cantidad de muestras para el promedio móvil del PIR
    MUESTRAS_PIR = 5

    def __init__(self):
        """
        Inicializa los pines de todos los sensores.
        PIR: solo entrada, sin resistencia pull (GPIO34/35 son input-only en ESP32).
        Limit switches: entrada con pull-up interno; el switch conecta a GND.
        """
        self._pir          = Pin(PIN_PIR,       Pin.IN)
        self._limit_izq    = Pin(PIN_LIMIT_IZQ, Pin.IN)
        self._limit_der    = Pin(PIN_LIMIT_DER, Pin.IN, Pin.PULL_UP)

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
    def obtener_limite_izquierdo(self):
        """
        Parámetros: ninguno.
        Hace: lee el estado del limit switch del extremo izquierdo del riel.
              El switch está conectado a GND, con pull-up interno; al activarse
              el pin baja a 0.
        Devuelve: True si el carrito ha llegado al extremo izquierdo, False si no.
        """
        # Pull-up: 0 = presionado (límite alcanzado), 1 = libre
        return self._limit_izq.value() == 0

    # -------------------------------------------------------------------------
    def obtener_limite_derecho(self):
        """
        Parámetros: ninguno.
        Hace: lee el estado del limit switch del extremo derecho del riel.
        Devuelve: True si el carrito ha llegado al extremo derecho, False si no.
        """
        return self._limit_der.value() == 0

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
            "limite_izq"  : self.obtener_limite_izquierdo(),
            "limite_der"  : self.obtener_limite_derecho(),
        }


# =============================================================================
# CLASE: CajaActuadores
# Gestiona todos los actuadores del sistema con comandos de alto nivel.
# =============================================================================

class CajaActuadores:
    """
    Clase que encapsula el control de los 3 actuadores del sistema:
      1. Motor NEMA 17 (vía TMC2208) — mueve el carrito a lo largo del riel
      2. LED de estado               — indica el estado del sistema visualmente
      3. Buzzer pasivo               — emite señales sonoras a la persona fotografiada
    Expone métodos de alto nivel. El main.py nunca accede a machine.Pin directamente.
    """

    # Frecuencia del buzzer en Hz para cada tipo de señal
    FREQ_LISTA    = 1000  # tono agudo: sistema listo
    FREQ_ALERTA   = 400   # tono grave: no moverse / esperar
    FREQ_FIN      = 1500  # tono corto: sesión terminada

    def __init__(self):
        """
        Inicializa los pines del motor (STEP, DIR, ENABLE), LED y buzzer.
        El driver TMC2208 arranca deshabilitado (ENABLE en HIGH) para
        que el motor no consuma corriente ni se caliente en reposo.
        """
        self._paso      = Pin(PIN_STEP,   Pin.OUT, value=0)
        self._direccion = Pin(PIN_DIR,    Pin.OUT, value=0)
        self._habilitar = Pin(PIN_ENABLE, Pin.OUT, value=1)  # HIGH = apagado al inicio

        self._led    = Pin(PIN_LED_ESTADO, Pin.OUT, value=0)
        self._buzzer = PWM(Pin(PIN_BUZZER), freq=1000, duty=0)  # inicia silencioso

        # Posición actual en pasos (0 = extremo izquierdo, inicio del riel)
        self._posicion_pasos = 0

    # -------------------------------------------------------------------------
    # MOTOR — movimiento
    # -------------------------------------------------------------------------

    def mover_angulo(self, angulo_grados, velocidad_us=VELOCIDAD_NORMAL):
        """
        Parámetros:
          angulo_grados (float) — grados a mover; positivo = derecha, negativo = izquierda.
          velocidad_us  (int)   — microsegundos entre pulsos STEP (defecto 600 µs).
        Hace: convierte el ángulo en milímetros de arco, luego en pasos del motor,
              configura la dirección y genera los pulsos STEP necesarios.
              Detiene el movimiento si se activa algún limit switch.
        Devuelve: pasos efectivamente ejecutados (puede ser menor si hubo límite).
        """
        # Arco en mm = radio × ángulo en radianes
        import math
        arco_mm   = RADIO_RIEL_MM * abs(angulo_grados) * math.pi / 180.0
        num_pasos = int(arco_mm / MM_POR_PASO)

        # Dirección: HIGH = derecha (ángulos positivos)
        self._direccion.value(1 if angulo_grados >= 0 else 0)
        self._habilitar.value(0)  # activar driver

        pasos_dados = 0
        for _ in range(num_pasos):
            # Verificar límites antes de cada paso
            if angulo_grados > 0 and self._leer_limite_der():
                break
            if angulo_grados < 0 and self._leer_limite_izq():
                break

            self._paso.value(1)
            time.sleep_us(velocidad_us)
            self._paso.value(0)
            time.sleep_us(velocidad_us)
            pasos_dados += 1

        delta = pasos_dados if angulo_grados >= 0 else -pasos_dados
        self._posicion_pasos += delta
        return pasos_dados

    def ir_a_inicio(self):
        """
        Parámetros: ninguno.
        Hace: mueve el carrito hacia la izquierda a velocidad lenta hasta que
              el limit switch izquierdo se activa (homing). Restablece la
              posición interna a cero.
        Devuelve: nada.
        """
        self._direccion.value(0)  # izquierda
        self._habilitar.value(0)

        while not self._leer_limite_izq():
            self._paso.value(1)
            time.sleep_us(VELOCIDAD_LENTA)
            self._paso.value(0)
            time.sleep_us(VELOCIDAD_LENTA)

        self._posicion_pasos = 0

    def obtener_posicion_grados(self):
        """
        Parámetros: ninguno.
        Hace: convierte la posición interna en pasos a grados sobre el arco.
        Devuelve: float con los grados actuales (0° = extremo izquierdo, 180° = derecho).
        """
        import math
        arco_mm = self._posicion_pasos * MM_POR_PASO
        grados  = (arco_mm / RADIO_RIEL_MM) * (180.0 / math.pi)
        return round(grados, 2)

    # -------------------------------------------------------------------------
    # LED — señalización visual
    # -------------------------------------------------------------------------

    def encender_led(self):
        """
        Parámetros: ninguno.
        Hace: enciende el LED de estado (sistema activo / grabando).
        Devuelve: nada.
        """
        self._led.value(1)

    def apagar_led(self):
        """
        Parámetros: ninguno.
        Hace: apaga el LED de estado.
        Devuelve: nada.
        """
        self._led.value(0)

    def parpadear_led(self, veces=3, intervalo_ms=200):
        """
        Parámetros:
          veces        (int) — cantidad de parpadeos (defecto 3).
          intervalo_ms (int) — duración en ms de cada estado ON/OFF (defecto 200).
        Hace: hace parpadear el LED la cantidad de veces indicada.
        Devuelve: nada.
        """
        for _ in range(veces):
            self._led.value(1)
            time.sleep_ms(intervalo_ms)
            self._led.value(0)
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
        self._habilitar.value(1)   # deshabilitar driver — motor sin torque
        self._paso.value(0)        # asegurar STEP en bajo
        self._led.value(0)         # apagar LED
        self._buzzer.duty(0)       # silenciar buzzer

    # -------------------------------------------------------------------------
    # MÉTODOS PRIVADOS — solo para uso interno de la clase
    # -------------------------------------------------------------------------

    def _leer_limite_izq(self):
        """Lee directamente el pin del limit switch izquierdo (pull-up: 0 = activo)."""
        return Pin(PIN_LIMIT_IZQ, Pin.IN).value() == 0

    def _leer_limite_der(self):
        """Lee directamente el pin del limit switch derecho (pull-up: 0 = activo)."""
        return Pin(PIN_LIMIT_DER, Pin.IN, Pin.PULL_UP).value() == 0

