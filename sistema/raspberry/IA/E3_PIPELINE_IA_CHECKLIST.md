# E3 Pipeline de Inteligencia Artificial - CANMA

Este documento sirve como evidencia de la entrega E3 sin modificar la logica que ya funciona entre la Raspberry y el ESP32.

## Objetivo de E3

Integrar el modelo de IA en el servidor Python para que el flujo quede asi:

```text
Camara en Raspberry Pi / sensor -> Python IA -> MQTT -> ESP32 -> actuador fisico
```

En la version actual del proyecto CANMA, la IA corre en Raspberry Pi/Python con OpenCV y YOLO. El resultado se publica por MQTT en `sistema/ia/resultado` y el ESP32 lo recibe para activar LEDs y buzzer.

## Aclaracion de hardware de camara para esta entrega

Para esta revision, el equipo tiene autorizado usar **Raspberry Pi como modulo de camara y servidor Python**, conservando la misma validez que una ESP32-CAM dentro del pipeline de IA.

Por esa razon, en este proyecto la fuente visual funcional es:

```text
Camara conectada a Raspberry Pi -> OpenCV -> YOLO -> MQTT -> ESP32 -> actuadores
```

La Raspberry Pi no es decorativa: captura imagenes reales con OpenCV, ejecuta el modelo de IA y publica el resultado por MQTT para que el ESP32 active fisicamente LEDs y buzzer.

Para no romper el sistema que ya funciona, no se cambio la logica principal. Se conserva tambien el soporte opcional para una camara IP o ESP32-CAM por URL mediante la variable de entorno:

```bash
CANMA_CAMARA_FUENTE="http://IP_DE_LA_CAMARA:81/stream" python3 ia_processor_mqtt.py
```

Si no se define esa variable, el sistema sigue usando la camara local de la Raspberry con `CAMARA_ID = 0`.

---

## Librerias de IA utilizadas

El proyecto usa:

- `OpenCV` para capturar imagenes y manejar frames.
- `ultralytics` / `YOLO` para deteccion o clasificacion visual.
- `paho-mqtt` para comunicacion MQTT desde Python.

Instalacion sugerida en Raspberry:

```bash
python3 -m pip install ultralytics opencv-python paho-mqtt
```

---

## Modelo entrenado incluido

Rutas de modelos encontrados:

```text
sistema/raspberry/IA/Modelo-Feb2026/runs/cancer/train_v1/weights/best.pt
sistema/raspberry/IA/Modelo-Feb2026/runs/cancer_SinFalsosPositivos/weights/best.pt
```

Clases documentadas en `Datav3.yml`:

```text
Seno Herido
Seno Ileso
Falso Positivo
```

El sistema normaliza estas clases a:

```text
herido
ileso
falso
sin_lectura
```

---

## Resultados de entrenamiento disponibles

El proyecto incluye evidencias de entrenamiento dentro de:

```text
sistema/raspberry/IA/Modelo-Feb2026/runs/cancer/train_v1/
sistema/raspberry/IA/Modelo-Feb2026/runs/cancer_SinFalsosPositivos/
```

Metricas observadas en los CSV del entrenamiento:

| Modelo | Precision final aprox. | Recall final aprox. | mAP50 final aprox. | mAP50-95 final aprox. |
|---|---:|---:|---:|---:|
| `cancer/train_v1` | 1.000 | 0.618 | 0.995 | 0.642 |
| `cancer_SinFalsosPositivos` | 0.972 | 0.950 | 0.977 | 0.697 |

Para explicar en exposicion: el modelo detecta posibles regiones clasificadas como `Seno Herido`, `Seno Ileso` o `Falso Positivo`. La confianza se publica como numero decimal entre 0 y 1.

---

## Prueba 1: modelo con datos estaticos antes de MQTT

Ejecutar desde Raspberry:

```bash
cd sistema/raspberry/IA
python3 probar_modelo_estatico.py
```

El script toma imagenes de:

```text
sistema/raspberry/interfaz/Imagenes_capturas/
```

Genera evidencias en:

```text
sistema/raspberry/IA/evidencias_e3/prueba_modelo_estatico/
```

Archivos generados:

```text
resultados_prueba_estatica.csv
resumen_prueba_estatica.json
imagenes anotadas *_resultado.jpg
```

Esto cubre el checklist:

```text
Modelo probado con datos estaticos antes de conectar MQTT
```

---

## Prueba 2: IA en vivo con MQTT

Terminal 1: dejar corriendo el `main.py` del ESP32.

Terminal 2: ejecutar la interfaz o el procesador de IA.

Opcion A, interfaz completa:

```bash
cd sistema/raspberry
python3 main_interfaz_mqtt.py
```

Opcion B, procesador IA independiente:

```bash
cd sistema/raspberry/IA
python3 ia_processor_mqtt.py
```

Activar IA desde la interfaz o publicar manualmente:

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t sistema/cmd/modo -m ia
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t sistema/cmd/ia/estado -m on
```

Resultado esperado:

```text
Python publica sistema/ia/resultado
ESP32 recibe sistema/ia/resultado
ESP32 cambia LED y buzzer segun lectura
```

---

## Prueba 3: verificador extremo a extremo MQTT -> actuador

Ejecutar:

```bash
cd sistema/raspberry/IA
python3 verificar_e3_pipeline_mqtt.py --resultado herido
```

El script hace lo siguiente:

1. Se conecta a Mosquitto.
2. Se suscribe a topicos de estado, sensores, IA, alertas y actuadores.
3. Publica `sistema/cmd/modo = ia`.
4. Publica `sistema/cmd/ia/estado = on`.
5. Publica un resultado de prueba en `sistema/ia/resultado`.
6. Muestra con timestamp las respuestas recibidas.

Probar los tres estados principales:

```bash
python3 verificar_e3_pipeline_mqtt.py --resultado herido
python3 verificar_e3_pipeline_mqtt.py --resultado ileso
python3 verificar_e3_pipeline_mqtt.py --resultado sin_lectura
```

Respuesta fisica esperada en ESP32:

| Resultado IA | Actuador esperado |
|---|---|
| `herido` | LED rojo y buzzer de alerta |
| `ileso` | LED azul y buzzer apagado |
| `sin_lectura` | LED amarillo y buzzer suave |

---

## Topicos E3

| Direccion | Topico | Mensaje | Funcion |
|---|---|---|---|
| Interfaz/Python -> ESP32 | `sistema/cmd/modo` | `ia` | Pone el ESP32 en modo IA |
| Interfaz/Python -> IA/ESP32 | `sistema/cmd/ia/estado` | `on` / `off` | Activa o apaga la IA |
| ESP32 -> Python | `sistema/sensores/pir` | `true` / `false` | Evidencia de sensor por MQTT |
| ESP32 -> Python | `sistema/sensores/ultrasonico` | distancia en cm | Evidencia de sensor por MQTT |
| Python IA -> ESP32 | `sistema/ia/resultado` | JSON | Resultado del modelo |
| ESP32/Python -> interfaz | `sistema/alertas/ultima` | texto | Alerta legible |
| ESP32 -> Python | `sistema/actuadores/base/grados` | grados | Evidencia de actuador/servo |

---

## JSON publicado por la IA

Ejemplo para deteccion positiva:

```json
{
  "estado_ia": "activa",
  "lectura": "herido",
  "clase": "Seno Herido",
  "confianza": 0.91,
  "alerta": true,
  "timestamp": "2026-06-12T10:30:00"
}
```

El ESP32 procesa `lectura`:

```text
herido -> ROJO
ileso -> AZUL
sin_lectura/falso -> AMARILLO
```

---

## Checklist E3

| Requisito | Estado en esta version | Evidencia |
|---|---:|---|
| Modelo probado con datos estaticos antes de conectar MQTT | Cumplido al ejecutar prueba | `probar_modelo_estatico.py` |
| Pipeline completo extremo a extremo funcionando | Cumplido si se ejecuta con hardware | `ia_processor_mqtt.py` + `verificar_e3_pipeline_mqtt.py` |
| Raspberry Pi / camara funcional con rol en IA | Cumplido | La Raspberry captura imagenes con OpenCV, ejecuta YOLO y publica el resultado por MQTT |
| Equipo explica que detecta el modelo y precision | Cumplido con evidencias de entrenamiento | `Datav3.yml`, `results.csv`, curvas y matriz |

---

## Evidencias recomendadas para entregar

Tomar capturas o video de:

1. `python3 probar_modelo_estatico.py` mostrando predicciones.
2. Carpeta `evidencias_e3/prueba_modelo_estatico/` con imagenes anotadas.
3. `python3 ia_processor_mqtt.py` publicando resultados reales.
4. `python3 verificar_e3_pipeline_mqtt.py --resultado herido` mostrando timestamps.
5. ESP32 cambiando LED rojo/azul/amarillo y buzzer segun resultado IA.
6. Interfaz mostrando `resultado_ia` y `alerta_ultima`.
