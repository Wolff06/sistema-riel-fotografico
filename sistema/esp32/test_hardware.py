# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# INTEGRANTES: Escribir aqui los nombres de los integrantes del equipo
# ARCHIVO: sistema/esp32/test_hardware.py
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# DESCRIPCION:
# Prueba general de la entrega E1. Demuestra los metodos principales de
# SensorBox y ActuatorBox sin usar primitivas de hardware directamente. Para
# ejecutar esta prueba en la ESP32, subir este archivo junto con las carpetas
# hardware, comunicacion y nucleo, y ejecutarlo desde Thonny o guardarlo como
# main.py temporalmente solo para la prueba.
# =============================================================================

import utime
import hardware


# =============================================================================
# PRUEBA DE SENSORES
# =============================================================================

def probar_sensores(sensores):
    """
    Parametros:
        sensores: objeto SensorBox.

    Hace:
        Lee PIR, ultrasonico y joystick. Imprime valores interpretados con
        unidad, promedio movil y resumen global.

    Devuelve:
        Nada.
    """

    print("\n========== PRUEBA DE SENSORES ==========")

    for numero in range(5):
        presencia = sensores.obtener_presencia_interpretada()
        distancia = sensores.obtener_distancia_interpretada()
        joystick = sensores.obtener_joystick_base_interpretado()
        resumen = sensores.obtener_resumen()

        print("\nLectura", numero + 1)
        print("PIR:", presencia["descripcion"], "| Valor:", presencia["valor"], "| Unidad:", presencia["unidad"])
        print("Ultrasonico:", distancia["valor"], distancia["unidad"], "| Promedio movil:", distancia["promedio_movil"], "| Estado:", distancia["descripcion"])
        print("Joystick:", joystick["valor"], joystick["unidad"], "| Promedio movil:", joystick["promedio_movil"], "| Centro:", joystick["centro"], "| Direccion:", joystick["direccion"])
        print("Resumen global:", resumen)

        utime.sleep_ms(700)


# =============================================================================
# PRUEBA DE ACTUADORES
# =============================================================================

def probar_actuadores(actuadores):
    """
    Parametros:
        actuadores: objeto ActuatorBox.

    Hace:
        Prueba LEDs, buzzer, servo base, servo brazo, movimiento por direccion,
        movimiento por joystick y estado seguro.

    Devuelve:
        Nada.
    """

    print("\n========== PRUEBA DE ACTUADORES ==========")

    print("Estado seguro inicial")
    actuadores.estado_seguro()
    utime.sleep_ms(800)

    print("\nProbando LEDs")
    for led in ("ROJO", "AMARILLO", "AZUL"):
        print("Encendiendo solo LED", led)
        actuadores.encender_solo_led(led)
        utime.sleep_ms(700)
        actuadores.apagar_led(led)
        utime.sleep_ms(250)

    print("Parpadeando LED azul")
    actuadores.parpadear_led("AZUL", veces=3, intervalo_ms=150)

    print("\nProbando buzzer")
    actuadores.encender_buzzer(frecuencia=1000, intensidad=350)
    utime.sleep_ms(300)
    actuadores.apagar_buzzer()
    utime.sleep_ms(300)
    actuadores.senal_lista()
    utime.sleep_ms(300)
    actuadores.senal_quieta()
    utime.sleep_ms(300)
    actuadores.senal_fin_sesion()

    print("\nProbando servo de base")
    for angulo in (0, 45, 90, 135, 180, 90):
        posicion = actuadores.mover_base(angulo)
        print("Base en", posicion, "grados")
        utime.sleep_ms(700)

    print("\nProbando servo de brazo")
    for angulo in (30, 90, 150, 90):
        posicion = actuadores.mover_brazo(angulo)
        print("Brazo en", posicion, "grados")
        utime.sleep_ms(700)

    print("\nProbando movimiento por direccion")
    actuadores.mover_base(90)
    for direccion in ("DERECHA", "DERECHA", "IZQUIERDA", "CENTRO"):
        posicion = actuadores.mover_base_por_direccion(direccion, paso=10)
        print("Direccion:", direccion, "| Base:", posicion, "grados")
        utime.sleep_ms(500)

    print("\nProbando movimiento simulado por joystick")
    for valor in (3200, 3200, 900, 900, 2048):
        posicion = actuadores.mover_base_desde_joystick(valor, paso=5)
        print("Joystick:", valor, "| Base:", posicion, "grados")
        utime.sleep_ms(500)

    print("\nEstado actual de actuadores:", actuadores.obtener_estado_actuadores())

    print("Aplicando estado seguro final")
    actuadores.estado_seguro()
    print("Estado final:", actuadores.obtener_estado_actuadores())


# =============================================================================
# EJECUCION COMPLETA DE E1
# =============================================================================

def ejecutar_prueba_e1():
    """
    Parametros:
        Ninguno.

    Hace:
        Crea SensorBox y ActuatorBox, ejecuta la prueba completa solicitada en
        E1 e imprime evidencia de funcionamiento en consola.

    Devuelve:
        Nada.
    """

    print("==========================================")
    print("CANMA - PRUEBA E1 BIBLIOTECA HAL")
    print("No se usan primitivas de hardware fuera de dispositivos.py")
    print("==========================================")

    sensores = hardware.SensorBox()
    actuadores = hardware.ActuatorBox(centrar_servos=False)

    probar_sensores(sensores)
    probar_actuadores(actuadores)

    print("\nPrueba E1 terminada correctamente")


ejecutar_prueba_e1()
