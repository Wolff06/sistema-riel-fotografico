
# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/esp32/nucleo/maquina_estado.py
#
# OBJETIVO:
# Gestionar WiFi, MQTT, sensores, actuadores y modo IA usando la HAL.
# Este archivo NO usa Pin, PWM ni ADC directamente.
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


class MaquinaEstado:
    """
    Controla el ciclo principal del ESP32.

    Modos internos:
    - reposo: LEDs y buzzer apagados.
    - sensores: LEDs y buzzer dependen de PIR + ultrasonico.
    - ia: LEDs y buzzer dependen del resultado publicado por la IA.
    """

    def __init__(self):
        """
        Parametros:
            Ninguno.

        Hace:
            Inicializa variables internas.
        """

        self.estado = ESTADO_BOOT

        self._actuadores = None
        self._sensores = None
        self.mqttBroker = None

        self._ultimo_envio_ms = 0
        self._intervalo_envio_ms = 500
        self._ultimo_estado_publicado = None

        # Modo activo: reposo, sensores o ia.
        self.modo_sistema = "reposo"
        self.ia_activa = False

        # Estado fisico que se mantiene en el ciclo para LEDs/buzzer.
        # Valores esperados: APAGADO, ROJO, AMARILLO, AZUL.
        self._estado_salida = "APAGADO"
        self._ultimo_estado_salida = None

        # Logica de movimiento basada en el codigo de Thonny.
        self._distancia_anterior = None
        self._ultimo_cambio_distancia = 0
        self._movimiento_usuario = False

        self.DISTANCIA_MUY_CERCA = 10
        self.DISTANCIA_IDEAL_MIN = 15
        self.DISTANCIA_IDEAL_MAX = 20
        self.CAMBIO_MAXIMO_PERMITIDO = 6

        # Histeresis para evitar parpadeos por ruido del ultrasonico.
        self.MARGEN_SALIDA_ROJO_CM = 2
        self.MARGEN_SALIDA_AZUL_CM = 2
        self.LECTURAS_CONFIRMAR_ESTADO = 3
        self._estado_sensores_estable = "AMARILLO"
        self._estado_sensores_candidato = "AMARILLO"
        self._conteo_estado_sensores = 0

        # Joystick/base.
        self.INVERTIR_BASE = False

    # ---------------------------------------------------------------------
    def transicion(self, nuevo_estado):
        """
        Parametros:
            nuevo_estado: nuevo estado del sistema.

        Hace:
            Cambia el estado interno.
        """

        print("Transicionando a", nuevo_estado)
        self.estado = nuevo_estado

    # ---------------------------------------------------------------------
    def boot(self):
        """
        Hace:
            Conecta WiFi, MQTT, inicializa sensores/actuadores y pasa a espera.
        """

        if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
            self._sensores = hardware.CajaSensores()
            self._actuadores = hardware.CajaActuadores()

            self._actuadores.mover_base(90)
            self._actuadores.estado_seguro()

            self.mqttBroker = comms.MQTTLink(
                comms.config.SERVIDOR_MQTT,
                comms.config.PUERTO_MQTT,
                comms.config.USUARIO_MQTT,
                comms.config.CLAVE_MQTT
            )

            self.mqttBroker.establecer_conexion_mqtt(callback=self._callback_mqtt)
            self._suscribir_comandos()

            self._publicar_estado("Iniciando")
            self._publicar_valores_iniciales()

            self.transicion(ESTADO_ESPERA)
            self._publicar_estado("Esperando instrucciones")

        else:
            self.transicion(ESTADO_ERROR)

    # ---------------------------------------------------------------------
    def espera(self):
        """
        Hace:
            Publica sensores y escucha MQTT. En modo IA mantiene activo el
            patron de LEDs/buzzer segun el ultimo resultado de IA.
        """

        if not comms.verificar_conexion():
            print("Conexion perdida en modo espera, reconectando...")

            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_ESPERA)
                self._publicar_estado("Esperando instrucciones")
            else:
                self.transicion(ESTADO_ERROR)

            return

        self._publicar_estado("Esperando instrucciones")

        # En espera no se permite que PIR/ultrasonico controlen LEDs.
        # El joystick si puede mover la base para ajustar la camara/garra.
        resumen = self._sensores.obtener_resumen()
        self._actualizar_servo_por_joystick(resumen)
        self._publicar_datos_sensores(resumen=resumen)

        # Si la IA esta activa, los sensores no controlan LEDs/buzzer.
        # Solo se mantiene el resultado fisico de IA.
        if self.modo_sistema == "ia":
            self._actualizar_salida_fisica()

        self._checar_mqtt()

    # ---------------------------------------------------------------------
    def operando(self):
        """
        Hace:
            En modo sensores, mueve servo con joystick y aplica logica de
            distancia/movimiento. En modo IA no deja que sensores controlen
            LEDs/buzzer.
        """

        if not comms.verificar_conexion():
            print("Conexion perdida durante operacion. Abortando...")
            self._publicar_estado("Abortando")
            self._publicar_error("Conexion perdida con el servidor")

            if self._actuadores is not None:
                self._actuadores.estado_seguro()

            if comms.conectar_wifi(comms.config.SSID, comms.config.CLAVE):
                self.transicion(ESTADO_OPERANDO)
                self._publicar_estado("Operando")
            else:
                self.transicion(ESTADO_ERROR)

            return

        self._publicar_estado("Operando")
        resumen = self._sensores.obtener_resumen()

        # El joystick mueve la base, pero ya viene filtrado por la HAL.
        self._actualizar_servo_por_joystick(resumen)

        if self.modo_sistema == "sensores":
            estado_fisico, cambio, movimiento_usuario = self._calcular_estado_sensores(resumen)
            self._estado_salida = estado_fisico
            self._actualizar_salida_fisica()
        elif self.modo_sistema == "ia":
            # En modo IA se ignora la logica fisica de sensores.
            cambio = self._ultimo_cambio_distancia
            movimiento_usuario = False
            self._actualizar_salida_fisica()
        else:
            cambio = self._ultimo_cambio_distancia
            movimiento_usuario = False
            self._estado_salida = "APAGADO"
            self._actualizar_salida_fisica()

        self._publicar_datos_sensores(
            resumen=resumen,
            estado_fisico=self._estado_salida,
            cambio_distancia=cambio,
            movimiento_usuario=movimiento_usuario
        )

        self._checar_mqtt()

    # ---------------------------------------------------------------------
    def error(self):
        """
        Hace:
            Activa estado seguro y publica error.
        """

        print("Estado de error")

        if self._actuadores is not None:
            self._actuadores.estado_seguro()

        self._publicar_estado("ERROR")
        self._publicar_error("Error en el sistema")

    # ---------------------------------------------------------------------
    def _callback_mqtt(self, topico, mensaje):
        """
        Parametros:
            topico: topico recibido.
            mensaje: mensaje recibido.

        Hace:
            Procesa comandos MQTT.
        """

        topico = self._decodificar(topico)
        mensaje = self._decodificar(mensaje).strip()

        print("MQTT recibido:", topico, "=", mensaje)

        if topico == comms.T_CMD_INICIAR_OP:
            self._procesar_comando_inicio(mensaje)

        elif topico == comms.T_CMD_MODO_SISTEMA:
            self._procesar_modo_sistema(mensaje)

        elif topico == comms.T_CMD_IA_ESTADO:
            self._procesar_estado_ia(mensaje)

        elif topico == comms.T_IA_RESULTADO:
            self._procesar_resultado_ia(mensaje)

        elif topico == comms.T_CMD_BASE_MOVER:
            self._procesar_comando_servo("base", mensaje)

        elif topico == comms.T_CMD_BRAZO_MOVER:
            self._procesar_comando_servo("brazo", mensaje)

        elif topico == comms.T_CMD_SERVO_MOVER:
            self._procesar_comando_servo("base", mensaje)

        elif topico == comms.T_CMD_LED_ESTADO_AZUL:
            self._procesar_comando_led("AZUL", mensaje)

        elif topico == comms.T_CMD_LED_ESTADO_AMARILLO:
            self._procesar_comando_led("AMARILLO", mensaje)

        elif topico == comms.T_CMD_LED_ESTADO_ROJO:
            self._procesar_comando_led("ROJO", mensaje)

        elif topico == comms.T_CMD_LED_PARPADEAR:
            self._procesar_comando_led_parpadear(mensaje)

        elif topico == comms.T_CMD_BUZZER:
            self._procesar_comando_buzzer(mensaje)

        elif topico == comms.T_CMD_SEGURO:
            self._activar_estado_seguro()

        else:
            print("Topico no manejado:", topico)

    # ---------------------------------------------------------------------
    def _suscribir_comandos(self):
        """
        Hace:
            Suscribe el ESP32 a todos los comandos necesarios.
        """

        topicos = [
            comms.T_CMD_INICIAR_OP,
            comms.T_CMD_SEGURO,
            comms.T_CMD_MODO_SISTEMA,
            comms.T_CMD_IA_ESTADO,
            comms.T_IA_RESULTADO,
            comms.T_CMD_BASE_MOVER,
            comms.T_CMD_BRAZO_MOVER,
            comms.T_CMD_SERVO_MOVER,
            comms.T_CMD_LED_ESTADO_AZUL,
            comms.T_CMD_LED_ESTADO_AMARILLO,
            comms.T_CMD_LED_ESTADO_ROJO,
            comms.T_CMD_LED_PARPADEAR,
            comms.T_CMD_BUZZER,
        ]

        for topico in topicos:
            self.mqttBroker.suscribir(topico)

    # ---------------------------------------------------------------------
    def _publicar_valores_iniciales(self):
        """
        Hace:
            Publica valores iniciales.
        """

        self._publicar(comms.T_SENSOR_PIR, "false")
        self._publicar(comms.T_SENSOR_ULTRASONICO, "null")
        self._publicar(comms.T_SENSOR_JOYSTICK_BASE, "0")
        self._publicar(comms.T_SENSOR_DIRECCION_BASE, "CENTRO")
        self._publicar(comms.T_ACTUADOR_BASE_GRADOS, "90")
        self._publicar(comms.T_ACTUADOR_BRAZO_GRADOS, "90")
        self._publicar(comms.T_ALERTA_ULTIMA, "Sistema en espera")

    # ---------------------------------------------------------------------
    def _clasificar_distancia_con_histeresis(self, distancia):
        """
        Parametros:
            distancia: distancia filtrada en centimetros.

        Hace:
            Clasifica la distancia usando zonas normales y margen de salida.
            El margen evita alternar rapidamente entre AZUL y AMARILLO o
            entre ROJO y AMARILLO cuando la lectura cae cerca del limite.

        Devuelve:
            ROJO, AZUL o AMARILLO.
        """

        if distancia is None or distancia <= 0:
            return "AMARILLO"

        estado_actual = self._estado_sensores_estable

        if estado_actual == "ROJO":
            if distancia <= self.DISTANCIA_MUY_CERCA + self.MARGEN_SALIDA_ROJO_CM:
                return "ROJO"

        if estado_actual == "AZUL":
            minimo_salida = self.DISTANCIA_IDEAL_MIN - self.MARGEN_SALIDA_AZUL_CM
            maximo_salida = self.DISTANCIA_IDEAL_MAX + self.MARGEN_SALIDA_AZUL_CM
            if minimo_salida <= distancia <= maximo_salida:
                return "AZUL"

        if distancia <= self.DISTANCIA_MUY_CERCA:
            return "ROJO"

        if self.DISTANCIA_IDEAL_MIN <= distancia <= self.DISTANCIA_IDEAL_MAX:
            return "AZUL"

        return "AMARILLO"

    # ---------------------------------------------------------------------
    def _confirmar_estado_sensores(self, candidato):
        """
        Parametros:
            candidato: color calculado por la distancia.

        Hace:
            Confirma el cambio de LED solo despues de varias lecturas iguales.
            Esto evita que un valor suelto del ultrasonico cambie el LED.

        Devuelve:
            Estado estable confirmado.
        """

        if candidato == self._estado_sensores_estable:
            self._estado_sensores_candidato = candidato
            self._conteo_estado_sensores = 0
            return self._estado_sensores_estable

        if candidato == self._estado_sensores_candidato:
            self._conteo_estado_sensores += 1
        else:
            self._estado_sensores_candidato = candidato
            self._conteo_estado_sensores = 1

        if self._conteo_estado_sensores >= self.LECTURAS_CONFIRMAR_ESTADO:
            self._estado_sensores_estable = candidato
            self._conteo_estado_sensores = 0

        return self._estado_sensores_estable

    # ---------------------------------------------------------------------
    def _calcular_estado_sensores(self, resumen):
        """
        Parametros:
            resumen: diccionario de CajaSensores.

        Hace:
            Aplica la regla solicitada para modo Sensores:
            - distancia <= 10 cm: ROJO y buzzer rapido.
            - distancia de 15 a 20 cm: AZUL y buzzer apagado.
            - distancia mayor a 20 cm: AMARILLO y buzzer suave.
            - distancia de 11 a 14 cm: AMARILLO para pedir ajuste.

            El PIR solo se reporta como movimiento true/false; no decide LED.
            El cambio de LED se confirma con histeresis para evitar parpadeos.

        Devuelve:
            estado_fisico, cambio_distancia, movimiento_usuario.
        """

        distancia = resumen.get("distancia_cm", resumen.get("distancia", None))
        pir_detectado = bool(resumen.get("presencia", False))

        if distancia is not None and distancia > 0:
            if self._distancia_anterior is not None and self._distancia_anterior > 0:
                cambio = abs(distancia - self._distancia_anterior)
            else:
                cambio = 0
            self._distancia_anterior = distancia
        else:
            cambio = 0

        self._ultimo_cambio_distancia = cambio
        movimiento_usuario = pir_detectado

        candidato = self._clasificar_distancia_con_histeresis(distancia)
        estado_fisico = self._confirmar_estado_sensores(candidato)

        self._movimiento_usuario = movimiento_usuario
        print("Modo sensores:", estado_fisico, "| Candidato:", candidato, "| Distancia:", distancia, "| Cambio:", round(cambio, 1), "| PIR:", pir_detectado)
        return estado_fisico, cambio, movimiento_usuario

    # ---------------------------------------------------------------------
    def _actualizar_salida_fisica(self):
        """
        Hace:
            Actualiza LEDs y buzzer de forma no bloqueante.
            Solo cambia de LED cuando cambia el estado, para evitar parpadeos.
        """

        if self._actuadores is None:
            return

        try:
            if self._estado_salida == "APAGADO":
                if self._ultimo_estado_salida != "APAGADO":
                    self._actuadores.estado_seguro()
                self._ultimo_estado_salida = "APAGADO"
                return

            if self._estado_salida != self._ultimo_estado_salida:
                if self._estado_salida == "ROJO":
                    self._actuadores.encender_solo_led("ROJO")
                elif self._estado_salida == "AZUL":
                    self._actuadores.encender_solo_led("AZUL")
                else:
                    self._actuadores.encender_solo_led("AMARILLO")

                self._ultimo_estado_salida = self._estado_salida

            self._actuadores.controlar_buzzer_por_estado(self._estado_salida)

        except Exception as error:
            print("Error actualizando salida fisica:", error)

    # ---------------------------------------------------------------------
    def _actualizar_servo_por_joystick(self, resumen):
        """
        Parametros:
            resumen: diccionario de CajaSensores.

        Hace:
            Mueve la base con la direccion filtrada del joystick.
            Si el joystick esta centrado, no mueve el servomotor.

        Devuelve:
            Angulo actual de la base.
        """

        if self._actuadores is None:
            return None

        direccion = resumen.get("direccion_base", "CENTRO")

        if self.INVERTIR_BASE:
            if direccion == "DERECHA":
                direccion = "IZQUIERDA"
            elif direccion == "IZQUIERDA":
                direccion = "DERECHA"

        return self._actuadores.mover_base_por_direccion(
            direccion,
            paso=1,
            minimo=0,
            maximo=180
        )

    # ---------------------------------------------------------------------
    def _publicar_datos_sensores(self, resumen=None, estado_fisico=None, cambio_distancia=None, movimiento_usuario=None):
        """
        Hace:
            Publica sensores y posicion de servos por MQTT.
        """

        actual = time.ticks_ms()

        if time.ticks_diff(actual, self._ultimo_envio_ms) < self._intervalo_envio_ms:
            return

        self._ultimo_envio_ms = actual

        if resumen is None:
            resumen = self._sensores.obtener_resumen()

        presencia = resumen.get("presencia", False)
        distancia = resumen.get("distancia_cm", resumen.get("distancia", None))
        joystick = resumen.get("joystick_base", 0)
        direccion = resumen.get("direccion_base", "CENTRO")
        centro_joystick = resumen.get("joystick_centro", "")

        if movimiento_usuario is None:
            movimiento_usuario = self._movimiento_usuario

        if estado_fisico is None:
            estado_fisico = self._estado_salida

        if cambio_distancia is None:
            cambio_distancia = self._ultimo_cambio_distancia

        angulo_base = self._actuadores.obtener_posicion_base()

        try:
            angulo_brazo = self._actuadores.obtener_posicion_brazo()
        except Exception:
            angulo_brazo = 90

        distancia_txt = "null" if distancia is None else str(round(distancia, 2))
        movimiento_txt = "true" if movimiento_usuario else "false"

        self._publicar(comms.T_SENSOR_PIR, movimiento_txt)
        self._publicar(comms.T_SENSOR_ULTRASONICO, distancia_txt)
        self._publicar(comms.T_SENSOR_JOYSTICK_BASE, str(joystick))
        self._publicar(comms.T_SENSOR_DIRECCION_BASE, direccion)
        self._publicar(comms.T_ACTUADOR_BASE_GRADOS, str(angulo_base))
        self._publicar(comms.T_ACTUADOR_BRAZO_GRADOS, str(angulo_brazo))

        print(
            "Modo:", self.modo_sistema,
            "| PIR crudo:", presencia,
            "| Movimiento:", movimiento_txt,
            "| Distancia:", distancia_txt,
            "| Cambio:", round(cambio_distancia, 1),
            "| Estado fisico:", estado_fisico,
            "| Joystick:", joystick,
            "| Centro:", centro_joystick,
            "| Direccion:", direccion,
            "| Base:", angulo_base
        )

    # ---------------------------------------------------------------------
    def _procesar_comando_inicio(self, mensaje):
        """
        Hace:
            Cambia entre OPERANDO y ESPERA.
        """

        mensaje = mensaje.lower()

        if mensaje in ("on", "iniciar", "true", "1"):
            self.modo_sistema = "sensores"
            self.ia_activa = False
            self._estado_salida = "APAGADO"
            self._ultimo_estado_salida = None
            self._distancia_anterior = None
            self._estado_sensores_estable = "AMARILLO"
            self._estado_sensores_candidato = "AMARILLO"
            self._conteo_estado_sensores = 0
            self.transicion(ESTADO_OPERANDO)
            self._publicar_estado("Operando")
            self._publicar(comms.T_ALERTA_ULTIMA, "Modo sensores activo")

        elif mensaje in ("off", "detener", "false", "0"):
            self.modo_sistema = "reposo"
            self.ia_activa = False
            self._estado_salida = "APAGADO"
            self._ultimo_estado_salida = None
            self._distancia_anterior = None
            self._estado_sensores_estable = "AMARILLO"
            self._estado_sensores_candidato = "AMARILLO"
            self._conteo_estado_sensores = 0

            if self._actuadores is not None:
                self._actuadores.estado_seguro()

            self.transicion(ESTADO_ESPERA)
            self._publicar_estado("Esperando instrucciones")
            self._publicar(comms.T_ALERTA_ULTIMA, "Sistema en reposo")

        else:
            self._publicar_error("Comando de inicio invalido")

    # ---------------------------------------------------------------------
    def _procesar_modo_sistema(self, mensaje):
        """
        Hace:
            Cambia el modo logico: sensores, ia o reposo.
        """

        modo = mensaje.lower().strip()

        if modo in ("sensores", "sensor"):
            self.modo_sistema = "sensores"
            self.ia_activa = False
            self._estado_salida = "APAGADO"
            self._ultimo_estado_salida = None
            self._publicar_estado("Modo sensores")

        elif modo in ("ia", "captura"):
            self.modo_sistema = "ia"
            self.ia_activa = True
            self._estado_salida = "AMARILLO"
            self._ultimo_estado_salida = None
            self.transicion(ESTADO_ESPERA)
            self._publicar_estado("Modo IA")
            self._publicar(comms.T_ALERTA_ULTIMA, "IA activa, esperando lectura")

        elif modo in ("reposo", "off", "apagado"):
            self.modo_sistema = "reposo"
            self.ia_activa = False
            self._estado_salida = "APAGADO"
            self._ultimo_estado_salida = None

            if self._actuadores is not None:
                self._actuadores.estado_seguro()

            self.transicion(ESTADO_ESPERA)
            self._publicar_estado("Esperando instrucciones")
            self._publicar(comms.T_ALERTA_ULTIMA, "Sistema en reposo")

        else:
            self._publicar_error("Modo de sistema invalido")

    # ---------------------------------------------------------------------
    def _procesar_estado_ia(self, mensaje):
        """
        Hace:
            Activa o apaga modo IA del lado ESP32.
        """

        mensaje = mensaje.lower().strip()

        if mensaje in ("on", "activar", "true", "1"):
            self.modo_sistema = "ia"
            self.ia_activa = True
            self._estado_salida = "AMARILLO"
            self._ultimo_estado_salida = None
            self.transicion(ESTADO_ESPERA)
            self._publicar_estado("Modo IA")
            self._publicar(comms.T_ALERTA_ULTIMA, "IA activa, esperando lectura")

        elif mensaje in ("off", "apagar", "false", "0"):
            self.modo_sistema = "reposo"
            self.ia_activa = False
            self._estado_salida = "APAGADO"
            self._ultimo_estado_salida = None

            if self._actuadores is not None:
                self._actuadores.estado_seguro()

            self.transicion(ESTADO_ESPERA)
            self._publicar_estado("IA desactivada")
            self._publicar(comms.T_ALERTA_ULTIMA, "IA desactivada")

    # ---------------------------------------------------------------------
    def _procesar_resultado_ia(self, mensaje):
        """
        Parametros:
            mensaje: JSON publicado por ia_processor_mqtt.py.

        Hace:
            Convierte resultado IA en actuadores fisicos.
        """

        if self.modo_sistema != "ia":
            print("Resultado IA ignorado porque el modo actual es", self.modo_sistema)
            return

        try:
            datos = ujson.loads(mensaje)
        except Exception:
            datos = {"lectura": mensaje}

        lectura = str(datos.get("lectura", "sin_lectura")).lower()
        clase = str(datos.get("clase", "Sin lectura"))
        confianza = datos.get("confianza", 0)

        if lectura == "herido":
            self._estado_salida = "ROJO"
            alerta = "IA: posible hallazgo visual detectado"
        elif lectura == "ileso":
            self._estado_salida = "AZUL"
            alerta = "IA: lectura sin alerta visual"
        else:
            self._estado_salida = "AMARILLO"
            alerta = "IA: sin lectura confiable"

        self._ultimo_estado_salida = None
        self._actualizar_salida_fisica()
        self._publicar(comms.T_ALERTA_ULTIMA, alerta + " | " + clase + " | confianza: " + str(confianza))

    # ---------------------------------------------------------------------
    def _procesar_comando_servo(self, servomotor, mensaje):
        """
        Hace:
            Mueve base o brazo por comando MQTT.
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

        except Exception as error:
            print("Error al mover servo por MQTT:", error)
            self._publicar_error("Comando de servo invalido")

    # ---------------------------------------------------------------------
    def _procesar_comando_led(self, led, mensaje):
        """
        Hace:
            Control manual de LED solo en reposo. En sensores o IA se ignora
            para evitar que dos logicas controlen LEDs al mismo tiempo.
        """

        if self.modo_sistema != "reposo":
            print("Comando LED ignorado. Modo activo:", self.modo_sistema)
            return

        mensaje = mensaje.lower()
        if mensaje == "on":
            self._actuadores.encender_solo_led(led)
        elif mensaje == "off":
            self._actuadores.apagar_led(led)
        elif mensaje == "blink":
            self._actuadores.parpadear_led(led)
        else:
            self._publicar_error("Comando de LED invalido")

    # ---------------------------------------------------------------------
    def _procesar_comando_led_parpadear(self, mensaje):
        """
        Hace:
            Parpadea un LED por JSON solo en reposo.
        """

        if self.modo_sistema != "reposo":
            print("Parpadeo de LED ignorado. Modo activo:", self.modo_sistema)
            return

        try:
            datos = ujson.loads(mensaje)
            led = datos.get("led", "AZUL")
            veces = int(datos.get("veces", 3))
            intervalo_ms = int(datos.get("intervalo_ms", 200))
            self._actuadores.parpadear_led(led, veces, intervalo_ms)
        except Exception as error:
            print("Error al parpadear LED:", error)
            self._publicar_error("Comando de parpadeo invalido")

    # ---------------------------------------------------------------------
    def _procesar_comando_buzzer(self, mensaje):
        """
        Hace:
            Ejecuta senales de buzzer solo en reposo.
        """

        if self.modo_sistema != "reposo":
            print("Comando de buzzer ignorado. Modo activo:", self.modo_sistema)
            return

        mensaje = mensaje.lower()

        if mensaje == "lista":
            self._ejecutar_senal("lista")
        elif mensaje == "quieta":
            self._ejecutar_senal("quieta")
        elif mensaje == "fin":
            self._ejecutar_senal("fin")
        else:
            self._publicar_error("Comando de buzzer invalido")

    # ---------------------------------------------------------------------
    def _activar_estado_seguro(self):
        """
        Hace:
            Apaga actuadores y vuelve a espera.
        """

        if self._actuadores is not None:
            self._actuadores.estado_seguro()

        self.modo_sistema = "reposo"
        self.ia_activa = False
        self._estado_salida = "APAGADO"
        self._ultimo_estado_salida = None
        self.transicion(ESTADO_ESPERA)
        self._publicar_estado("Estado seguro")

    # ---------------------------------------------------------------------
    def _extraer_angulo(self, mensaje):
        """
        Hace:
            Extrae angulo desde texto o JSON.
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

    # ---------------------------------------------------------------------
    def _ejecutar_senal(self, tipo):
        """
        Hace:
            Ejecuta senales del buzzer si existen en la HAL.
        """

        if self._actuadores is None:
            return

        if tipo == "lista":
            metodo = getattr(self._actuadores, "senal_lista", None)
            if metodo is not None:
                metodo()
        elif tipo == "quieta":
            metodo = getattr(self._actuadores, "senal_quieta", None)
            if metodo is not None:
                metodo()
        elif tipo == "fin":
            metodo = getattr(self._actuadores, "senal_fin_sesion", None)
            if metodo is not None:
                metodo()

    # ---------------------------------------------------------------------
    def _publicar_estado(self, estado):
        """
        Hace:
            Publica estado si cambio.
        """

        if estado != self._ultimo_estado_publicado:
            self._ultimo_estado_publicado = estado
            self._publicar(comms.T_SISTEMA_ESTADO, estado)

    # ---------------------------------------------------------------------
    def _publicar_error(self, mensaje):
        """
        Hace:
            Publica un error.
        """

        self._publicar(comms.T_SISTEMA_ERROR, mensaje)

    # ---------------------------------------------------------------------
    def _publicar(self, topico, mensaje):
        """
        Hace:
            Publica por MQTT si existe broker.
        """

        if self.mqttBroker is not None:
            try:
                self.mqttBroker.publicar(topico, str(mensaje))
            except Exception as error:
                print("Error publicando MQTT:", error)

    # ---------------------------------------------------------------------
    def _checar_mqtt(self):
        """
        Hace:
            Revisa mensajes pendientes.
        """

        if self.mqttBroker is not None:
            try:
                self.mqttBroker.checar_mensajes()
            except Exception as error:
                print("Error revisando mensajes MQTT:", error)

    # ---------------------------------------------------------------------
    def _decodificar(self, dato):
        """
        Hace:
            Convierte bytes a texto.
        """

        if isinstance(dato, bytes):
            return dato.decode("utf-8")

        return str(dato)