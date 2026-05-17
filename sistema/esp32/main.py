#

import nucleo
import utime

ultima = utime.ticks_ms()
intervalo = 50

sm = nucleo.MaquinaEstado()

while True:
    actual = utime.ticks_ms()

    if utime.ticks_diff(actual, ultima) >= intervalo:
        ultima = actual

        if sm.estado == nucleo.ESTADO_BOOT:
            sm.boot()
        elif sm.estado == nucleo.ESTADO_ESPERA:
            sm.espera()
        elif sm.estado == nucleo.ESTADO_OPERANDO:
            sm.operando()
        elif sm.estado == nucleo.ESTADO_ERROR:
            sm.error()
