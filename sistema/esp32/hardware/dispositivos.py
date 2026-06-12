# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/esp32/hardware/dispositivos.py
#
# OBJETIVO:
# Biblioteca HAL para ESP32. Aqui si se usan Pin, PWM y ADC.
# main.py y maquina_estado.py NO deben usar primitivas de hardware.
# =============================================================================

from machine import Pin, PWM, ADC, time_pulse_us
import utime

# =============================================================================
# MAPA DE PINES ACTUAL DEL PROYECTO
# =============================================================================

# Sensores
PIN_PIR = 33
PIN_ULTRASONICO_TRIG = 25
PIN_ULTRASONICO_ECHO = 26
PIN_JOYSTICK_BASE_X = 35

# Actuadores
PIN_LED_ESTADO_ROJO = 18
PIN_LED_ESTADO_AMARILLO = 19
PIN_LED_ESTADO_AZUL = 21
PIN_BUZZER = 27

# Servos
PIN_SERVO_BASE = 14
PIN_SERVO_BRAZO = 23

# Ultrasonico
ULTRASONICO_TIEMPO_ESPERA_MS = 150


# =============================================================================
# CLASE: CajaSensores
# =============================================================================

class CajaSensores:
    """
    Clase que concentra la lectura de sensores del sistema.

    Sensores:
    - PIR en GPIO33.
    - Ultrasonico TRIG GPIO25 y ECHO GPIO26.
    - Joystick VRx en GPIO35.

    Devuelve lecturas interpretadas para que la maquina de estados no use
    directamente Pin, ADC ni time_pulse_us.
    """

    MUESTRAS_PIR = 3
    LIMITE_JOYSTICK_ALTO = 2500
    LIMITE_JOYSTICK_BAJO = 1700

    def __init__(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Inicializa PIR, ultrasonico y joystick.

        Devuelve:
            Nada.
        """

        self._pir = Pin(PIN_PIR, Pin.IN, Pin.PULL_DOWN)

        self._ultrasonico_trig = Pin(PIN_ULTRASONICO_TRIG, Pin.OUT)
        self._ultrasonico_trig.value(0)
        self._ultrasonico_echo = Pin(PIN_ULTRASONICO_ECHO, Pin.IN)

        self._ultrasonico_ultima_medida = 0
        self._ultrasonico_ultima_distancia = None

        self._joystick_base_x = ADC(Pin(PIN_JOYSTICK_BASE_X))
        self._joystick_base_x.atten(ADC.ATTN_11DB)
        self._joystick_base_x.width(ADC.WIDTH_12BIT)

        self._historial_pir = [0] * self.MUESTRAS_PIR
        self._indice_pir = 0

    # -------------------------------------------------------------------------
    def obtener_presencia(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Lee el PIR y aplica un filtro simple por muestras.

        Devuelve:
            True si el PIR detecta movimiento/presencia.
            False si no detecta.
        """

        lectura = self._pir.value()

        self._historial_pir[self._indice_pir] = lectura
        self._indice_pir = (self._indice_pir + 1) % self.MUESTRAS_PIR

        votos = sum(self._historial_pir)
        return votos >= 1

    # -------------------------------------------------------------------------
    def leer_distancia(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Lee el sensor ultrasonico y calcula distancia en cm.

        Devuelve:
            Distancia en centimetros.
            None si no hay lectura valida.
        """

        actual = utime.ticks_ms()

        if utime.ticks_diff(actual, self._ultrasonico_ultima_medida) < ULTRASONICO_TIEMPO_ESPERA_MS:
            return self._ultrasonico_ultima_distancia

        self._ultrasonico_trig.value(0)
        utime.sleep_us(3)

        self._ultrasonico_trig.value(1)
        utime.sleep_us(10)
        self._ultrasonico_trig.value(0)

        try:
            duracion = time_pulse_us(self._ultrasonico_echo, 1, 30000)
        except OSError:
            duracion = -1

        if duracion <= 0:
            distancia = None
        else:
            distancia = (duracion * 0.0343) / 2

        self._ultrasonico_ultima_medida = actual
        self._ultrasonico_ultima_distancia = distancia

        return distancia

    # -------------------------------------------------------------------------
    def leer_joystick_base(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Lee el eje VRx del joystick de la base.

        Devuelve:
            Valor analogico de 0 a 4095.
        """

        return self._joystick_base_x.read()

    # -------------------------------------------------------------------------
    def obtener_direccion_joystick_base(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Convierte el valor analogico del joystick en direccion.

        Devuelve:
            DERECHA, IZQUIERDA o CENTRO.
        """

        valor = self.leer_joystick_base()

        if valor > self.LIMITE_JOYSTICK_ALTO:
            return "DERECHA"

        if valor < self.LIMITE_JOYSTICK_BAJO:
            return "IZQUIERDA"

        return "CENTRO"

    # -------------------------------------------------------------------------
    def obtener_joystick_base_interpretado(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Lee el joystick y devuelve valor crudo mas direccion.

        Devuelve:
            Diccionario con valor y direccion.
        """

        valor = self.leer_joystick_base()

        if valor > self.LIMITE_JOYSTICK_ALTO:
            direccion = "DERECHA"
        elif valor < self.LIMITE_JOYSTICK_BAJO:
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
        Parametros:
            Ninguno.

        Hace:
            Lee todos los sensores necesarios para el ciclo principal.

        Devuelve:
            Diccionario con presencia, distancia, joystick y direccion.
        """

        joystick = self.obtener_joystick_base_interpretado()
        presencia = self.obtener_presencia()
        distancia = self.leer_distancia()

        return {
            "presencia": presencia,
            "distancia_cm": distancia,
            "joystick_base": joystick["valor"],
            "direccion_base": joystick["direccion"]
        }


# =============================================================================
# CLASE: CajaActuadores
# =============================================================================

class CajaActuadores:
    """
    Clase que concentra el control de actuadores del sistema.

    Actuadores:
    - LED rojo GPIO18.
    - LED amarillo GPIO19.
    - LED azul GPIO21.
    - Buzzer GPIO27.
    - Servo base GPIO14.
    - Servo brazo GPIO23.
    """

    FREQ_LISTA = 1000
    FREQ_ALERTA = 400
    FREQ_FIN = 1500

    DUTY_SERVO_MIN = 26
    DUTY_SERVO_MAX = 128

    def __init__(self, centrar_servos=False):
        """
        Parametros:
            centrar_servos: si es True centra base y brazo en 90 grados.

        Hace:
            Inicializa LEDs, buzzer y servos.

        Devuelve:
            Nada.
        """

        self._led_rojo = Pin(PIN_LED_ESTADO_ROJO, Pin.OUT, value=0)
        self._led_amarillo = Pin(PIN_LED_ESTADO_AMARILLO, Pin.OUT, value=0)
        self._led_azul = Pin(PIN_LED_ESTADO_AZUL, Pin.OUT, value=0)

        self._buzzer = PWM(Pin(PIN_BUZZER), freq=1000, duty=0)

        self._servo_base = PWM(Pin(PIN_SERVO_BASE), freq=50)
        self._servo_brazo = PWM(Pin(PIN_SERVO_BRAZO), freq=50)

        self._angulo_base = 90
        self._angulo_brazo = 90

        if centrar_servos:
            self.mover_base(self._angulo_base)
            self.mover_brazo(self._angulo_brazo)

    # -------------------------------------------------------------------------
    def _aplicar_angulo_servo(self, servo, angulo):
        """
        Parametros:
            servo: objeto PWM del servo.
            angulo: angulo entre 0 y 180.

        Hace:
            Convierte grados a duty y mueve el servo.

        Devuelve:
            Angulo aplicado.
        """

        angulo = int(angulo)

        if angulo < 0:
            angulo = 0
        elif angulo > 180:
            angulo = 180

        duty = self.DUTY_SERVO_MIN + int(
            (angulo / 180) * (self.DUTY_SERVO_MAX - self.DUTY_SERVO_MIN)
        )

        servo.duty(duty)
        return angulo

    # -------------------------------------------------------------------------
    def mover_base(self, angulo):
        """
        Parametros:
            angulo: angulo deseado de la base.

        Hace:
            Mueve el servo base.

        Devuelve:
            Angulo final de la base.
        """

        self._angulo_base = self._aplicar_angulo_servo(self._servo_base, angulo)
        return self._angulo_base

    # -------------------------------------------------------------------------
    def mover_brazo(self, angulo):
        """
        Parametros:
            angulo: angulo deseado del brazo.

        Hace:
            Mueve el servo del brazo.

        Devuelve:
            Angulo final del brazo.
        """

        self._angulo_brazo = self._aplicar_angulo_servo(self._servo_brazo, angulo)
        return self._angulo_brazo

    # -------------------------------------------------------------------------
    def mover_base_por_direccion(self, direccion, paso=1, minimo=0, maximo=180):
        """
        Parametros:
            direccion: DERECHA, IZQUIERDA o CENTRO.
            paso: grados por ciclo.
            minimo: angulo minimo.
            maximo: angulo maximo.

        Hace:
            Mueve la base de forma incremental, como en la prueba de Thonny.

        Devuelve:
            Angulo actual de la base.
        """

        if direccion == "DERECHA":
            nuevo = self._angulo_base + paso
            self.mover_base(max(minimo, min(maximo, nuevo)))

        elif direccion == "IZQUIERDA":
            nuevo = self._angulo_base - paso
            self.mover_base(max(minimo, min(maximo, nuevo)))

        return self._angulo_base

    # -------------------------------------------------------------------------
    def mover_base_desde_joystick(self, valor_joystick, paso=1, minimo=0, maximo=180, invertir=False):
        """
        Parametros:
            valor_joystick: valor analogico entre 0 y 4095.
            paso: grados por ciclo.
            minimo: angulo minimo.
            maximo: angulo maximo.
            invertir: invierte el sentido del servo.

        Hace:
            Usa directamente los limites 2500 y 1700 de la prueba de Thonny.

        Devuelve:
            Angulo actual de la base.
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
        Devuelve:
            Angulo actual registrado de la base.
        """

        return self._angulo_base

    # -------------------------------------------------------------------------
    def obtener_posicion_brazo(self):
        """
        Devuelve:
            Angulo actual registrado del brazo.
        """

        return self._angulo_brazo

    # -------------------------------------------------------------------------
    def mover_servo(self, angulo, servomotor):
        """
        Parametros:
            angulo: angulo deseado.
            servomotor: base o brazo.

        Hace:
            Mantiene compatibilidad con codigo anterior.

        Devuelve:
            Angulo aplicado o None.
        """

        if servomotor == "base":
            return self.mover_base(angulo)

        if servomotor == "brazo":
            return self.mover_brazo(angulo)

        return None

    # -------------------------------------------------------------------------
    def encender_led(self, led):
        """
        Parametros:
            led: ROJO, AMARILLO o AZUL.

        Hace:
            Enciende un LED.
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
        Parametros:
            led: ROJO, AMARILLO o AZUL.

        Hace:
            Apaga un LED.
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
        Hace:
            Apaga todos los LEDs.
        """

        self._led_rojo.value(0)
        self._led_amarillo.value(0)
        self._led_azul.value(0)

    # -------------------------------------------------------------------------
    def encender_solo_led(self, led):
        """
        Parametros:
            led: ROJO, AMARILLO o AZUL.

        Hace:
            Apaga todos los LEDs y enciende solo uno.
        """

        self.apagar_leds()
        self.encender_led(led)

    # -------------------------------------------------------------------------
    def parpadear_led(self, led, veces=3, intervalo_ms=200):
        """
        Parametros:
            led: ROJO, AMARILLO o AZUL.
            veces: numero de parpadeos.
            intervalo_ms: tiempo de encendido/apagado.

        Hace:
            Parpadea un LED. Este metodo bloquea, usar solo en pruebas.
        """

        for _ in range(veces):
            self.encender_led(led)
            utime.sleep_ms(intervalo_ms)
            self.apagar_led(led)
            utime.sleep_ms(intervalo_ms)

    # -------------------------------------------------------------------------
    def apagar_buzzer(self):
        """
        Hace:
            Apaga el buzzer.
        """

        self._buzzer.duty(0)

    # -------------------------------------------------------------------------
    def controlar_buzzer_por_estado(self, estado):
        """
        Parametros:
            estado: ROJO, AMARILLO, AZUL o SIN_LECTURA.

        Hace:
            Control no bloqueante del buzzer:
            - ROJO: rapido.
            - AMARILLO o SIN_LECTURA: lento.
            - AZUL: apagado.
        """

        tiempo = utime.ticks_ms()

        if estado == "ROJO":
            if tiempo % 300 < 150:
                self._buzzer.freq(1800)
                self._buzzer.duty(500)
            else:
                self._buzzer.duty(0)

        elif estado == "AMARILLO" or estado == "SIN_LECTURA":
            if tiempo % 1300 < 100:
                self._buzzer.freq(900)
                self._buzzer.duty(250)
            else:
                self._buzzer.duty(0)

        else:
            self._buzzer.duty(0)

    # -------------------------------------------------------------------------
    def senal_lista(self):
        """
        Hace:
            Pitido corto de sistema listo.
        """

        self._buzzer.freq(self.FREQ_LISTA)
        self._buzzer.duty(512)
        utime.sleep_ms(250)
        self._buzzer.duty(0)

    # -------------------------------------------------------------------------
    def senal_quieta(self):
        """
        Hace:
            Pitido de alerta simple.
        """

        self._buzzer.freq(self.FREQ_ALERTA)
        self._buzzer.duty(512)
        utime.sleep_ms(300)
        self._buzzer.duty(0)

    # -------------------------------------------------------------------------
    def senal_fin_sesion(self):
        """
        Hace:
            Dos pitidos de fin.
        """

        for frecuencia in (self.FREQ_ALERTA, self.FREQ_FIN):
            self._buzzer.freq(frecuencia)
            self._buzzer.duty(512)
            utime.sleep_ms(180)
            self._buzzer.duty(0)
            utime.sleep_ms(80)

    # -------------------------------------------------------------------------
    def estado_seguro(self):
        """
        Hace:
            Apaga LEDs, buzzer y senal PWM de servos.
        """

        self.apagar_leds()
        self.apagar_buzzer()
        self._servo_base.duty(0)
        self._servo_brazo.duty(0)


SensorBox = CajaSensores
ActuatorBox = CajaActuadores



