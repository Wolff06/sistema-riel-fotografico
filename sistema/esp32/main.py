#

import nucleo
import utime

ultima = utime.ticks_ms()
intervalo = 50

sm = MaquinaEstado()

while True:
    actual = utime.ticks_ms()

    if utime.ticks_diff(actual, ultima) >= intervalo:
        ultima = actual

        if sm.estado == nucleo.ESTADO_BOOT:
            sm.boot(SSID, PASSWORD)
        elif sm.estado == nucleo.ESTADO_ESPERA:
            sm.espera(SSID, PASSWORD)
        elif sm.estado == nucleo.ESTADO_OPERANDO:
            sm.operando(SSID, PASSWORD)
        elif sm.estado == nucleo.ESTADO_ERROR:
            sm.error()
