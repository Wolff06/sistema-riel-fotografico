# E4 Firebase + Interfaz Grafica - CANMA

## Decision de implementacion

Para E4 se recomienda usar **Cloud Firestore** mediante `firebase-admin` en Python.

La razon es que el proyecto ya funciona con MQTT entre Raspberry y ESP32. Para no romper esa logica, se agrega un puente independiente:

```text
ESP32 / IA / Interfaz -> MQTT -> firebase_gateway.py -> Firestore
Dashboard Firebase -> Firestore para monitoreo
Dashboard Firebase -> MQTT -> ESP32 para controlar actuadores
```

El sistema normal sigue funcionando aunque Firebase no este activo.

---

## Privacidad

No se guardan imagenes ni video en Firebase.

Solo se guardan metadatos:

- Resultado IA: `herido`, `ileso`, `sin_lectura`.
- Clase detectada por el modelo.
- Confianza de la prediccion.
- Timestamp.
- Ultimas lecturas de sensores.
- Estado del sistema.
- Comandos enviados a actuadores.

Esto cumple el requisito de privacidad:

> Sin imagenes identificables almacenadas en Firebase sin anonimizacion.

---

## Estructura recomendada en Firestore

### 1. Documento de estado actual

```text
estado_actual/sistema
```

Campos principales:

```json
{
  "sistema": "operando",
  "sensores": {
    "pir": true,
    "ultrasonico_cm": 18.0,
    "joystick_base": 2100,
    "direccion_base": "CENTRO"
  },
  "actuadores": {
    "base_grados": 90,
    "brazo_grados": 90
  },
  "ia": {
    "estado_ia": "activa",
    "lectura": "herido",
    "clase": "seno_herido",
    "confianza": 0.87,
    "alerta": true,
    "timestamp": "2026-06-12T11:45:00"
  },
  "alerta_ultima": "IA: posible hallazgo visual detectado",
  "timestamp_local": "2026-06-12T11:45:00"
}
```

Este documento se sobrescribe con intervalo controlado para evitar gastar escrituras.

---

### 2. Coleccion de eventos historicos

```text
eventos/{id_auto}
```

Tipos de evento usados:

| Tipo | Descripcion |
|---|---|
| `ia_resultado` | Guarda resultado IA historico, limitado por tiempo. |
| `snapshot_sensores` | Guarda una muestra de sensores, actuadores e IA. |
| `comando_actuador` | Guarda comandos enviados a actuadores. |
| `alerta_ia` | Guarda alerta cuando la IA detecta posible seno herido. |
| `error_sistema` | Guarda errores publicados por ESP32. |

Con esto se cumple:

> Minimo 3 tipos de eventos distintos registrados con timestamp.

---

### 3. Coleccion de alertas

```text
alertas/{id_auto}
```

El dashboard lee las ultimas 5 alertas ordenadas por timestamp.

---

## Archivos agregados

### `firebase_gateway.py`

Escucha MQTT y escribe en Firestore.

Ejecutar:

```bash
cd sistema/raspberry/firebase
python3 firebase_gateway.py
```

### `dashboard_firebase_mqtt.py`

Dashboard tipo app que lee Firestore y controla actuadores por MQTT.

Ejecutar:

```bash
cd sistema/raspberry/firebase
python3 dashboard_firebase_mqtt.py
```

### `requirements_firebase.txt`

Dependencias necesarias:

```bash
python3 -m pip install -r requirements_firebase.txt
```

---

## Credenciales Firebase

Descargar desde Firebase Console / Google Cloud una llave de cuenta de servicio para Admin SDK.

Guardar como:

```text
sistema/raspberry/firebase/credenciales/firebase_key.json
```

O usar variable de entorno:

```bash
export CANMA_FIREBASE_CRED="/ruta/segura/firebase_key.json"
```

No compartir este archivo.

---

## Variables opcionales para cuidar creditos

### Intervalo de escritura del estado actual

Por defecto:

```bash
CANMA_FIREBASE_INTERVALO_ESTADO=30
```

Ejemplo para demo mas rapida:

```bash
export CANMA_FIREBASE_INTERVALO_ESTADO=10
```

### Intervalo historico de IA

Por defecto, guarda deteccion IA historica maximo una vez por hora:

```bash
CANMA_FIREBASE_INTERVALO_IA=3600
```

---

## Comprobacion E4 paso a paso

### 1. Instalar dependencias

```bash
cd sistema/raspberry/firebase
python3 -m pip install -r requirements_firebase.txt
```

### 2. Colocar credencial

```text
sistema/raspberry/firebase/credenciales/firebase_key.json
```

### 3. Ejecutar Mosquitto y el sistema normal

Ejecutar el ESP32 con `main.py` y la interfaz normal de Raspberry.

### 4. Ejecutar Gateway Firebase

```bash
cd sistema/raspberry/firebase
python3 firebase_gateway.py
```

Debe mostrar mensajes como:

```text
Gateway Firebase conectado a Mosquitto
MQTT -> Firebase: sistema/ia/resultado {...}
Firebase estado_actual/sistema actualizado
Firebase evento registrado: ia_resultado
```

### 5. Ejecutar dashboard

```bash
cd sistema/raspberry/firebase
python3 dashboard_firebase_mqtt.py
```

El dashboard debe mostrar:

- Estado actual del sistema.
- Ultima lectura del PIR.
- Ultima lectura del ultrasonico.
- Ultimo valor del joystick.
- Ultima lectura de IA.
- Ultimas 5 alertas.
- Botones para mover base, mover brazo, activar/apagar IA y estado seguro.

### 6. Probar control remoto

Desde el dashboard mover la base a 120 grados.

Debe ocurrir:

```text
Dashboard -> MQTT -> ESP32 -> HAL -> Servo base
```

Y el gateway debe registrar un evento `comando_actuador`.

---

## Checklist E4

| Requisito | Como se cumple |
|---|---|
| Firebase recibe datos reales en tiempo real | `firebase_gateway.py` escucha MQTT y actualiza `estado_actual/sistema`. |
| Minimo 3 tipos de eventos con timestamp | `ia_resultado`, `snapshot_sensores`, `comando_actuador`, `alerta_ia`, `error_sistema`. |
| Dashboard con estado actual, lecturas y alertas | `dashboard_firebase_mqtt.py` lee `estado_actual/sistema` y ultimas 5 alertas. |
| Control remoto de al menos 1 actuador | Dashboard publica `sistema/cmd/base/mover` y `sistema/cmd/seguro`. |
| Privacidad de imagenes garantizada | No se suben imagenes ni video, solo metadatos. |

---

## Recomendacion para la exposicion

Explicar que se eligio guardar metadatos y no imagenes por privacidad y por ahorro de recursos. La IA se ejecuta localmente en Raspberry; Firebase solo recibe el resultado procesado.

Ejemplo de explicacion:

> El sistema no sube fotografias de los usuarios a Firebase. La Raspberry procesa la imagen localmente con YOLO y solo envia a Firestore el resultado de la deteccion: herido, ileso o sin lectura, junto con la confianza y la hora. Esto reduce consumo de lecturas/escrituras y protege la privacidad.
