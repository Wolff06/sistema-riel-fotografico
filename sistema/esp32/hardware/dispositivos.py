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
ULTRASONICO_TIEMPO_ESPERA_MS = 180


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

    Esta version agrega filtros para evitar cambios falsos:
    - El ultrasonico usa historial, mediana y suavizado.
    - El joystick se calibra al iniciar y usa zona muerta amplia.
    """

    MUESTRAS_PIR = 3

    # Filtro del sensor ultrasonico.
    MUESTRAS_ULTRASONICO = 5
    DISTANCIA_MINIMA_VALIDA = 2
    DISTANCIA_MAXIMA_VALIDA = 250
    CAMBIO_ULTRASONICO_MAXIMO_CM = 35

    # Filtro del joystick.
    MUESTRAS_JOYSTICK = 5
    MUESTRAS_CALIBRACION_JOYSTICK = 25
    JOYSTICK_CENTRO_DEFECTO = 2048
    JOYSTICK_ZONA_MUERTA = 700
    JOYSTICK_ZONA_REINGRESO = 450
    JOYSTICK_CONFIRMACIONES = 2

    def __init__(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Inicializa PIR, ultrasonico y joystick.
            Calibra el centro del joystick al encender.

        Devuelve:
            Nada.
        """

        self._pir = Pin(PIN_PIR, Pin.IN, Pin.PULL_DOWN)

        self._ultrasonico_trig = Pin(PIN_ULTRASONICO_TRIG, Pin.OUT)
        self._ultrasonico_trig.value(0)
        self._ultrasonico_echo = Pin(PIN_ULTRASONICO_ECHO, Pin.IN)

        self._ultrasonico_ultima_medida = 0
        self._ultrasonico_ultima_distancia = None
        self._ultrasonico_distancia_filtrada = None
        self._historial_ultrasonico = []

        self._joystick_base_x = ADC(Pin(PIN_JOYSTICK_BASE_X))
        self._joystick_base_x.atten(ADC.ATTN_11DB)
        self._joystick_base_x.width(ADC.WIDTH_12BIT)

        self._historial_joystick = []
        self._joystick_centro = self._calibrar_joystick_base()
        self._joystick_direccion_estable = "CENTRO"
        self._joystick_direccion_candidata = "CENTRO"
        self._joystick_conteo_candidata = 0

        self._historial_pir = [0] * self.MUESTRAS_PIR
        self._indice_pir = 0

        print("Centro calibrado del joystick:", self._joystick_centro)

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
    def _leer_distancia_cruda(self):
        """
        Hace:
            Ejecuta el pulso real del sensor ultrasonico.

        Devuelve:
            Distancia cruda en cm o None si la lectura no es valida.
        """

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
            return None

        distancia = (duracion * 0.0343) / 2

        if distancia < self.DISTANCIA_MINIMA_VALIDA:
            return None

        if distancia > self.DISTANCIA_MAXIMA_VALIDA:
            return None

        return distancia

    # -------------------------------------------------------------------------
    def _filtrar_distancia(self, distancia_cruda):
        """
        Parametros:
            distancia_cruda: distancia medida en cm o None.

        Hace:
            Reduce saltos del ultrasonico usando historial y mediana.
            Esto evita que el estado de LEDs cambie por ruido de una lectura.

        Devuelve:
            Distancia filtrada en cm o None.
        """

        if distancia_cruda is None:
            return self._ultrasonico_distancia_filtrada

        if self._ultrasonico_distancia_filtrada is not None:
            diferencia = abs(distancia_cruda - self._ultrasonico_distancia_filtrada)
            if diferencia > self.CAMBIO_ULTRASONICO_MAXIMO_CM:
                # Se ignora un salto demasiado grande porque suele ser ruido.
                return self._ultrasonico_distancia_filtrada

        self._historial_ultrasonico.append(distancia_cruda)
        if len(self._historial_ultrasonico) > self.MUESTRAS_ULTRASONICO:
            self._historial_ultrasonico.pop(0)

        ordenadas = sorted(self._historial_ultrasonico)
        mediana = ordenadas[len(ordenadas) // 2]

        if self._ultrasonico_distancia_filtrada is None:
            self._ultrasonico_distancia_filtrada = mediana
        else:
            self._ultrasonico_distancia_filtrada = (
                self._ultrasonico_distancia_filtrada * 0.65 + mediana * 0.35
            )

        return self._ultrasonico_distancia_filtrada

    # -------------------------------------------------------------------------
    def leer_distancia(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Lee el sensor ultrasonico y calcula distancia en cm.
            La salida ya va filtrada para evitar parpadeos de LEDs.

        Devuelve:
            Distancia en centimetros.
            None si no hay lectura valida inicial.
        """

        actual = utime.ticks_ms()

        if utime.ticks_diff(actual, self._ultrasonico_ultima_medida) < ULTRASONICO_TIEMPO_ESPERA_MS:
            return self._ultrasonico_ultima_distancia

        distancia_cruda = self._leer_distancia_cruda()
        distancia = self._filtrar_distancia(distancia_cruda)

        self._ultrasonico_ultima_medida = actual
        self._ultrasonico_ultima_distancia = distancia

        return distancia

    # -------------------------------------------------------------------------
    def _leer_joystick_crudo(self):
        """
        Hace:
            Lee directamente el ADC del joystick.

        Devuelve:
            Valor analogico de 0 a 4095.
        """

        return self._joystick_base_x.read()

    # -------------------------------------------------------------------------
    def _calibrar_joystick_base(self):
        """
        Hace:
            Obtiene el centro real del joystick al iniciar.
            Es importante no tocar el joystick durante el arranque.

        Devuelve:
            Valor central calibrado.
        """

        total = 0
        lecturas_validas = 0

        for _ in range(self.MUESTRAS_CALIBRACION_JOYSTICK):
            valor = self._leer_joystick_crudo()
            if 0 <= valor <= 4095:
                total += valor
                lecturas_validas += 1
            utime.sleep_ms(5)

        if lecturas_validas == 0:
            return self.JOYSTICK_CENTRO_DEFECTO

        centro = int(total / lecturas_validas)

        # Si el centro cae demasiado cerca de los extremos, probablemente
        # el joystick esta mal conectado o se estaba tocando al encender.
        if centro < 350 or centro > 3745:
            return self.JOYSTICK_CENTRO_DEFECTO

        return centro

    # -------------------------------------------------------------------------
    def leer_joystick_base(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Lee el eje VRx del joystick de la base y aplica promedio movil.

        Devuelve:
            Valor analogico filtrado de 0 a 4095.
        """

        valor = self._leer_joystick_crudo()

        self._historial_joystick.append(valor)
        if len(self._historial_joystick) > self.MUESTRAS_JOYSTICK:
            self._historial_joystick.pop(0)

        return int(sum(self._historial_joystick) / len(self._historial_joystick))

    # -------------------------------------------------------------------------
    def _direccion_joystick_instantanea(self, valor):
        """
        Parametros:
            valor: lectura analogica filtrada.

        Hace:
            Convierte el valor del joystick en direccion usando centro calibrado,
            zona muerta e histeresis de reingreso al centro.

        Devuelve:
            DERECHA, IZQUIERDA o CENTRO.
        """

        diferencia = valor - self._joystick_centro

        if self._joystick_direccion_estable == "DERECHA":
            if diferencia > self.JOYSTICK_ZONA_REINGRESO:
                return "DERECHA"
            return "CENTRO"

        if self._joystick_direccion_estable == "IZQUIERDA":
            if diferencia < -self.JOYSTICK_ZONA_REINGRESO:
                return "IZQUIERDA"
            return "CENTRO"

        if diferencia > self.JOYSTICK_ZONA_MUERTA:
            return "DERECHA"

        if diferencia < -self.JOYSTICK_ZONA_MUERTA:
            return "IZQUIERDA"

        return "CENTRO"

    # -------------------------------------------------------------------------
    def obtener_direccion_joystick_base(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Convierte el valor analogico del joystick en direccion estable.

        Devuelve:
            DERECHA, IZQUIERDA o CENTRO.
        """

        valor = self.leer_joystick_base()
        direccion = self._direccion_joystick_instantanea(valor)

        if direccion == self._joystick_direccion_estable:
            self._joystick_direccion_candidata = direccion
            self._joystick_conteo_candidata = 0
            return self._joystick_direccion_estable

        if direccion == self._joystick_direccion_candidata:
            self._joystick_conteo_candidata += 1
        else:
            self._joystick_direccion_candidata = direccion
            self._joystick_conteo_candidata = 1

        if self._joystick_conteo_candidata >= self.JOYSTICK_CONFIRMACIONES:
            self._joystick_direccion_estable = direccion
            self._joystick_conteo_candidata = 0

        return self._joystick_direccion_estable

    # -------------------------------------------------------------------------
    def obtener_joystick_base_interpretado(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Lee el joystick y devuelve valor crudo mas direccion estable.

        Devuelve:
            Diccionario con valor, direccion y centro calibrado.
        """

        valor = self.leer_joystick_base()
        direccion = self._direccion_joystick_instantanea(valor)

        if direccion == self._joystick_direccion_estable:
            self._joystick_direccion_candidata = direccion
            self._joystick_conteo_candidata = 0
        else:
            if direccion == self._joystick_direccion_candidata:
                self._joystick_conteo_candidata += 1
            else:
                self._joystick_direccion_candidata = direccion
                self._joystick_conteo_candidata = 1

            if self._joystick_conteo_candidata >= self.JOYSTICK_CONFIRMACIONES:
                self._joystick_direccion_estable = direccion
                self._joystick_conteo_candidata = 0

        return {
            "valor": valor,
            "direccion": self._joystick_direccion_estable,
            "centro": self._joystick_centro
        }

    # -------------------------------------------------------------------------
    def obtener_resumen(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Lee todos los sensores necesarios para el ciclo principal.

        Devuelve:
            Diccionario con presencia, distancia, joystick, centro y direccion.
        """

        joystick = self.obtener_joystick_base_interpretado()
        presencia = self.obtener_presencia()
        distancia = self.leer_distancia()

        return {
            "presencia": presencia,
            "distancia_cm": distancia,
            "joystick_base": joystick["valor"],
            "joystick_centro": joystick["centro"],
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
        self._led_actual = "APAGADO"

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
            Mueve la base de forma incremental.
            Si la direccion es CENTRO, conserva el angulo actual.

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
            Mantiene compatibilidad con versiones anteriores. Para el proyecto
            actual se recomienda mover con mover_base_por_direccion usando la
            direccion filtrada por CajaSensores.

        Devuelve:
            Angulo actual de la base.
        """

        direccion = "CENTRO"

        if valor_joystick > 3000:
            direccion = "DERECHA"
        elif valor_joystick < 1100:
            direccion = "IZQUIERDA"

        if invertir:
            if direccion == "DERECHA":
                direccion = "IZQUIERDA"
            elif direccion == "IZQUIERDA":
                direccion = "DERECHA"

        return self.mover_base_por_direccion(direccion, paso, minimo, maximo)

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
            self._led_actual = "ROJO"
        elif led == "AMARILLO":
            self._led_amarillo.value(1)
            self._led_actual = "AMARILLO"
        elif led == "AZUL":
            self._led_azul.value(1)
            self._led_actual = "AZUL"

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

        if self._led_actual == led:
            self._led_actual = "APAGADO"

    # -------------------------------------------------------------------------
    def apagar_leds(self):
        """
        Hace:
            Apaga todos los LEDs.
        """

        self._led_rojo.value(0)
        self._led_amarillo.value(0)
        self._led_azul.value(0)
        self._led_actual = "APAGADO"

    # -------------------------------------------------------------------------
    def encender_solo_led(self, led):
        """
        Parametros:
            led: ROJO, AMARILLO o AZUL.

        Hace:
            Apaga todos los LEDs y enciende solo uno.
            Si ese LED ya esta encendido, no vuelve a apagar/encender.
        """

        if self._led_actual == led:
            return

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
            - AMARILLO o SIN_LECTURA: lento y suave.
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
                self._buzzer.duty(220)
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

