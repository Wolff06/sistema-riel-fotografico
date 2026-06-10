# - OBJETIVO DEL CODIGO -
# Inicializar y ejecutar la interfaz
# gráfica del sistema mediante la 
# estructura Modelo-Vista-Controlador.

# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando

from modelo_pantalla import ModeloPantalla
from vista_pantalla import VistaPantalla
from controlador_pantalla import ControladorPantalla

if __name__ == "__main__":
    modelo = ModeloPantalla()
    vista = VistaPantalla(modelo)
    controlador = ControladorPantalla(modelo, vista)
    vista.pantalla.mainloop()
