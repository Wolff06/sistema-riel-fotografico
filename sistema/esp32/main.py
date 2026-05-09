# =============================================================================
# PROYECTO: Sistema de Riel Semicircular Fotográfico 180°
# INTEGRANTES: 
#              Macias Campos Ariadne Lizett 
#              Soto Garnica Ari Adair 
#              Lira Gamiño Luis Fernando 


# DESCRIPCIÓN: Script principal del ESP32. Coordina el barrido fotográfico de
#              180° usando la biblioteca de clases 'dispositivos.py'. La RPi
#              envía el comando "FOTO_OK" por USB-Serial cuando termina de
#              capturar; el ESP32 avanza al siguiente ángulo y confirma.
#              Toda la interacción con el hardware ocurre exclusivamente
#              a través de CajaSensores y CajaActuadores.
# =============================================================================
