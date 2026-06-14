# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/esp32/comunicacion/comunicacion.py
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# OBJETIVO:
# Definir la tabla oficial de topicos MQTT del proyecto.
# =============================================================================

# =============================================================================
# PUBLICACION: ESP32 -> Mosquitto -> Raspberry / Interfaz
# =============================================================================

T_SENSOR_PIR = "sistema/sensores/pir"
T_SENSOR_ULTRASONICO = "sistema/sensores/ultrasonico"
T_SENSOR_JOYSTICK_BASE = "sistema/sensores/joystick_base"
T_SENSOR_DIRECCION_BASE = "sistema/sensores/direccion_base"

T_ACTUADOR_BASE_GRADOS = "sistema/actuadores/base/grados"
T_ACTUADOR_BRAZO_GRADOS = "sistema/actuadores/brazo/grados"

T_SISTEMA_ESTADO = "sistema/estado"
T_SISTEMA_ERROR = "sistema/error"
T_ALERTA_ULTIMA = "sistema/alertas/ultima"

# Resultado publicado por el procesador de IA en Raspberry.
# El ESP32 tambien se suscribe a este topico cuando esta en modo IA.
T_IA_RESULTADO = "sistema/ia/resultado"

# =============================================================================
# SUSCRIPCION: Raspberry / Interfaz / IA -> Mosquitto -> ESP32
# =============================================================================

T_CMD_INICIAR_OP = "sistema/cmd/iniciar"
T_CMD_SEGURO = "sistema/cmd/seguro"

# Modo general del sistema.
# sensores: LEDs/buzzer responden a PIR + ultrasonico.
# ia: LEDs/buzzer responden al resultado de IA.
# reposo: LEDs/buzzer apagados.
T_CMD_MODO_SISTEMA = "sistema/cmd/modo"

# Orden para activar o apagar el procesador de IA en Raspberry.
# La interfaz publica aqui. El ESP32 tambien lo escucha para cambiar modo.
T_CMD_IA_ESTADO = "sistema/cmd/ia/estado"

T_CMD_BASE_MOVER = "sistema/cmd/base/mover"
T_CMD_BRAZO_MOVER = "sistema/cmd/brazo/mover"
T_CMD_SERVO_MOVER = "sistema/cmd/servo/iniciar"

T_CMD_LED_ESTADO_AZUL = "sistema/cmd/led/azul/estado"
T_CMD_LED_ESTADO_AMARILLO = "sistema/cmd/led/amarillo/estado"
T_CMD_LED_ESTADO_ROJO = "sistema/cmd/led/rojo/estado"
T_CMD_LED_PARPADEAR = "sistema/cmd/led/parpadear"

T_CMD_BUZZER = "sistema/cmd/buzzer/senal"

