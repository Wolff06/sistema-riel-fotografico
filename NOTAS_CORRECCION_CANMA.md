# CANMA corregido - notas rapidas de uso

Este paquete mantiene la estructura del proyecto, los pines del HAL y la interfaz Tkinter 800x480.

## Flujo corregido

1. Pestaña Sensores:
   - ON publica modo sensores y arranque.
   - OFF publica reposo y apaga LEDs/buzzer.
   - No permite entrar a Captura si Sensores sigue activo.

2. Pestaña Captura:
   - El boton con imagen abierto abre la camara.
   - Activar IA enciende el modelo YOLO y publica sistema/cmd/modo = ia.
   - Si se vuelve a presionar Desactivar IA, se publica reposo y estado seguro.
   - No permite volver a Sensores mientras IA siga activa.

3. Control de LEDs:
   - En modo sensores solo manda la distancia.
   - En modo IA solo manda el resultado de IA.
   - En reposo todos los LEDs y buzzer quedan apagados.

## Rangos de distancia

- <= 10 cm: rojo + buzzer rapido.
- 15 a 20 cm: azul + buzzer apagado.
- > 20 cm: amarillo + buzzer suave.
- 11 a 14 cm: amarillo para ajustar distancia.

## Pines conservados

- PIR: GPIO33
- Ultrasonico TRIG: GPIO25
- Ultrasonico ECHO: GPIO26
- Joystick VRx: GPIO35
- LED rojo: GPIO18
- LED amarillo: GPIO19
- LED azul: GPIO21
- Buzzer: GPIO27
- Servo base MG995: GPIO14
- Servo brazo: GPIO23

## Prueba rapida en Raspberry

Desde sistema/raspberry:

python3 main_interfaz_mqtt.py

Si la camara no abre, ejecutar una prueba de indices de camara con OpenCV.

## Importante para servo MG995

El MG995 no debe alimentarse del 3V3 del ESP32. Usar fuente externa de 5V a 6V con GND comun:

- Rojo del servo a +5V/+6V fuente externa.
- Cafe/negro del servo a GND fuente externa.
- GND fuente externa unido a GND ESP32.
- Naranja/amarillo del servo a GPIO14.
