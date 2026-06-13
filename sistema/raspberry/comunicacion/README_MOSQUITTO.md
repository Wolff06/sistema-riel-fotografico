# Configuracion de Mosquitto en Raspberry Pi

## Objetivo

Configurar la Raspberry Pi como broker MQTT local para el proyecto CANMA.  
La ESP32 se conecta a la red `RaspberryLAN` y utiliza la IP `192.168.4.1` para enviar y recibir mensajes MQTT.

## Datos de conexion

| Parametro | Valor |
|---|---|
| Broker MQTT | Mosquitto |
| Host | 192.168.4.1 |
| Puerto | 1884 |
| Usuario | admin |
| Contrasena | 123 |
| Red WiFi | RaspberryLAN |

## Instalacion

Ejecutar desde la carpeta:

```bash
cd sistema/raspberry/comunicacion
chmod +x instalar_mosquitto.sh
./instalar_mosquitto.sh
```

## Verificar que Mosquitto esta activo

```bash
sudo systemctl status mosquitto
```

## Escuchar todos los mensajes del proyecto

```bash
mosquitto_sub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/#" -v
```

## Enviar comando de prueba al servo de base

```bash
mosquitto_pub -h 192.168.4.1 -p 1884 -u admin -P 123 -t "sistema/cmd/base/mover" -m "120"
```

## Ejecutar verificacion E2 con Python

Solo escuchar datos con timestamp:

```bash
python3 verificar_e2_mqtt.py
```

Escuchar datos y enviar un comando de prueba al servo de base:

```bash
python3 verificar_e2_mqtt.py --enviar-comando --angulo 120
```

La documentacion completa de la entrega E2 esta en:

```text
sistema/raspberry/comunicacion/E2_MQTT_CHECKLIST.md
```