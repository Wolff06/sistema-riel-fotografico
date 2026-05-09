# Documentación MQTT — Sistema de Riel Semicircular Fotográfico 180°

**PROYECTO:** Sistema de Riel Semicircular Fotográfico 180°  
**INTEGRANTES:**  
- Macias Campos Ariadne Lizett  
- Soto Garnica Ari Adair  
- Lira Gamiño Luis Fernando  

---

## 1. Arquitectura de Comunicación

```
┌─────────────────────────────────────────────────────────────────┐
│                   ECOSISTEMA MQTT DEL SISTEMA                   │
│                                                                 │
│  ┌───────────────┐     MQTT/TCP     ┌───────────────────────┐  │
│  │  ESP32        │ ◄──────────────► │  Broker Mosquitto     │  │
│  │  mqtt_esp32.py│                  │  (Raspberry Pi / PC)  │  │
│  └──────┬────────┘                  └──────────┬────────────┘  │
│         │                                       │               │
│   ┌─────▼──────┐                        ┌──────▼──────────┐    │
│   │  HAL       │                        │  servidor_      │    │
│   │  dispositiv│                        │  python.py      │    │
│   │  os.py     │                        └─────────────────┘    │
│   └─────┬──────┘                                               │
│         │                                                       │
│   ┌─────▼───────────────────────────────────────┐              │
│   │  Hardware Físico                             │              │
│   │  PIR · Limit switches · Motor · LED · Buzzer │              │
│   └──────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

**Principio de encapsulamiento HAL:** el módulo `mqtt_esp32.py` nunca
accede a `machine.Pin` ni `machine.PWM` directamente. Toda interacción
con hardware pasa exclusivamente por `CajaSensores` y `CajaActuadores`.

---

## 2. Matriz Completa de Tópicos MQTT

### 2.1 Publicación — ESP32 → Broker → Servidor Python

| # | Tópico | Tipo de dato | Valores posibles | Dispositivo HAL | Método HAL |
|---|--------|-------------|-----------------|-----------------|------------|
| 1 | `riel/sensores/pir` | string | `"1"` / `"0"` | Sensor PIR GPIO34 | `CajaSensores.obtener_presencia()` |
| 2 | `riel/sensores/limite_izq` | string | `"1"` / `"0"` | Limit switch izq. GPIO35 | `CajaSensores.obtener_limite_izquierdo()` |
| 3 | `riel/sensores/limite_der` | string | `"1"` / `"0"` | Limit switch der. GPIO32 | `CajaSensores.obtener_limite_derecho()` |
| 4 | `riel/actuadores/motor/posicion` | float string | `"0.0"` … `"180.0"` | Motor NEMA 17 | `CajaActuadores.obtener_posicion_grados()` |
| 5 | `riel/sistema/estado` | string | `IDLE` / `BARRIENDO` / `HOMING` / `ERROR` | Sistema | Estado interno |
| 6 | `riel/sistema/error` | string | Descripción libre | Sistema | Try/except callbacks |

### 2.2 Suscripción — Servidor Python → Broker → ESP32

| # | Tópico | Payload | Dispositivo HAL | Método HAL invocado |
|---|--------|---------|-----------------|---------------------|
| 7 | `riel/cmd/motor/mover` | JSON `{"angulo": float, "velocidad": int}` | Motor NEMA 17 | `CajaActuadores.mover_angulo(angulo, velocidad)` |
| 8 | `riel/cmd/motor/inicio` | Cualquier texto | Motor NEMA 17 | `CajaActuadores.ir_a_inicio()` |
| 9 | `riel/cmd/led/estado` | `"on"` / `"off"` / `"blink"` | LED GPIO2 | `encender_led()` / `apagar_led()` / `parpadear_led()` |
| 10 | `riel/cmd/led/parpadear` | JSON `{"veces": int, "intervalo_ms": int}` | LED GPIO2 | `CajaActuadores.parpadear_led(veces, intervalo_ms)` |
| 11 | `riel/cmd/buzzer/señal` | `"lista"` / `"quieta"` / `"fin"` | Buzzer GPIO4 | `señal_lista()` / `señal_quieta()` / `señal_fin_sesion()` |
| 12 | `riel/cmd/seguro` | Cualquier texto | Todos los actuadores | `CajaActuadores.estado_seguro()` |

**Total de dispositivos mapeados:** 5 (PIR, limit-izq, limit-der, motor NEMA 17, LED, buzzer = 6 dispositivos físicos, 12 tópicos)

---

## 3. Instalación y Puesta en Marcha

### 3.1 Broker Mosquitto (PC o Raspberry Pi)

```bash
# Ubuntu / Debian
sudo apt install mosquitto mosquitto-clients -y
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Verificar que escucha en puerto 1883
sudo netstat -tlnp | grep 1883
```

### 3.2 Servidor Python (PC)

```bash
pip install paho-mqtt
python servidor_python.py
```

### 3.3 ESP32 — MicroPython

1. Flashear MicroPython en la ESP32 (firmware ≥ 1.20).
2. Copiar `dispositivos.py` y `mqtt_esp32.py` al sistema de archivos de la ESP32:

```bash
# Con mpremote
mpremote cp dispositivos.py :dispositivos.py
mpremote cp mqtt_esp32.py   :mqtt_esp32.py
```

3. Editar `WIFI_SSID`, `WIFI_PASSWORD` y `BROKER_HOST` en `mqtt_esp32.py`.
4. Ejecutar:

```bash
mpremote run mqtt_esp32.py
# o copiar como main.py para autoarranque
mpremote cp mqtt_esp32.py :main.py
```

### 3.4 Verificación con cliente MQTT CLI

```bash
# Escuchar toda la telemetría del sistema
mosquitto_sub -h localhost -t "riel/#" -v

# Enviar comando manual de prueba
mosquitto_pub -h localhost -t "riel/cmd/led/estado" -m "blink"
mosquitto_pub -h localhost -t "riel/cmd/motor/mover" -m '{"angulo": 90, "velocidad": 600}'
mosquitto_pub -h localhost -t "riel/cmd/seguro" -m "STOP"
```

---

## 4. Dependencias y Versiones

| Componente | Entorno | Librería | Versión mínima |
|------------|---------|----------|----------------|
| ESP32 firmware | MicroPython | `umqtt.simple` | Incluida en MicroPython ≥ 1.20 |
| Servidor Python | CPython | `paho-mqtt` | ≥ 1.6.1 |
| Broker | Sistema operativo | Mosquitto | ≥ 2.0 |

---
