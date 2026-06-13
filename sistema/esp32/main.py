# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# INTEGRANTES: Escribir aqui los nombres de los integrantes del equipo
# ARCHIVO: sistema/esp32/main.py
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# DESCRIPCION:
# Programa principal del ESP32. Ejecuta la maquina de estados del sistema CANMA.
# Este archivo no usa clases ni funciones directas de hardware de MicroPython.
# Todo acceso a sensores y actuadores se realiza mediante la biblioteca HAL
# ubicada en hardware/dispositivos.py.
# =============================================================================

import nucleo
import utime

INTERVALO_CICLO_MS = 50

ultima = utime.ticks_ms()
sm = nucleo.MaquinaEstado()

while True:
    actual = utime.ticks_ms()

    if utime.ticks_diff(actual, ultima) >= INTERVALO_CICLO_MS:
        ultima = actual

        if sm.estado == nucleo.ESTADO_BOOT:
            sm.boot()
        elif sm.estado == nucleo.ESTADO_ESPERA:
            sm.espera()
        elif sm.estado == nucleo.ESTADO_OPERANDO:
            sm.operando()
        elif sm.estado == nucleo.ESTADO_ERROR:
            sm.error()

