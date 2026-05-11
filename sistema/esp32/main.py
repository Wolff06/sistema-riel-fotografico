#

import nucleo

sm = MaquinaEstado()

while True:
    if sm.estado == nucleo.ESTADO_BOOT:
        sm.boot(SSID, PASSWORD)
    elif sm.estado == nucleo.ESTADO_ESPERA:
        sm.espera(SSID, PASSWORD)
    elif sm.estado == nucleo.ESTADO_OPERANDO:
        sm.operando(SSID, PASSWORD)
    elif sm.estado == nucleo.ESTADO_ERROR:
        sm.error()

    time.sleep(1)
