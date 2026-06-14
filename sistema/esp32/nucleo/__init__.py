# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# ARCHIVO:
# sistema/esp32/nucleo/__init__.py
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
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
