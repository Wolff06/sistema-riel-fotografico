# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# ARCHIVO:
# sistema/esp32/nucleo/__init__.py
#
# OBJETIVO:
# Exponer la máquina de estados del ESP32 para que pueda importarse desde main.py.
# =============================================================================

from .maquina_estado import (
    MaquinaEstado,
    ESTADO_BOOT,
    ESTADO_ESPERA,
    ESTADO_OPERANDO,
    ESTADO_ERROR
)
