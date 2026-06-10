import cv2
import imutils
import os
import numpy as np
import modelo_pantalla as modelo
import vista_pantalla as vista
import tkinter as tk
from PIL import Image, ImageTk

class ControladorPantalla:
    def __init__ (self, modelo, vista):
        self.modelo = modelo
        self.vista = vista

        self.modelo.pantalla = self.vista.pantalla 
        self.modelo.slider_umbral_alto = self.vista.slider_umbral_alto
        self.modelo.slider_umbral_bajo = self.vista.slider_umbral_bajo
        self.modelo.lblVideo = self.vista.lblVideo

        self.vista.boton_inicio.config(command=self.activar_camara)
        self.vista.boton_fin.config(command=self.desactivar_camara)
        self.vista.boton_rgb.config(command=self.filtro_rgb)
        self.vista.boton_grises.config(command=self.filtro_gray)
        self.vista.boton_canny.config(command=self.filtro_canny)
        self.vista.boton_iniciar_grabacion.config(command=self.iniciar_grabacion)
        self.vista.boton_detener_grabacion.config(command=self.detener_grabacion)
        self.vista.boton_ia.config(command=self.activar_claisificador)
        self.vista.boton_extraer_frames.config(command=self.extraer_frames)

    # Eventos de los botones
    def activar_camara(self):
        self.vista.boton_inicio.config(state=tk.DISABLED)
        self.vista.boton_fin.config(state=tk.NORMAL)
        self.vista.boton_iniciar_grabacion.config(state=tk.NORMAL)
        self.vista.boton_ia.config(state=tk.NORMAL)
        self.vista.boton_detener_grabacion.config(state=tk.DISABLED)
        self.modelo.activar_camara()

    def desactivar_camara(self):
        self.vista.boton_fin.config(state=tk.DISABLED)
        self.vista.boton_inicio.config(state=tk.NORMAL)
        self.vista.boton_iniciar_grabacion.config(state=tk.DISABLED)
        self.vista.boton_ia.config(state=tk.DISABLED)
        self.modelo.desactivar_camara()

    def iniciar_grabacion(self):
        self.vista.boton_iniciar_grabacion.config(state=tk.DISABLED)
        self.vista.boton_fin.config(state=tk.DISABLED)
        self.vista.boton_detener_grabacion.config(state=tk.NORMAL)
        self.modelo.iniciar_grabacion()

    def detener_grabacion(self):
        self.vista.boton_iniciar_grabacion.config(state=tk.NORMAL)
        self.vista.boton_fin.config(state=tk.NORMAL)
        self.vista.boton_detener_grabacion.config(state=tk.DISABLED)
        self.modelo.detener_grabacion()

    def filtro_rgb(self):
        self.modelo.filtro_rgb()
    
    def filtro_gray(self):
        self.modelo.filtro_gray()

    def filtro_canny(self):
        self.modelo.filtro_canny()

    def activar_claisificador(self):
        if self.modelo.lblVideo is not None:
            self.vista.boton_ia.config(command=self.desactivar_claisificador)
            self.modelo.activar_clasificador()
    
    def desactivar_claisificador(self):
        self.vista.boton_ia.config(command=self.activar_claisificador)
        self.modelo.desactivar_clasificador()
    
    def extraer_frames(self):
        self.modelo.seleccionar_video()