# -*- coding: utf-8 -*-
# Prueba rapida del servo base usando la HAL del proyecto.
# =============================================================================
# PROYECTO: PROYECTO: CANMA - Garra Robotica con Camara e IA
# - OBJETIVO DEL CODIGO -
# Probar el movimiento del servomotor de la base de la garra/cámara recorriendo varios ángulos de forma automática.
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# =============================================================================
import utime
import hardware

actuadores = hardware.CajaActuadores(centrar_servos=False)

while True:
    for angulo in (0, 45, 90, 135, 180, 90):
        print("Moviendo base a", angulo)
        actuadores.mover_base(angulo)
        utime.sleep_ms(1000)
