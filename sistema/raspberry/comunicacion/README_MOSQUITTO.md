# Configuración de Mosquitto en Raspberry Pi

## Objetivo

Configurar la Raspberry Pi como broker MQTT local para el proyecto CANMA.  
La ESP32 se conecta a la red `RaspberryLAN` y utiliza la IP `192.168.4.1` para enviar y recibir mensajes MQTT.

## Datos de conexión

| Parámetro | Valor |
|---|---|
| Broker MQTT | Mosquitto |
| Host | 192.168.4.1 |
| Puerto | 1884 |
| Usuario | admin |
| Contraseña | 123 |
| Red WiFi | RaspberryLAN |

## Instalación

Ejecutar desde la carpeta:

```bash
cd sistema/raspberry/comunicacion
chmod +x instalar_mosquitto.sh
./instalar_mosquitto.sh
