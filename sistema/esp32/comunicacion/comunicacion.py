# =============================================================================
# TABLA DE TÓPICOS MQTT
# Jerarquía: sistema/<subsistema>/<dispositivo>/<acción>
# =============================================================================
# =============================================================================
# PUBLICACIÓN: ESP32 → Broker Mosquitto → Raspberry / Servidor Python
# =============================================================================

# Sensores
T_SENSOR_PIR = "sistema/sensores/pir"
# bool/string: "true" si hay presencia o movimiento, "false" si no hay.

T_SENSOR_ULTRASONICO = "sistema/sensores/ultrasonico"
# float/string: distancia aproximada en centímetros. Ejemplo: "25.4"

T_SENSOR_JOYSTICK_BASE = "sistema/sensores/joystick_base"
# int/string: valor analógico del joystick de la base. Rango aproximado: 0 a 4095.

T_SENSOR_DIRECCION_BASE = "sistema/sensores/direccion_base"
# string: "DERECHA", "IZQUIERDA" o "CENTRO".

# Actuadores / posiciones
T_ACTUADOR_BASE_GRADOS = "sistema/actuadores/base/grados"
# int/string: ángulo actual del servo de la base. Rango: 0 a 180.

T_ACTUADOR_BRAZO_GRADOS = "sistema/actuadores/brazo/grados"
# int/string: ángulo actual del servo del brazo, si después se usa.

# Sistema
T_SISTEMA_ESTADO = "sistema/estado"
# string: "Iniciando", "Esperando instrucciones", "Operando", "ERROR", etc.

T_SISTEMA_ERROR = "sistema/error"
# string: descripción del error.

# =============================================================================
# SUSCRIPCIÓN: Raspberry / Servidor Python → Broker Mosquitto → ESP32
# =============================================================================

T_CMD_INICIAR_OP = "sistema/cmd/iniciar"
# string: "on" para iniciar operación, "off" para volver a espera.

T_CMD_BASE_MOVER = "sistema/cmd/base/mover"
# int/string o JSON:
# "90"
# {"angulo": 90}

T_CMD_BRAZO_MOVER = "sistema/cmd/brazo/mover"
# int/string o JSON:
# "90"
# {"angulo": 90}

# Se conserva este tópico para compatibilidad con código anterior.
T_CMD_SERVO_MOVER = "sistema/cmd/servo/iniciar"
# int/string: ángulo 0 a 180.

T_CMD_LED_ESTADO_AZUL = "sistema/cmd/led/azul/estado"
# string: "on", "off" o "blink".

T_CMD_LED_ESTADO_AMARILLO = "sistema/cmd/led/amarillo/estado"
# string: "on", "off" o "blink".

T_CMD_LED_ESTADO_ROJO = "sistema/cmd/led/rojo/estado"
# string: "on", "off" o "blink".

T_CMD_LED_PARPADEAR = "sistema/cmd/led/parpadear"
# JSON: {"led": "AZUL", "veces": 3, "intervalo_ms": 200}

T_CMD_BUZZER = "sistema/cmd/buzzer/senal"
# string: "lista", "quieta" o "fin".

T_CMD_SEGURO = "sistema/cmd/seguro"
# string: cualquier mensaje. Activa estado seguro.

