# -*- coding: utf-8 -*-
# Prueba rapida del servo base usando la HAL del proyecto.

import utime
import hardware

actuadores = hardware.CajaActuadores(centrar_servos=False)

while True:
    for angulo in (0, 45, 90, 135, 180, 90):
        print("Moviendo base a", angulo)
        actuadores.mover_base(angulo)
        utime.sleep_ms(1000)
