# CANMA — Garra Robótica con Cámara e IA para Apoyo en la Detección de Cáncer de Mama

## Descripción del proyecto

CANMA es un prototipo académico de una garra robótica controlada con ESP32 y Raspberry Pi. El sistema integra sensores, actuadores, comunicación MQTT, interfaz gráfica e inteligencia artificial en servidor externo para apoyar el análisis visual de imágenes relacionadas con posibles indicios de cáncer de mama.

El prototipo utiliza una ESP32 con MicroPython para leer sensores y controlar actuadores físicos. La Raspberry Pi funciona como estación central: crea la red local, ejecuta Mosquitto como broker MQTT, muestra la interfaz gráfica y procesa datos recibidos desde el ESP32.

> **Nota importante:** Este proyecto es académico y experimental. No sustituye diagnóstico médico profesional ni debe usarse como herramienta clínica definitiva.

---

## Integrantes

* Macias Campos Ariadne Lizett
* Soto Garnica Ari Adair
* Lira Gamiño Luis Fernando

---

## Objetivo general

Diseñar e implementar un prototipo funcional de garra robótica con cámara, sensores y actuadores, capaz de comunicarse mediante MQTT con una Raspberry Pi para mostrar información en una interfaz gráfica, controlar el movimiento de la cámara/base, registrar eventos del sistema y preparar el flujo para el análisis de imágenes mediante inteligencia artificial en servidor externo.

---

## Arquitectura general del sistema

```text
┌─────────────────────────────────────────────────────────────────────┐
│                           SISTEMA CANMA                              │
│                                                                     │
│  ┌─────────────────────┐       MQTT       ┌──────────────────────┐  │
│  │        ESP32         │ ◄──────────────► │   Mosquitto Broker   │  │
│  │    MicroPython       │                  │    Raspberry Pi      │  │
│  └─────────┬───────────┘                  └──────────┬───────────┘  │
│            │                                         │              │
│            │                                         │              │
│  ┌─────────▼───────────┐                  ┌──────────▼───────────┐  │
│  │     HAL Hardware     │                  │     MQTT Bridge      │  │
│  │   dispositivos.py    │                  │    mqtt_bridge.py    │  │
│  └─────────┬───────────┘                  └──────────┬───────────┘  │
│            │                                         │              │
│  ┌─────────▼───────────┐                  ┌──────────▼───────────┐  │
│  │  Sensores/Actuadores │                  │  Interfaz Tkinter    │  │
│  │ PIR · Ultrasónico    │                  │ vista_pantalla.py    │  │
│  │ Joystick · Servos    │                  └──────────┬───────────┘  │
│  │ LED · Buzzer         │                             │              │
│  └─────────────────────┘                  ┌──────────▼───────────┐  │
│                                           │ IA / Firebase         │  │
│                                           │ En integración        │  │
│                                           └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tecnologías utilizadas

| Componente                | Tecnología                                  |
| ------------------------- | ------------------------------------------- |
| Microcontrolador          | ESP32 con MicroPython                       |
| Broker MQTT               | Mosquitto en Raspberry Pi                   |
| Comunicación              | MQTT                                        |
| Interfaz gráfica          | Python + Tkinter                            |
| Cliente MQTT en Raspberry | paho-mqtt                                   |
| Procesamiento de imagen   | OpenCV / YOLO                               |
| Base de datos             | Firebase, pendiente de integración completa |
| Arquitectura de hardware  | HAL mediante `dispositivos.py`              |

---

## Estado actual del proyecto

### Implementado

* Estructura de carpetas separada para ESP32 y Raspberry.
* HAL en ESP32 mediante `CajaSensores` y `CajaActuadores`.
* Lectura de sensor PIR.
* Lectura de sensor ultrasónico.
* Lectura de joystick de base.
* Control de servo base.
* Control preparado para servo de brazo.
* Control de LEDs y buzzer.
* Máquina de estados en ESP32.
* Tabla de tópicos MQTT con jerarquía `sistema/...`.
* Comunicación MQTT base entre ESP32 y Mosquitto.
* Interfaz gráfica para Raspberry adaptada a 800x480.
* Botones ON/OFF en interfaz para cambiar el estado del ESP32.
* Flechas en interfaz para solicitar movimiento de la base.
* Bridge MQTT en Raspberry para recibir datos y publicar comandos.
* Script para crear hotspot en Raspberry.

### En integración

* Conexión completa de la interfaz con datos reales MQTT.
* Registro de eventos en Firebase.
* Integración del resultado de IA con MQTT.
* Almacenamiento histórico de sensores y alertas.
* Flujo completo cámara → IA → MQTT → actuador → Firebase.

---

## Estructura actual recomendada del repositorio

```text
sistema-riel-fotografico/
│
├── README.md
│
└── sistema/
    │
    ├── esp32/
    │   ├── main.py
    │   │
    │   ├── comunicacion/
    │   │   ├── __init__.py
    │   │   ├── config.py
    │   │   ├── comunicacion.py
    │   │   ├── conexion_wifi.py
    │   │   └── conexion_mosquitto.py
    │   │
    │   ├── hardware/
    │   │   ├── __init__.py
    │   │   └── dispositivos.py
    │   │
    │   └── nucleo/
    │       ├── __init__.py
    │       └── maquina_estado.py
    │
    └── raspberry/
        ├── main_interfaz_mqtt.py
        │
        ├── comunicacion/
        │   ├── crear_hotspot.sh
        │   ├── instalar_mosquitto.sh
        │   ├── mqtt_bridge.py
        │   └── README_MOSQUITTO.md
        │
        ├── interfaz/
        │   ├── vista_pantalla.py
        │   ├── modelo_pantalla.py
        │   └── controlador_pantalla.py
        │
        └── IA/
            └── Modelo-Feb2026/
                └── Detector cancer.py
```

---

## Hardware utilizado

| Componente                 | Función                                               |
| -------------------------- | ----------------------------------------------------- |
| ESP32                      | Control principal de sensores y actuadores            |
| Raspberry Pi               | Broker MQTT, interfaz gráfica y procesamiento externo |
| Sensor PIR                 | Detección de movimiento/presencia                     |
| Sensor ultrasónico         | Medición de distancia aproximada                      |
| Joystick                   | Control manual de la base                             |
| Servomotor base            | Movimiento izquierda/derecha                          |
| Servomotor brazo           | Movimiento vertical preparado                         |
| LEDs rojo, amarillo y azul | Indicadores visuales de estado                        |
| Buzzer                     | Indicador sonoro de alertas                           |
| Cámara                     | Captura de imagen para análisis                       |
| Fuente externa 5V          | Alimentación de servomotores                          |

---

## Conexiones principales del ESP32

### Sensores

| Dispositivo       | Pin ESP32 |
| ----------------- | --------- |
| PIR               | GPIO33    |
| Ultrasónico TRIG  | GPIO25    |
| Ultrasónico ECHO  | GPIO26    |
| Joystick base VRx | GPIO35    |

> Importante: si se usa un HC-SR04 común, el pin ECHO puede entregar 5V. Se recomienda usar divisor de voltaje antes de conectarlo al ESP32.

### Actuadores

| Dispositivo  | Pin ESP32 |
| ------------ | --------- |
| LED rojo     | GPIO18    |
| LED amarillo | GPIO19    |
| LED azul     | GPIO21    |
| Buzzer       | GPIO27    |
| Servo base   | GPIO14    |
| Servo brazo  | GPIO23    |

### Alimentación recomendada

```text
Servo rojo       → +5V fuente externa
Servo café/negro → GND fuente externa
GND fuente       → GND ESP32

Joystick VCC     → 3V3 ESP32
Joystick GND     → GND ESP32
Joystick VRx     → GPIO35
```

No se recomienda alimentar servomotores directamente desde el pin 3V3 del ESP32.

---

## Principio de arquitectura HAL

El proyecto utiliza una capa HAL en:

```text
sistema/esp32/hardware/dispositivos.py
```

La HAL centraliza el acceso al hardware mediante:

```python
CajaSensores
CajaActuadores
```

El código principal del ESP32 no debe usar directamente:

```python
machine.Pin
machine.PWM
machine.ADC
```

La lectura de sensores y el control de actuadores debe realizarse mediante métodos de la HAL, por ejemplo:

```python
sensores.obtener_resumen()
actuadores.mover_base(90)
actuadores.estado_seguro()
```

---

## Máquina de estados del ESP32

El archivo principal de control está en:

```text
sistema/esp32/nucleo/maquina_estado.py
```

Estados principales:

| Estado            | Descripción                               |
| ----------------- | ----------------------------------------- |
| `ESTADO_BOOT`     | Inicializa WiFi, MQTT y hardware          |
| `ESTADO_ESPERA`   | Publica sensores y espera comandos        |
| `ESTADO_OPERANDO` | Lee joystick, mueve servo y publica datos |
| `ESTADO_ERROR`    | Activa estado seguro y reporta error      |

---

## Broker Mosquitto en Raspberry Pi

La Raspberry Pi se usa como broker MQTT local.

Datos de conexión:

| Parámetro   | Valor        |
| ----------- | ------------ |
| Red WiFi    | RaspberryLAN |
| IP broker   | 192.168.4.1  |
| Puerto MQTT | 1884         |
| Usuario     | admin        |
| Contraseña  | 123          |

Para instalar y configurar Mosquitto:

```bash
cd sistema/raspberry/comunicacion
chmod +x instalar_mosquitto.sh
./instalar_mosquitto.sh
```

Para verificar Mosquitto:

```bash
sudo systemctl status mosquitto
```

Para escuchar todos los mensajes:

```bash
mosquitto_sub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/#" -v
```

---

## Matriz de tópicos MQTT

### Publicación: ESP32 → Mosquitto → Raspberry

| Tópico                            | Payload                          | Descripción                         |
| --------------------------------- | -------------------------------- | ----------------------------------- |
| `sistema/estado`                  | texto                            | Estado general del sistema          |
| `sistema/error`                   | texto                            | Mensaje de error                    |
| `sistema/sensores/pir`            | `true` / `false`                 | Movimiento o presencia detectada    |
| `sistema/sensores/ultrasonico`    | número / `null`                  | Distancia aproximada en cm          |
| `sistema/sensores/joystick_base`  | `0` a `4095`                     | Lectura analógica del joystick      |
| `sistema/sensores/direccion_base` | `DERECHA`, `IZQUIERDA`, `CENTRO` | Dirección interpretada del joystick |
| `sistema/actuadores/base/grados`  | `0` a `180`                      | Ángulo real de la base              |
| `sistema/actuadores/brazo/grados` | `0` a `180`                      | Ángulo del brazo, si se usa         |
| `sistema/ia/resultado`            | JSON                             | Resultado del análisis de IA        |
| `sistema/alertas/ultima`          | texto                            | Última alerta del sistema           |

### Suscripción: Raspberry → Mosquitto → ESP32

| Tópico                            | Payload                  | Acción esperada                    |
| --------------------------------- | ------------------------ | ---------------------------------- |
| `sistema/cmd/iniciar`             | `on`                     | Entra en estado OPERANDO           |
| `sistema/cmd/iniciar`             | `off`                    | Vuelve a estado ESPERA             |
| `sistema/cmd/base/mover`          | `90` o `{"angulo": 90}`  | Mueve la base al ángulo indicado   |
| `sistema/cmd/brazo/mover`         | `90` o `{"angulo": 90}`  | Mueve el brazo al ángulo indicado  |
| `sistema/cmd/servo/iniciar`       | `0` a `180`              | Tópico compatible para mover servo |
| `sistema/cmd/led/azul/estado`     | `on`, `off`, `blink`     | Controla LED azul                  |
| `sistema/cmd/led/amarillo/estado` | `on`, `off`, `blink`     | Controla LED amarillo              |
| `sistema/cmd/led/rojo/estado`     | `on`, `off`, `blink`     | Controla LED rojo                  |
| `sistema/cmd/led/parpadear`       | JSON                     | Parpadea LED indicado              |
| `sistema/cmd/buzzer/senal`        | `lista`, `quieta`, `fin` | Activa señal sonora                |
| `sistema/cmd/seguro`              | cualquier texto          | Activa estado seguro               |

---

## Ejemplos de prueba MQTT

Escuchar todos los mensajes:

```bash
mosquitto_sub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/#" -v
```

Iniciar operación:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/iniciar" -m "on"
```

Volver a espera:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/iniciar" -m "off"
```

Mover base a 120 grados:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/base/mover" -m "120"
```

Mover base con JSON:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/base/mover" -m '{"angulo": 90}'
```

Activar buzzer:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/buzzer/senal" -m "lista"
```

Activar estado seguro:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/seguro" -m "on"
```

---

## Interfaz gráfica en Raspberry

La interfaz se encuentra en:

```text
sistema/raspberry/interfaz/vista_pantalla.py
```

El archivo encargado de unir interfaz y MQTT es:

```text
sistema/raspberry/main_interfaz_mqtt.py
```

Ejecutar interfaz conectada a MQTT:

```bash
cd sistema/raspberry
python3 main_interfaz_mqtt.py
```

La interfaz permite:

* Mostrar distancia del usuario.
* Mostrar movimiento detectado.
* Mostrar ángulo actual de la base/cámara.
* Mostrar estado del sistema.
* Enviar comando ON al ESP32.
* Enviar comando OFF al ESP32.
* Enviar comando de estado seguro.
* Solicitar movimiento de base mediante flechas.

---

## Flujo de funcionamiento esperado

1. La Raspberry crea la red local `RaspberryLAN`.
2. Mosquitto queda activo en `192.168.4.1:1884`.
3. La ESP32 se conecta a la red de la Raspberry.
4. La ESP32 se conecta al broker MQTT.
5. La ESP32 inicializa sensores y actuadores mediante la HAL.
6. La ESP32 publica estado, distancia, PIR, joystick y grados.
7. `mqtt_bridge.py` recibe los datos en Raspberry.
8. `vista_pantalla.py` actualiza la interfaz.
9. El usuario presiona ON en la interfaz.
10. La interfaz publica `sistema/cmd/iniciar = on`.
11. La ESP32 entra en estado OPERANDO.
12. El joystick puede mover la base.
13. Las flechas de la interfaz pueden solicitar un ángulo.
14. La ESP32 mueve el servo y publica el ángulo real.
15. La interfaz muestra el ángulo real recibido.

---

## Inteligencia artificial

El proyecto cuenta con un modelo de detección basado en YOLO dentro de la carpeta de IA. Actualmente se encuentra en proceso de integración con el flujo MQTT.

La integración esperada es:

```text
Cámara / captura
      ↓
Python IA en Raspberry
      ↓
Resultado del modelo
      ↓
MQTT: sistema/ia/resultado
      ↓
Interfaz / Firebase / actuadores
```

El modelo no debe ejecutarse en la ESP32. La IA debe correr en Raspberry, PC o servidor externo.

---

## Firebase

Firebase está contemplado para registrar eventos e histórico del sistema.

Estructura esperada:

```text
canma/
  estado_actual/
    distancia_cm
    movimiento_usuario
    grados_camara
    estado_sistema
    ultimo_resultado_ia
    timestamp

  eventos/
    evento_id/
      tipo
      valor
      timestamp

  alertas/
    alerta_id/
      tipo
      mensaje
      timestamp
```

Eventos mínimos esperados:

* Lectura de distancia.
* Movimiento/presencia.
* Cambio de ángulo de base.
* Resultado de IA.
* Estado del sistema.
* Alertas.

> No deben almacenarse imágenes identificables en Firebase sin anonimización.

---

## Pruebas recomendadas

### 1. Probar HAL del ESP32

Verificar que el ESP32 lea:

* PIR.
* Ultrasónico.
* Joystick.
* Posición de base.

También verificar que controle:

* Servo base.
* LEDs.
* Buzzer.

### 2. Probar Mosquitto

```bash
mosquitto_sub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/#" -v
```

### 3. Probar publicación de ESP32

Confirmar que aparezcan mensajes como:

```text
sistema/estado Iniciando
sistema/sensores/pir false
sistema/sensores/ultrasonico 25.4
sistema/sensores/joystick_base 2100
sistema/sensores/direccion_base CENTRO
sistema/actuadores/base/grados 90
```

### 4. Probar comandos hacia ESP32

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/iniciar" -m "on"
```

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/base/mover" -m "120"
```

### 5. Probar interfaz

Ejecutar:

```bash
cd sistema/raspberry
python3 main_interfaz_mqtt.py
```

Confirmar:

* Botón ON cambia el sistema a operación.
* Botón OFF vuelve a espera.
* Flechas publican ángulo de base.
* Distancia, movimiento y grados se actualizan con datos reales.

---

## Dependencias principales

### Raspberry Pi

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients -y
sudo apt install python3-paho-mqtt -y
sudo apt install python3-opencv -y
sudo apt install python3-pil python3-pil.imagetk -y
```

Opcional con pip:

```bash
python3 -m pip install paho-mqtt
```

### ESP32

* MicroPython.
* `umqtt.simple`.
* Archivos del proyecto copiados a la memoria del ESP32.

---

## Consideraciones físicas del prototipo

Para la entrega física se recomienda:

* Evitar protoboard expuesta.
* Evitar cables sueltos visibles.
* Usar fuente externa fija para servomotores.
* Colocar sensores en una estructura o carcasa.
* Etiquetar el prototipo con nombre del proyecto e integrantes.
* Probar el flujo completo antes del video demostrativo.

---

## Consideraciones éticas y médicas

CANMA es un prototipo educativo y experimental. El sistema puede apoyar en el análisis visual, pero no representa un diagnóstico médico.

Cualquier resultado generado por la IA debe ser revisado por personal médico capacitado y complementarse con estudios clínicos autorizados.

---

## Licencia

Este proyecto fue desarrollado con fines educativos para la materia de Sistemas Programables.

El uso, modificación o distribución del código deberá respetar los lineamientos de los integrantes del equipo y de la institución académica correspondiente.
