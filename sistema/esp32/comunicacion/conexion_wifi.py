#

import network
import time

def conectar_wifi(ssid, password, intentos=5, delay=2):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    wlan.active(True)
    intento = 0
    while not wlan.isconnected() and intento < intentos:
        print(f"Intento {intento+1} para conectar...")
        wlan.connect(ssid, password)
        time.sleep(delay)
        intento += 1
    if wlan.isconnected():
        print("Conectado:", wlan.ifconfig())
        return True
    else:
        print("Fallo al conectar.")
        return False

def verificar_conexion():
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()
