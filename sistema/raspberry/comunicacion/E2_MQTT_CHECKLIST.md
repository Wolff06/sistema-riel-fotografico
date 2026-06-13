# Entrega E2 - Integracion MQTT del proyecto CANMA

## Objetivo

Demostrar que la ESP32 y la Raspberry se comunican mediante MQTT sin romper la HAL. La ESP32 publica datos reales de sensores y recibe comandos desde Python para activar actuadores.

Esta evidencia no modifica la logica principal del proyecto. La interfaz sigue ejecutandose desde:

```bash
python3 sistema/raspberry/main_interfaz_mqtt.py
```

El programa principal del ESP32 sigue siendo:

```python
sistema/esp32/main.py
```

---

## Datos de conexion

| Elemento | Valor |
|---|---|
| Broker | Mosquitto en Raspberry Pi |
| Host | `192.168.4.1` |
| Puerto | `1884` |
| Usuario | `admin` |
| Clave | `123` |
| Red WiFi esperada | `RaspberryLAN` |

---

## Tabla oficial de topicos

### Publicacion: ESP32 -> Mosquitto -> Raspberry/Python

| Topico | Mensaje esperado | Funcion dentro del proyecto |
|---|---|---|
| `sistema/sensores/pir` | `true` / `false` | Publica presencia o movimiento detectado por PIR |
| `sistema/sensores/ultrasonico` | numero en cm / `null` | Publica distancia medida por el sensor ultrasonico |
| `sistema/sensores/joystick_base` | numero de `0` a `4095` | Publica lectura analogica filtrada del joystick |
| `sistema/sensores/direccion_base` | `DERECHA`, `IZQUIERDA` o `CENTRO` | Publica direccion interpretada del joystick |
| `sistema/actuadores/base/grados` | numero de `0` a `180` | Publica la posicion actual del servo de base |
| `sistema/actuadores/brazo/grados` | numero de `0` a `180` | Publica la posicion actual del servo de brazo |
| `sistema/estado` | texto | Publica estado general del sistema |
| `sistema/error` | texto | Publica errores detectados |
| `sistema/alertas/ultima` | texto | Publica ultima alerta visible para la interfaz |

### Suscripcion: Raspberry/Python -> Mosquitto -> ESP32

| Topico | Mensaje de prueba | Actuador o proceso esperado |
|---|---|---|
| `sistema/cmd/iniciar` | `on` / `off` | Activa o detiene modo sensores |
| `sistema/cmd/modo` | `sensores`, `ia` o `reposo` | Cambia el modo general del sistema |
| `sistema/cmd/base/mover` | `90` o `{"angulo": 90}` | Mueve fisicamente el servo de base |
| `sistema/cmd/brazo/mover` | `90` o `{"angulo": 90}` | Mueve fisicamente el servo de brazo |
| `sistema/cmd/servo/iniciar` | numero de `0` a `180` | Compatibilidad para mover servo de base |
| `sistema/cmd/led/azul/estado` | `on`, `off`, `blink` | Control manual del LED azul cuando el sistema esta en reposo |
| `sistema/cmd/led/amarillo/estado` | `on`, `off`, `blink` | Control manual del LED amarillo cuando el sistema esta en reposo |
| `sistema/cmd/led/rojo/estado` | `on`, `off`, `blink` | Control manual del LED rojo cuando el sistema esta en reposo |
| `sistema/cmd/buzzer/senal` | `lista`, `quieta`, `fin` | Activa senales sonoras cuando el sistema esta en reposo |
| `sistema/cmd/seguro` | `on` | Ejecuta estado seguro en la HAL |

---

## Como verificar Mosquitto activo

Desde la Raspberry:

```bash
sudo systemctl status mosquitto
```

Tambien se puede verificar escuchando todos los topicos:

```bash
mosquitto_sub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/#" -v
```

Salida esperada cuando la ESP32 esta encendida y conectada:

```text
sistema/estado Esperando instrucciones
sistema/sensores/pir false
sistema/sensores/ultrasonico 18.45
sistema/sensores/joystick_base 2048
sistema/sensores/direccion_base CENTRO
sistema/actuadores/base/grados 90
```

---

## Verificacion con script Python

El archivo `verificar_e2_mqtt.py` demuestra que Python recibe datos con timestamp.

Ejecutar solo escucha:

```bash
cd sistema/raspberry/comunicacion
python3 verificar_e2_mqtt.py
```

Salida esperada:

```text
[2026-06-12 10:30:01] Broker Mosquitto conectado correctamente
[2026-06-12 10:30:02] sistema/sensores/pir = false
[2026-06-12 10:30:02] sistema/sensores/ultrasonico = 18.45
[2026-06-12 10:30:02] sistema/sensores/joystick_base = 2048
```

Para demostrar que Python publica un comando y el actuador responde, ejecutar:

```bash
cd sistema/raspberry/comunicacion
python3 verificar_e2_mqtt.py --enviar-comando --angulo 120
```

Respuesta esperada:

```text
[2026-06-12 10:31:05] Enviando comando de prueba: sistema/cmd/base/mover = 120
[2026-06-12 10:31:06] sistema/actuadores/base/grados = 120
```

El servo de la base debe moverse fisicamente al angulo indicado.

---

## Verificacion manual con mosquitto_pub

Mover base desde la Raspberry:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/base/mover" -m "120"
```

Regresar a estado seguro:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/seguro" -m "on"
```

---

## Encapsulamiento HAL

La integracion MQTT no controla pines directamente. El flujo correcto es:

```text
Raspberry/Python -> MQTT -> ESP32/nucleo/maquina_estado.py -> hardware/dispositivos.py -> actuador fisico
```

La maquina de estados usa la HAL mediante:

```python
self._sensores = hardware.CajaSensores()
self._actuadores = hardware.CajaActuadores()
```

Por lo tanto, MQTT no rompe el encapsulamiento porque los actuadores se activan mediante metodos de la HAL como:

```python
self._actuadores.mover_base(angulo)
self._actuadores.mover_brazo(angulo)
self._actuadores.estado_seguro()
```

---

## Checklist E2

| Punto solicitado | Estado en el proyecto |
|---|---|
| Tabla de topicos documentada y coherente | Cumplido en este archivo y en `sistema/esp32/comunicacion/comunicacion.py` |
| Broker Mosquitto activo y verificado | Verificable con `systemctl`, `mosquitto_sub` y `verificar_e2_mqtt.py` |
| ESP32 publica minimo 2 sensores en topicos distintos | Cumplido: PIR, ultrasonico, joystick y direccion |
| Python recibe datos con timestamp | Cumplido: `mqtt_bridge.py` y `verificar_e2_mqtt.py` imprimen hora del mensaje |
| Al menos 1 actuador responde a comando desde Python | Cumplido con `sistema/cmd/base/mover` hacia el servo de base |
| Encapsulamiento HAL no roto | Cumplido: la logica MQTT llama metodos de `CajaActuadores` y `CajaSensores` |
