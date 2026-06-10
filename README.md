# Garra Robótica con Cámara e IA para Apoyo en la Detección de Cáncer de Mama

## Descripción del proyecto

Este proyecto consiste en el desarrollo de una **garra robótica controlada por ESP32**, equipada con una **cámara** y un sistema de **inteligencia artificial** orientado al análisis de imágenes para apoyar en la detección temprana de posibles indicios relacionados con cáncer de mama.

El sistema integra hardware físico, control de servomotores, comunicación mediante MQTT y procesamiento de imágenes en un servidor Python. La ESP32 se encarga del control de movimiento de la garra, mientras que el servidor procesa la información recibida, administra la comunicación y ejecuta los módulos relacionados con IA.

> **Nota importante:** Este prototipo es de carácter académico y experimental. No sustituye el diagnóstico médico profesional ni debe utilizarse como herramienta clínica definitiva.

---

## Integrantes

* Macias Campos Ariadne Lizett
* Soto Garnica Ari Adair
* Lira Gamiño Luis Fernando

---

## Objetivo general

Diseñar e implementar un prototipo funcional de garra robótica con cámara, capaz de realizar movimientos controlados para posicionar el sistema de captura de imagen y enviar información a un servidor mediante MQTT, donde se integra un módulo de inteligencia artificial para el análisis de imágenes relacionadas con la detección de cáncer de mama.

---

## Características principales

* Control de movimiento mediante ESP32.
* Movimiento de base de izquierda a derecha.
* Movimiento vertical de la cámara mediante servomotores.
* Captura de imágenes mediante cámara.
* Comunicación MQTT entre ESP32, broker y servidor Python.
* Arquitectura basada en HAL para separar la lógica del hardware.
* Integración con módulo de inteligencia artificial.
* Posibilidad de enviar estados, comandos y alertas del sistema.
* Uso de LED y buzzer como indicadores físicos del estado del prototipo.

---

## Arquitectura del sistema

```text
┌─────────────────────────────────────────────────────────────────┐
│                 ECOSISTEMA GENERAL DEL SISTEMA                  │
│                                                                 │
│  ┌────────────────┐      MQTT/TCP       ┌────────────────────┐  │
│  │     ESP32      │ ◄────────────────► │ Broker Mosquitto   │  │
│  │ mqtt_esp32.py  │                    │ Raspberry Pi / PC  │  │
│  └───────┬────────┘                    └─────────┬──────────┘  │
│          │                                       │              │
│          │                                       │              │
│  ┌───────▼────────┐                    ┌─────────▼──────────┐  │
│  │  HAL Hardware  │                    │ servidor_python.py │  │
│  │ dispositivos.py│                    │ IA + Control MQTT  │  │
│  └───────┬────────┘                    └─────────┬──────────┘  │
│          │                                       │              │
│  ┌───────▼────────────────────┐          ┌───────▼──────────┐  │
│  │ Hardware físico             │          │ Cámara / IA       │  │
│  │ Servos · Joysticks · LED    │          │ Captura y análisis│  │
│  │ Buzzer · Sensores           │          │ de imagen         │  │
│  └─────────────────────────────┘          └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Principio de encapsulamiento HAL

El proyecto utiliza una arquitectura tipo **HAL** (*Hardware Abstraction Layer*) para separar la lógica principal del acceso directo al hardware.

Esto significa que el módulo `mqtt_esp32.py` no debe acceder directamente a instrucciones como:

```python
machine.Pin
machine.PWM
ADC
```

En su lugar, toda la interacción con el hardware debe realizarse a través de clases como:

```python
CajaSensores
CajaActuadores
```

Esta separación permite que el código sea más ordenado, fácil de mantener y más sencillo de adaptar si se cambian sensores, actuadores o pines físicos.

---

## Flujo general de funcionamiento

1. La ESP32 inicia el sistema y se conecta a la red WiFi.
2. La ESP32 establece conexión con el broker MQTT.
3. Los joysticks o comandos MQTT controlan los servomotores de la garra.
4. La cámara captura imágenes desde la posición indicada.
5. El servidor Python recibe datos del sistema y procesa las imágenes.
6. El módulo de IA analiza la imagen y genera un resultado preliminar.
7. El sistema puede activar indicadores físicos como LED o buzzer.
8. Los estados del prototipo se publican mediante tópicos MQTT.

---

## Hardware utilizado

| Componente                   | Función dentro del sistema              |
| ---------------------------- | --------------------------------------- |
| ESP32                        | Control principal del prototipo         |
| Servomotor de base           | Movimiento izquierda/derecha            |
| Servomotor de hombro         | Movimiento arriba/abajo de la cámara    |
| Joystick 1                   | Control manual de la base               |
| Joystick 2                   | Control manual del movimiento vertical  |
| Cámara                       | Captura de imágenes para análisis       |
| Fuente externa de 5V         | Alimentación de servomotores            |
| LED                          | Indicador visual del estado del sistema |
| Buzzer                       | Indicador sonoro                        |
| Cables Dupont                | Conexión entre módulos                  |
| Estructura de garra robótica | Soporte mecánico del sistema            |

---

## Software utilizado

| Componente             | Tecnología                     |
| ---------------------- | ------------------------------ |
| Control de ESP32       | MicroPython                    |
| Comunicación           | MQTT                           |
| Broker                 | Mosquitto                      |
| Servidor               | Python                         |
| Cliente MQTT en Python | paho-mqtt                      |
| IA                     | Modelo de análisis de imágenes |
| Control de hardware    | HAL en MicroPython             |

---

## Matriz de tópicos MQTT

### Publicación: ESP32 → Broker → Servidor Python

| # | Tópico                  | Tipo de dato | Valores posibles                                        | Descripción                              |
| - | ----------------------- | ------------ | ------------------------------------------------------- | ---------------------------------------- |
| 1 | `garra/sistema/estado`  | string       | `IDLE`, `MOVIENDO`, `CAPTURANDO`, `ANALIZANDO`, `ERROR` | Estado general del sistema               |
| 2 | `garra/base/posicion`   | float/string | `0` a `180`                                             | Posición angular de la base              |
| 3 | `garra/hombro/posicion` | float/string | `0` a `180`                                             | Posición angular del hombro              |
| 4 | `garra/joystick/base`   | int/string   | `0` a `4095`                                            | Lectura analógica del joystick de base   |
| 5 | `garra/joystick/hombro` | int/string   | `0` a `4095`                                            | Lectura analógica del joystick de hombro |
| 6 | `garra/camara/estado`   | string       | `lista`, `capturando`, `error`                          | Estado de la cámara                      |
| 7 | `garra/ia/resultado`    | JSON/string  | Resultado del modelo                                    | Resultado preliminar del análisis de IA  |
| 8 | `garra/sistema/error`   | string       | Descripción libre                                       | Mensajes de error del sistema            |

---

### Suscripción: Servidor Python → Broker → ESP32

| # | Tópico                      | Payload                  | Acción esperada                                          |
| - | --------------------------- | ------------------------ | -------------------------------------------------------- |
| 1 | `garra/cmd/base/mover`      | `{"angulo": 90}`         | Mover la base a un ángulo específico                     |
| 2 | `garra/cmd/hombro/mover`    | `{"angulo": 120}`        | Mover el hombro a un ángulo específico                   |
| 3 | `garra/cmd/camara/capturar` | Cualquier texto          | Solicitar captura de imagen                              |
| 4 | `garra/cmd/led/estado`      | `on`, `off`, `blink`     | Controlar LED indicador                                  |
| 5 | `garra/cmd/buzzer/senal`    | `inicio`, `fin`, `error` | Activar señal sonora                                     |
| 6 | `garra/cmd/seguro`          | `STOP`                   | Detener actuadores y colocar el sistema en estado seguro |

---

## Instalación y puesta en marcha

### 1. Instalar broker Mosquitto

En Ubuntu, Debian o Raspberry Pi OS:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients -y
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

Verificar que Mosquitto esté activo:

```bash
sudo systemctl status mosquitto
```

Verificar puerto MQTT:

```bash
sudo netstat -tlnp | grep 1883
```

---

### 2. Instalar dependencias del servidor Python

```bash
pip install paho-mqtt
```

Ejecutar el servidor:

```bash
python servidor_python.py
```

---

### 3. Preparar la ESP32 con MicroPython

Flashear MicroPython en la ESP32. Se recomienda utilizar una versión igual o superior a MicroPython 1.20.

Copiar los archivos principales a la ESP32:

```bash
mpremote cp dispositivos.py :dispositivos.py
mpremote cp mqtt_esp32.py :mqtt_esp32.py
```

Editar en `mqtt_esp32.py` los datos de conexión:

```python
WIFI_SSID = "NOMBRE_DE_TU_RED"
WIFI_PASSWORD = "CONTRASEÑA"
BROKER_HOST = "IP_DEL_BROKER"
```

Ejecutar el archivo:

```bash
mpremote run mqtt_esp32.py
```

O copiarlo como `main.py` para que inicie automáticamente:

```bash
mpremote cp mqtt_esp32.py :main.py
```

---

## Conexión básica de servomotores

Los servomotores deben alimentarse con una fuente externa de 5V. No se recomienda alimentar los servos directamente desde la ESP32.

```text
Fuente 5V +  → cable rojo de los servos
Fuente 5V -  → cable café/negro de los servos
GND fuente   → GND ESP32

Señal servo base   → GPIO25 ESP32
Señal servo hombro → GPIO26 ESP32
```

Los joysticks pueden alimentarse desde la ESP32:

```text
Joystick +5V/VCC → 3V3 ESP32
Joystick GND     → GND ESP32
Joystick VRx     → GPIO34
Joystick VRy     → GPIO33
```

---

## Verificación con cliente MQTT

Escuchar todos los mensajes del sistema:

```bash
mosquitto_sub -h localhost -t "garra/#" -v
```

Enviar comando para mover la base:

```bash
mosquitto_pub -h localhost -t "garra/cmd/base/mover" -m '{"angulo": 90}'
```

Enviar comando para mover el hombro:

```bash
mosquitto_pub -h localhost -t "garra/cmd/hombro/mover" -m '{"angulo": 120}'
```

Activar LED:

```bash
mosquitto_pub -h localhost -t "garra/cmd/led/estado" -m "blink"
```

Activar estado seguro:

```bash
mosquitto_pub -h localhost -t "garra/cmd/seguro" -m "STOP"
```

---

## Estructura sugerida del repositorio

```text
.
├── esp32/
│   ├── mqtt_esp32.py
│   ├── dispositivos.py
│   └── control_servos.py
│
├── servidor/
│   ├── servidor_python.py
│   ├── ia_modelo.py
│   └── captura_camara.py
│
├── docs/
│   ├── arquitectura.md
│   ├── topicos_mqtt.md
│   └── conexiones.md
│
├── imagenes/
│   ├── prototipo.jpg
│   └── diagrama_sistema.png
│
├── README.md
└── requirements.txt
```

---

## Dependencias y versiones

| Componente       | Entorno           | Librería               | Versión mínima                 |
| ---------------- | ----------------- | ---------------------- | ------------------------------ |
| ESP32            | MicroPython       | `umqtt.simple`         | Incluida en MicroPython ≥ 1.20 |
| Servidor Python  | CPython           | `paho-mqtt`            | ≥ 1.6.1                        |
| Broker MQTT      | Sistema operativo | Mosquitto              | ≥ 2.0                          |
| Procesamiento IA | Python            | Según modelo utilizado | Variable                       |

---

## Estado actual del prototipo

Actualmente el prototipo permite controlar el movimiento de la base mediante servomotor y joystick. La estructura mecánica de la garra está ensamblada y se trabaja en la integración del movimiento vertical de la cámara, así como en la conexión entre la cámara, el servidor Python y el módulo de IA.

---

## Mejoras futuras

* Integrar control completo de hombro y base.
* Añadir límites de seguridad para evitar forzar los servomotores.
* Implementar captura automática desde la cámara.
* Mejorar el modelo de IA para análisis de imágenes.
* Guardar resultados en una base de datos.
* Integrar una interfaz gráfica para visualizar imágenes y resultados.
* Agregar registro histórico de capturas y análisis.
* Mejorar la estructura mecánica para reducir vibraciones.

---

## Consideraciones éticas y médicas

Este proyecto tiene fines académicos, tecnológicos y de investigación. El sistema de IA puede apoyar en la identificación de patrones visuales, pero no debe considerarse un diagnóstico médico.

Cualquier resultado generado por el sistema debe ser revisado por personal médico capacitado y complementarse con estudios clínicos autorizados.

---

## Licencia

Este proyecto fue desarrollado con fines educativos.
El uso, modificación o distribución del código deberá respetar los lineamientos establecidos por los integrantes del equipo y la institución académica correspondiente.
