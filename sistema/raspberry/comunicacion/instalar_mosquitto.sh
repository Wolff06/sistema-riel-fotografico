#!/bin/bash

# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
# ARCHIVO: instalar_mosquitto.sh
# OBJETIVO:
# Instalar y configurar Mosquitto en la Raspberry Pi como broker MQTT local.
# El broker escuchará en el puerto 1884 para que la ESP32 pueda conectarse.
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
# =============================================================================

set -e

echo "Actualizando paquetes..."
sudo apt update

echo "Instalando Mosquitto y clientes MQTT..."
sudo apt install mosquitto mosquitto-clients -y

echo "Habilitando Mosquitto al iniciar la Raspberry..."
sudo systemctl enable mosquitto

echo "Creando usuario MQTT admin..."
sudo mosquitto_passwd -b -c /etc/mosquitto/passwd admin 123

echo "Creando configuración de Mosquitto para CANMA..."
sudo tee /etc/mosquitto/conf.d/canma.conf > /dev/null <<EOF
listener 1884 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
EOF

echo "Reiniciando Mosquitto..."
sudo systemctl restart mosquitto

echo "Verificando estado del servicio..."
sudo systemctl status mosquitto --no-pager

echo "Mosquitto quedó configurado en:"
echo "HOST: 192.168.4.1"
echo "PUERTO: 1884"
echo "USUARIO: admin"
echo "CLAVE: 123"
