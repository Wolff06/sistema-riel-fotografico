# =============================================================================
# PROYECTO: Sistema de Riel Semicircular Fotográfico 180°
# INTEGRANTES: 
#              Macias Campos Ariadne Lizett 
#              Soto Garnica Ari Adair 
#              Lira Gamiño Luis Fernando 


# DESCRIPCIÓN: Script principal del ESP32. Coordina el barrido fotográfico de
#              180° usando la biblioteca de clases 'dispositivos.py'. La RPi
#              envía el comando "FOTO_OK" por USB-Serial cuando termina de
#              capturar; el ESP32 avanza al siguiente ángulo y confirma.
#              Toda la interacción con el hardware ocurre exclusivamente
#              a través de CajaSensores y CajaActuadores.
# =============================================================================

from dispositivos import CajaSensores, CajaActuadores
import time
import sys

# =============================================================================
# PARÁMETROS DEL BARRIDO
# =============================================================================

ANGULO_TOTAL       = 180    # grados totales del arco
PASOS_DE_BARRIDO   = 12     # número de fotos por sesión (cada 15 grados)
ANGULO_POR_PASO    = ANGULO_TOTAL / PASOS_DE_BARRIDO   # 15° por foto
TIEMPO_ESPERA_MS   = 300    # ms de espera tras mover antes de pedir foto
TIEMPO_PIR_MS      = 3000   # ms que el PIR debe confirmar presencia continua

# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================

sensores = CajaSensores()
accion   = CajaActuadores()

print("=" * 40)
print("SISTEMA RIEL SEMICIRCULAR 180°")
print("Iniciando...")
print("=" * 40)

# Rutina de homing: llevar carrito al extremo izquierdo (posición 0°)
print("Ejecutando homing — buscando límite izquierdo...")
accion.ir_a_inicio()
print("Homing completado. Posición: 0°")

# Señal sonora y visual: sistema listo
accion.señal_lista()
accion.parpadear_led(veces=2, intervalo_ms=150)

# =============================================================================
# BUCLE PRINCIPAL
# =============================================================================

try:
    while True:

        # ----------------------------------------------------------------
        # ETAPA 1: Esperar persona en posición (PIR confirma presencia)
        # ----------------------------------------------------------------
        print("\nEsperando persona en posición...")
        accion.apagar_led()

        tiempo_presencia_ms = 0
        while tiempo_presencia_ms < TIEMPO_PIR_MS:
            estado = sensores.obtener_resumen()

            if estado["presencia"]:
                tiempo_presencia_ms += 100
            else:
                tiempo_presencia_ms = 0   # reiniciar si la persona se mueve

            time.sleep_ms(100)

        # Presencia confirmada
        print("Persona detectada y estable. Iniciando barrido.")
        accion.señal_quieta()    # pedir que no se mueva
        accion.encender_led()    # LED encendido = sesión activa
        time.sleep_ms(500)       # pausa para que la señal llegue

        # ----------------------------------------------------------------
        # ETAPA 2: Homing previo al barrido (carrito siempre arranca en 0°)
        # ----------------------------------------------------------------
        accion.ir_a_inicio()

        # ----------------------------------------------------------------
        # ETAPA 3: Barrido de 0° a 180° tomando fotos en cada posición
        # ----------------------------------------------------------------
        barrido_exitoso = True

        for numero_foto in range(PASOS_DE_BARRIDO + 1):

            posicion_actual = sensores.obtener_resumen()

            # Si la persona se retiró durante el barrido: abortar
            if not posicion_actual["presencia"]:
                print("¡Persona se retiró! Abortando barrido.")
                barrido_exitoso = False
                break

            # Si algún límite inesperado: detener
            if posicion_actual["limite_der"] and numero_foto < PASOS_DE_BARRIDO:
                print("Límite derecho alcanzado antes de completar barrido.")
                barrido_exitoso = False
                break

            angulo_actual = accion.obtener_posicion_grados()
            print("Posición: {:.1f}° — solicitando foto {}".format(
                angulo_actual, numero_foto + 1))

            # Enviar señal a Raspberry Pi por puerto serie USB
            # La RPi escucha este mensaje y dispara la cámara
            sys.stdout.write("TOMAR_FOTO:{:.1f}\n".format(angulo_actual))

            # Esperar confirmación de la RPi ("FOTO_OK\n")
            respuesta = ""
            tiempo_limite = time.ticks_ms() + 5000   # esperar máximo 5 segundos
            while "FOTO_OK" not in respuesta:
                if time.ticks_diff(time.ticks_ms(), tiempo_limite) > 0:
                    print("Timeout esperando confirmación de RPi.")
                    barrido_exitoso = False
                    break
                if sys.stdin in [sys.stdin]:  # lectura no bloqueante
                    try:
                        linea = sys.stdin.readline()
                        if linea:
                            respuesta += linea
                    except Exception:
                        pass
                time.sleep_ms(50)

            if not barrido_exitoso:
                break

            print("Foto {} confirmada.".format(numero_foto + 1))

            # Mover al siguiente ángulo (excepto en la última posición)
            if numero_foto < PASOS_DE_BARRIDO:
                time.sleep_ms(TIEMPO_ESPERA_MS)
                accion.mover_angulo(ANGULO_POR_PASO)

        # ----------------------------------------------------------------
        # ETAPA 4: Fin de sesión
        # ----------------------------------------------------------------
        accion.estado_seguro()   # apagar todo de forma segura

        if barrido_exitoso:
            print("\nSesión completada exitosamente.")
            accion.señal_fin_sesion()
            accion.parpadear_led(veces=4, intervalo_ms=100)
        else:
            print("\nSesión interrumpida.")
            accion.parpadear_led(veces=2, intervalo_ms=500)

        # Regresar carrito a posición de inicio para la próxima persona
        accion.ir_a_inicio()
        accion.señal_lista()
        print("\nSistema listo para la siguiente persona.")

except KeyboardInterrupt:
    # Control+C desde la consola: apagar todo de forma limpia
    print("\nInterrupción manual. Aplicando estado seguro...")
    accion.estado_seguro()
    print("Sistema detenido.")

except Exception as error:
    # Cualquier error inesperado: estado seguro antes de propagar
    accion.estado_seguro()
    print("Error inesperado:", error)
    raise
