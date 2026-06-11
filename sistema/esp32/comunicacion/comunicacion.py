

# =============================================================================
# TABLA DE TÓPICOS MQTT
# Jerarquía: sistema/<subsistema>/<dispositivo>/<acción>
# =============================================================================

# --- PUBLICACIÓN (ESP32 → Broker → Servidor Python) -------------------------
T_SENSOR_PIR         = "sistema/sensores/pir"           # bool: presencia detectada
T_SENSOR_ULTRASONICO = "sistema/sensores/ultrasonico"   # str: "{medida} cm"
T_SISTEMA_ESTADO     = "sistema/estado"         # str: IDLE / FUNCIONANDO / ERROR
T_SISTEMA_ERROR      = "sistema/error"          # str: descripción del error

# --- SUSCRIPCIÓN (Servidor Python → Broker → ESP32) -------------------------
T_CMD_INICIAR_OP 	= "sistema/cmd/iniciar" # str: "on" | "off"
T_CMD_SERVO_MOVER    = "sistema/cmd/servo/iniciar"    # int: angulo 0-180
T_CMD_LED_ESTADO_AZUL= "sistema/cmd/led/azul/estado"         # str: "on" | "off" | "blink"
T_CMD_LED_ESTADO_AMARILLO= "sistema/cmd/led/amarillo/estado"     # str: "on" | "off" | "blink"
T_CMD_LED_ESTADO_ROJO= "sistema/cmd/led/rojo/estado"         # str: "on" | "off" | "blink"
T_CMD_LED_PARPADEAR  = "sistema/cmd/led/parpadear"      # JSON: {"veces": int, "intervalo_ms": int}
T_CMD_BUZZER         = "sistema/cmd/buzzer/señal"       # str: "lista" | "quieta" | "fin"


