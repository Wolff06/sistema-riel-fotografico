
# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# ARCHIVO: sistema/esp32/hardware/__init__.py
#
# DESCRIPCION:
# Expone las clases de la biblioteca HAL para que el programa principal,
# la maquina de estados y las pruebas puedan usar sensores y actuadores sin
# importar directamente primitivas de MicroPython.
# =============================================================================

from .dispositivos import SensorBox, ActuatorBox, CajaSensores, CajaActuadores



