# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
# INTEGRANTES:
#              Macias Campos Ariadne Lizett
#              Soto Garnica Ari Adair
#              Lira Gamiño Luis Fernando
#
# DESCRIPCIÓN:
# Biblioteca HAL (Hardware Abstraction Layer) en MicroPython para el ESP32.
# Centraliza la lectura de sensores y el control de actuadores del sistema.
#
# El programa principal debe interactuar con el hardware únicamente por medio
# de CajaSensores y CajaActuadores, sin usar directamente machine.Pin,
# machine.PWM o machine.ADC fuera de esta biblioteca.
# =============================================================================

from machine import Pin, PWM, ADC, time_pulse_us
import time
import utime

# =============================================================================
# DEFINICIÓN DE PINES — mapa físico del ESP32
# =============================================================================
# -------------------------------------------------------------------------
# Sensores
# -------------------------------------------------------------------------
PIN_PIR = 33
PIN_ULTRASONICO_TRIG = 25
PIN_ULTRASONICO_ECHO = 26

# Joystick de la base.
PIN_JOYSTICK_BASE_X = 35

ULTRASONICO_TIEMPO_ESPERA = 150  # En milisegundos

# -------------------------------------------------------------------------
# Actuadores de señalización
# -------------------------------------------------------------------------
PIN_LED_ESTADO_ROJO = 18
PIN_LED_ESTADO_AMARILLO = 19
PIN_LED_ESTADO_AZUL = 21
PIN_BUZZER = 27

# -------------------------------------------------------------------------
# Servomotores
# -------------------------------------------------------------------------

PIN_SERVO_BASE = 14

# Se deja preparado para el brazo
PIN_SERVO_BRAZO = 23

# =============================================================================
# CLASE: CajaSensores
# Gestiona todos los sensores de lectura del sistema.
# =============================================================================

class CajaSensores:
    """
    Clase que encapsula la lectura e interpretación de los sensores del sistema.

    Sensores incluidos:
      1. Sensor PIR: detecta presencia o movimiento.
      2. Sensor ultrasónico: mide distancia aproximada en centímetros.
      3. Joystick base: lee el eje X para controlar la base de la garra.

    Esta clase permite que el programa principal no use directamente Pin ni ADC.
    """
    MUESTRAS_PIR = 5

    def __init__(self):
        """
        Parámetros: ninguno.

        Hace:
            Inicializa los pines de entrada de los sensores.
            Configura el sensor PIR, el sensor ultrasónico y el joystick.

        Devuelve:
            Nada.
        """

        # Sensor PIR
        self._pir = Pin(PIN_PIR, Pin.IN)

        # Sensor ultrasónico
        self._ultrasonico_trig = Pin(PIN_ULTRASONICO_TRIG, Pin.OUT)
        self._ultrasonico_trig.value(0)

        self._ultrasonico_echo = Pin(PIN_ULTRASONICO_ECHO, Pin.IN)
        self._ultrasonico_espera = ULTRASONICO_TIEMPO_ESPERA
        self._ultrasonico_ultima_medida = 0
        self._ultrasonico_ultima_distancia = None

        # Joystick de la base
        self._joystick_base_x = ADC(Pin(PIN_JOYSTICK_BASE_X))
        self._joystick_base_x.atten(ADC.ATTN_11DB)
        self._joystick_base_x.width(ADC.WIDTH_12BIT)

        # Historial de lecturas PIR para promedio móvil
        self._historial_pir = [0] * self.MUESTRAS_PIR
        self._indice_pir = 0

    # -------------------------------------------------------------------------
    def obtener_presencia(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Lee el sensor PIR, actualiza el historial de muestras y calcula
            un promedio móvil simple para evitar falsas detecciones.

        Devuelve:
            True si hay presencia o movimiento confirmado.
            False si no hay presencia o movimiento confirmado.
        """

        lectura = self._pir.value()

        self._historial_pir[self._indice_pir] = lectura
        self._indice_pir = (self._indice_pir + 1) % self.MUESTRAS_PIR

        votos_positivos = sum(self._historial_pir)

        return votos_positivos >= (self.MUESTRAS_PIR // 2 + 1)

    # -------------------------------------------------------------------------
    def leer_distancia(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Lee el sensor ultrasónico y calcula la distancia aproximada
            en centímetros. Para evitar lecturas demasiado rápidas, conserva
            la última medición durante un intervalo corto.

        Devuelve:
            Distancia en centímetros como número decimal.
            None si la lectura no fue válida.
        """

        actual = utime.ticks_ms()

        if utime.ticks_diff(actual, self._ultrasonico_ultima_medida) < self._ultrasonico_espera:
            return self._ultrasonico_ultima_distancia

        # Activar pulso de disparo
        self._ultrasonico_trig.value(0)
        utime.sleep_us(5)

        self._ultrasonico_trig.value(1)
        utime.sleep_us(10)

        self._ultrasonico_trig.value(0)

        try:
            duracion = time_pulse_us(self._ultrasonico_echo, 1, 30000)

            if duracion < 0:
                distancia = None
            else:
                distancia = (duracion / 2) / 29.1

        except OSError:
            distancia = None

        self._ultrasonico_ultima_medida = actual
        self._ultrasonico_ultima_distancia = distancia

        return distancia

    # -------------------------------------------------------------------------
    def leer_joystick_base(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Lee el eje X del joystick usado para mover la base.

        Devuelve:
            Valor analógico entre 0 y 4095.
            Aproximadamente 2048 cuando el joystick está al centro.
        """
        return self._joystick_base_x.read()

    # -------------------------------------------------------------------------
    def obtener_direccion_joystick_base(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Interpreta la lectura analógica del joystick de la base.

        Devuelve:
            "DERECHA" si el joystick supera el límite alto.
            "IZQUIERDA" si el joystick baja del límite bajo.
            "CENTRO" si el joystick está en reposo.
        """

        valor = self.leer_joystick_base()

        if valor > 2500:
            return "DERECHA"

        elif valor < 1700:
            return "IZQUIERDA"

        return "CENTRO"

    # -------------------------------------------------------------------------
    def obtener_joystick_base_interpretado(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Lee el joystick y entrega tanto el valor crudo como su interpretación.

        Devuelve:
            Diccionario con:
                valor: lectura de 0 a 4095.
                direccion: DERECHA, IZQUIERDA o CENTRO.
        """

        valor = self.leer_joystick_base()

        if valor > 2500:
            direccion = "DERECHA"

        elif valor < 1700:
            direccion = "IZQUIERDA"

        else:
            direccion = "CENTRO"

        return {
            "valor": valor,
            "direccion": direccion
        }

    # -------------------------------------------------------------------------
    def obtener_resumen(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Consulta los sensores principales del sistema y construye
            un resumen general.

        Devuelve:
            Diccionario con presencia, distancia, valor del joystick y
            dirección interpretada del joystick.
        """

        joystick = self.obtener_joystick_base_interpretado()

        return {
            "presencia": self.obtener_presencia(),
            "distancia_cm": self.leer_distancia(),
            "joystick_base": joystick["valor"],
            "direccion_base": joystick["direccion"]
        }
# =============================================================================
# CLASE: CajaActuadores
# Gestiona todos los actuadores del sistema con comandos de alto nivel.
# =============================================================================

class CajaActuadores:
    """
    Clase que encapsula el control de los actuadores del sistema.

    Actuadores incluidos:
      1. LEDs de estado.
      2. Buzzer.
      3. Servomotores de base y brazo.

    Esta clase permite que el programa principal no use directamente PWM ni Pin.
    """

    FREQ_LISTA = 1000
    FREQ_ALERTA = 400
    FREQ_FIN = 1500

    def __init__(self, centrar_servos=False):
        """
        Parámetros:
            centrar_servos:
                Si es True, manda los servos a 90 grados al iniciar.
                Si es False, solo prepara los PWM sin moverlos de inmediato.

        Hace:
            Inicializa LEDs, buzzer y servomotores.

        Devuelve:
            Nada.
        """

        # LEDs
        self._led_rojo = Pin(PIN_LED_ESTADO_ROJO, Pin.OUT, value=0)
        self._led_amarillo = Pin(PIN_LED_ESTADO_AMARILLO, Pin.OUT, value=0)
        self._led_azul = Pin(PIN_LED_ESTADO_AZUL, Pin.OUT, value=0)

        # Buzzer
        self._buzzer = PWM(Pin(PIN_BUZZER), freq=1000, duty=0)

        # Servomotores
        self._servo_base = PWM(Pin(PIN_SERVO_BASE), freq=50)
        self._servo_brazo = PWM(Pin(PIN_SERVO_BRAZO), freq=50)

        # Posiciones registradas
        self._angulo_base = 90
        self._angulo_brazo = 90

        if centrar_servos:
            self.mover_base(self._angulo_base)
            self.mover_brazo(self._angulo_brazo)

    # -------------------------------------------------------------------------
    def _aplicar_angulo_servo(self, servo, angulo):
        """
        Parámetros:
            servo: objeto PWM del servomotor.
            angulo: ángulo deseado entre 0 y 180.

        Hace:
            Limita el ángulo, lo convierte a duty PWM y lo aplica al servo.

        Devuelve:
            Ángulo final aplicado.
        """

        angulo = max(0, min(180, angulo))

        duty_min = 26
        duty_max = 128

        duty = int(duty_min + (duty_max - duty_min) * angulo / 180)

        servo.duty(duty)

        return angulo

    # -------------------------------------------------------------------------
    def mover_base(self, angulo):
        """
        Parámetros:
            angulo: posición deseada de la base entre 0 y 180 grados.

        Hace:
            Mueve el servo de la base al ángulo indicado.

        Devuelve:
            Ángulo final aplicado.
        """

        self._angulo_base = self._aplicar_angulo_servo(self._servo_base, angulo)

        return self._angulo_base

    # -------------------------------------------------------------------------
    def mover_brazo(self, angulo):
        """
        Parámetros:
            angulo: posición deseada del brazo entre 0 y 180 grados.

        Hace:
            Mueve el servo del brazo al ángulo indicado.

        Devuelve:
            Ángulo final aplicado.
        """

        self._angulo_brazo = self._aplicar_angulo_servo(self._servo_brazo, angulo)

        return self._angulo_brazo

    # -------------------------------------------------------------------------
    def mover_base_por_direccion(self, direccion, paso=1, minimo=0, maximo=180):
        """
        Parámetros:
            direccion: "DERECHA", "IZQUIERDA" o "CENTRO".
            paso: cantidad de grados que cambia por ciclo.
            minimo: ángulo mínimo permitido.
            maximo: ángulo máximo permitido.

        Hace:
            Mueve la base según la dirección interpretada desde el joystick.

        Devuelve:
            Ángulo actual de la base.
        """

        if direccion == "DERECHA":
            nuevo_angulo = self._angulo_base + paso
            self.mover_base(max(minimo, min(maximo, nuevo_angulo)))

        elif direccion == "IZQUIERDA":
            nuevo_angulo = self._angulo_base - paso
            self.mover_base(max(minimo, min(maximo, nuevo_angulo)))

        return self._angulo_base

    # -------------------------------------------------------------------------
    def mover_base_desde_joystick(self, valor_joystick, paso=1, minimo=0, maximo=180, invertir=False):
        """
        Parámetros:
            valor_joystick: lectura analógica del joystick entre 0 y 4095.
            paso: cantidad de grados por ciclo.
            minimo: ángulo mínimo permitido.
            maximo: ángulo máximo permitido.
            invertir: invierte la dirección del movimiento si es necesario.

        Hace:
            Interpreta directamente la lectura del joystick y mueve la base.

        Devuelve:
            Ángulo actual de la base.
        """

        if not invertir:
            if valor_joystick > 2500:
                self.mover_base_por_direccion("DERECHA", paso, minimo, maximo)

            elif valor_joystick < 1700:
                self.mover_base_por_direccion("IZQUIERDA", paso, minimo, maximo)

        else:
            if valor_joystick > 2500:
                self.mover_base_por_direccion("IZQUIERDA", paso, minimo, maximo)

            elif valor_joystick < 1700:
                self.mover_base_por_direccion("DERECHA", paso, minimo, maximo)

        return self._angulo_base

    # -------------------------------------------------------------------------
    def obtener_posicion_base(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Consulta la última posición registrada del servo de la base.

        Devuelve:
            Ángulo actual de la base.
        """

        return self._angulo_base

    # -------------------------------------------------------------------------
    def obtener_posicion_brazo(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Consulta la última posición registrada del servo del brazo.

        Devuelve:
            Ángulo actual del brazo.
        """

        return self._angulo_brazo

    # -------------------------------------------------------------------------
    def mover_servo(self, angulo, servomotor):
        """
        Parámetros:
            angulo: ángulo deseado entre 0 y 180.
            servomotor: "base" o "brazo".

        Hace:
            Mantiene compatibilidad con el código anterior, permitiendo mover
            un servo por nombre.

        Devuelve:
            Ángulo final aplicado o None si el nombre no es válido.
        """

        if servomotor == "base":
            return self.mover_base(angulo)

        elif servomotor == "brazo":
            return self.mover_brazo(angulo)

        return None

    # -------------------------------------------------------------------------
    def encender_led(self, led):
        """
        Parámetros:
            led: "ROJO", "AMARILLO" o "AZUL".

        Hace:
            Enciende el LED indicado.

        Devuelve:
            Nada.
        """

        if led == "ROJO":
            self._led_rojo.value(1)

        elif led == "AMARILLO":
            self._led_amarillo.value(1)

        elif led == "AZUL":
            self._led_azul.value(1)

    # -------------------------------------------------------------------------
    def apagar_led(self, led):
        """
        Parámetros:
            led: "ROJO", "AMARILLO" o "AZUL".

        Hace:
            Apaga el LED indicado.

        Devuelve:
            Nada.
        """

        if led == "ROJO":
            self._led_rojo.value(0)

        elif led == "AMARILLO":
            self._led_amarillo.value(0)

        elif led == "AZUL":
            self._led_azul.value(0)

    # -------------------------------------------------------------------------
    def apagar_leds(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Apaga todos los LEDs de estado.

        Devuelve:
            Nada.
        """

        self._led_rojo.value(0)
        self._led_amarillo.value(0)
        self._led_azul.value(0)

    # -------------------------------------------------------------------------
    def parpadear_led(self, led, veces=3, intervalo_ms=200):
        """
        Parámetros:
            led: "ROJO", "AMARILLO" o "AZUL".
            veces: cantidad de parpadeos.
            intervalo_ms: duración de cada encendido y apagado.

        Hace:
            Parpadea el LED indicado.

        Devuelve:
            Nada.
        """

        for _ in range(veces):
            self.encender_led(led)
            time.sleep_ms(intervalo_ms)
            self.apagar_led(led)
            time.sleep_ms(intervalo_ms)

    # -------------------------------------------------------------------------
    def señal_lista(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Emite un pitido corto indicando que el sistema está listo.

        Devuelve:
            Nada.
        """

        self._buzzer.freq(self.FREQ_LISTA)
        self._buzzer.duty(512)
        time.sleep_ms(300)
        self._buzzer.duty(0)

    # -------------------------------------------------------------------------
    def señal_quieta(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Emite un pitido grave para indicar que la persona debe permanecer quieta.

        Devuelve:
            Nada.
        """

        self._buzzer.freq(self.FREQ_ALERTA)
        self._buzzer.duty(512)
        time.sleep_ms(800)
        self._buzzer.duty(0)

    # -------------------------------------------------------------------------
    def señal_fin_sesion(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Emite dos pitidos indicando que la sesión terminó.

        Devuelve:
            Nada.
        """

        for frecuencia in (self.FREQ_ALERTA, self.FREQ_FIN):
            self._buzzer.freq(frecuencia)
            self._buzzer.duty(512)
            time.sleep_ms(250)
            self._buzzer.duty(0)
            time.sleep_ms(100)

    # -------------------------------------------------------------------------
    def estado_seguro(self):
        """
        Parámetros:
            Ninguno.

        Hace:
            Apaga LEDs, silencia el buzzer y detiene la señal PWM de los servos.
            Debe llamarse ante errores, interrupciones o al finalizar.

        Devuelve:
            Nada.
        """

        self.apagar_leds()
        self._buzzer.duty(0)

        # Detiene el pulso PWM de los servos.
        # Esto no corta la energía física, pero deja de enviar señal de control.
        self._servo_base.duty(0)
        self._servo_brazo.duty(0)


# =============================================================================
# ALIAS OPCIONALES
# Se agregan por compatibilidad con el nombre solicitado en la rúbrica:
# SensorBox y ActuatorBox.
# =============================================================================

SensorBox = CajaSensores
ActuatorBox = CajaActuadores


