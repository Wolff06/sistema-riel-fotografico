#!/bin/bash
# Configurar y crear hotspot WiFi

# Abortar operaciones si un comando falla
set -e

# Checar si el script fue ejecutado con permisos elevados
if [ "$EUID" -ne 0 ]; then
  echo "Ejecuta este script con sudo: sudo ./crear_hotspot.sh"
  exit 1
fi

# Crear hotspot
nmcli device wifi hotspot ifname wlan0 ssid RaspberryLAN password charizard

# Configurar direcciones IP
nmcli connection modify Hotspot ipv4.addresses 192.168.4.1/24 ipv4.method shared

# Ligar a interfaz wireless 
nmcli connection modify Hotspot connection.interface-name wlan0

# Permitir autoconectarse a la red
nmcli connection modify Hotspot connection.autoconnect yes

# Activar hotspot
nmcli connection up Hotspot
