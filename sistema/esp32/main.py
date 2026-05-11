#

import nucleo

sm = MaquinaEstado()

while True:
    if sm.estado == nucleo.ESTADO_BOOT:
        sm.handle_boot(SSID, PASSWORD)
    elif sm.estado == nucleo.ESTADO_ESPERA:
        sm.handle_standby(SSID, PASSWORD)
    elif sm.estado == nucleo.ESTADO_OPERANDO:
        sm.handle_operation(SSID, PASSWORD)
    elif sm.estado == nucleo.ESTADO_ERROR:
        sm.handle_error()

    time.sleep(1)
