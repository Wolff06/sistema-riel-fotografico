# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# ARCHIVO:
# sistema/esp32/comunicacion/comunicacion.py
#
# OBJETIVO:
# Definir la tabla oficial de tópicos MQTT del proyecto.
#
# JERARQUÍA:
# sistema/<subsistema>/<dispositivo>/<acción>
#
# IMPORTANTE:
# Todos los módulos del proyecto deben usar estos tópicos para evitar mezclar
# =============================================================================

# =============================================================================
# PUBLICACIÓN: ESP32 → Broker Mosquitto → Raspberry / Servidor Python
# =============================================================================

# -------------------------------------------------------------------------
# Sensores
# -------------------------------------------------------------------------

T_SENSOR_PIR = "sistema/sensores/pir"
# Valor esperado:
# "true"  → hay presencia o movimiento detectado.
# "false" → no hay presencia o movimiento detectado.

T_SENSOR_ULTRASONICO = "sistema/sensores/ultrasonico"
# Valor esperado:
# distancia aproximada en centímetros.
# Ejemplo: "25.4"
# Si no hay lectura válida: "null"

T_SENSOR_JOYSTICK_BASE = "sistema/sensores/joystick_base"
# Valor esperado:
# lectura analógica del joystick de la base.
# Rango aproximado: 0 a 4095.

T_SENSOR_DIRECCION_BASE = "sistema/sensores/direccion_base"
# Valor esperado:
# "DERECHA", "IZQUIERDA" o "CENTRO".

# -------------------------------------------------------------------------
# Actuadores / posiciones publicadas
# -------------------------------------------------------------------------

T_ACTUADOR_BASE_GRADOS = "sistema/actuadores/base/grados"
# Valor esperado:
# ángulo actual del servo de la base.
# Rango: 0 a 180.

T_ACTUADOR_BRAZO_GRADOS = "sistema/actuadores/brazo/grados"
# Valor esperado:
# ángulo actual del servo del brazo.
# Rango: 0 a 180.

# -------------------------------------------------------------------------
# Sistema
# -------------------------------------------------------------------------

T_SISTEMA_ESTADO = "sistema/estado"
# Valor esperado:
# "Iniciando", "Esperando instrucciones", "Operando", "Estado seguro",
# "Abortando", "ERROR", etc.

T_SISTEMA_ERROR = "sistema/error"
# Valor esperado:
# descripción breve del error.

T_ALERTA_ULTIMA = "sistema/alertas/ultima"
# Valor esperado:
# mensaje breve de alerta para que Raspberry lo muestre o guarde.

# -------------------------------------------------------------------------
# Inteligencia artificial
# -------------------------------------------------------------------------

T_IA_RESULTADO = "sistema/ia/resultado"
# Valor esperado:
# resultado de IA enviado desde Raspberry.
# Ejemplo JSON:
# {"clase":"Seno Herido","confianza":0.82,"alerta":true}


# =============================================================================
# SUSCRIPCIÓN: Raspberry / Servidor Python → Broker Mosquitto → ESP32
# =============================================================================

# -------------------------------------------------------------------------
# Control general
# -------------------------------------------------------------------------

T_CMD_INICIAR_OP = "sistema/cmd/iniciar"
# Valor esperado:
# "on", "iniciar", "true" o "1"  → pasar a OPERANDO.
# "off", "detener", "false" o "0" → volver a ESPERA.

T_CMD_SEGURO = "sistema/cmd/seguro"
# Valor esperado:
# cualquier mensaje.
# Activa estado seguro: apaga LEDs, silencia buzzer y detiene señal de servos.


# -------------------------------------------------------------------------
# Control de servos
# -------------------------------------------------------------------------

T_CMD_BASE_MOVER = "sistema/cmd/base/mover"
# Valor esperado:
# "90"
# o JSON:
# {"angulo": 90}

T_CMD_BRAZO_MOVER = "sistema/cmd/brazo/mover"
# Valor esperado:
# "90"
# o JSON:
# {"angulo": 90}

T_CMD_SERVO_MOVER = "sistema/cmd/servo/iniciar"
# Tópico conservado por compatibilidad con código anterior.
# Por defecto se usará para mover la base.
# Valor esperado:
# ángulo 0 a 180.


# -------------------------------------------------------------------------
# Control de LEDs
# -------------------------------------------------------------------------

T_CMD_LED_ESTADO_AZUL = "sistema/cmd/led/azul/estado"
# Valor esperado:
# "on", "off" o "blink".

T_CMD_LED_ESTADO_AMARILLO = "sistema/cmd/led/amarillo/estado"
# Valor esperado:
# "on", "off" o "blink".

T_CMD_LED_ESTADO_ROJO = "sistema/cmd/led/rojo/estado"
# Valor esperado:
# "on", "off" o "blink".

T_CMD_LED_PARPADEAR = "sistema/cmd/led/parpadear"
# Valor esperado:
# JSON:
# {"led": "AZUL", "veces": 3, "intervalo_ms": 200}

# -------------------------------------------------------------------------
# Control de buzzer
# -------------------------------------------------------------------------

T_CMD_BUZZER = "sistema/cmd/buzzer/senal"
# Valor esperado:
# "lista", "quieta" o "fin".
