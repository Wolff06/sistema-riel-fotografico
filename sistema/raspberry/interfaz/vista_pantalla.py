#Importación de librerias
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import imutils
import numpy as np
import os
import modelo_pantalla as modelo

class VistaPantalla:
    def __init__ (self, modelo):
        self.modelo = modelo

        # Tamaño ajustado para pantalla de 800x480
        self.ANCHO_PANTALLA = 800
        self.ALTO_PANTALLA = 480

        # Tamaño del recuadro de video.
        # Se bajó de 480x360 a 360x270 para que no se vea tan grande
        # en la pantalla física de 800x480.
        self.VIDEO_ANCHO = 360
        self.VIDEO_ALTO = 270

        #Construcción de la pantalla
        self.pantalla = tk.Tk()
        self.pantalla.title("Escaner Modelador")
        # Modo pantalla completa real para pantallas Raspberry/800x480.
        # Evita que la barra superior y el borde de la ventana corten la interfaz.
        self.pantalla.geometry(f"{self.ANCHO_PANTALLA}x{self.ALTO_PANTALLA}+0+0")
        self.pantalla.resizable(0,0)
        self.pantalla.attributes("-fullscreen", False)
        self.pantalla.overrideredirect(True)
        self.pantalla.bind("<Escape>", lambda evento: self.pantalla.destroy())

        #Implementar una imagen de fondo para personalizar la pantalla
        self.ruta_imagen_fondo = "./Detalles_de_pantalla/fondo_de_pantalla.png"
        imagen_fondo_original = Image.open(self.ruta_imagen_fondo)
        try:
            remuestreo = Image.Resampling.LANCZOS
        except AttributeError:
            remuestreo = Image.LANCZOS
        imagen_fondo_redimensionada = imagen_fondo_original.resize(
            (self.ANCHO_PANTALLA, self.ALTO_PANTALLA),
            remuestreo
        )
        self.imagen_fondo = ImageTk.PhotoImage(imagen_fondo_redimensionada)
        self.background = tk.Label(self.pantalla, image=self.imagen_fondo, text="Fondo")
        self.background.place(x=0, y=0, width=self.ANCHO_PANTALLA, height=self.ALTO_PANTALLA)

        #Implementar etiquetas de texto en la pantalla
        self.etiqueta_control = tk.Label(self.pantalla, text="CONTROLES DE VIDEO:", font=("Calibri", 10))
        self.etiqueta_control.place(x=80, y=8)

        self.etiqueta_video = tk.Label(self.pantalla, text="VIDEO EN TIEMPO REAL:", font=("Calibri", 10))
        self.etiqueta_video.place(x=495, y=28)

        self.etiqueta_filtro = tk.Label(self.pantalla, text="FILTROS DE CAMARA:", font=("Calibri", 10))
        self.etiqueta_filtro.place(x=85, y=180)

        self.etiqueta_canny = tk.Label(self.pantalla, text="CONTROL DE UMBRALES DE CANNY:", font=("Calibri", 9))
        self.etiqueta_canny.place(x=35, y=350)

        #Construcción de los botones para navegar con las funciones de la pantalla
        self.ruta_imagen_boton_inicio = "./Detalles_de_pantalla/abierto.png"
        self.imagen_boton_inicio = tk.PhotoImage(file=self.ruta_imagen_boton_inicio)
        self.boton_inicio = tk.Button(self.pantalla, text="Iniciar", image=self.imagen_boton_inicio, width=90, height=60, font=("Calibri", 10))
        self.boton_inicio.place(x=45, y=40)

        self.ruta_imagen_boton_fin = "./Detalles_de_pantalla/cerrar.png"
        self.imagen_boton_fin = tk.PhotoImage(file=self.ruta_imagen_boton_fin)
        self.boton_fin = tk.Button(self.pantalla, text="Terminar", image=self.imagen_boton_fin, width=90, height=60, font=("Calibri", 10))
        self.boton_fin.place(x=160, y=40)

        self.ruta_imagen_boton_iniciar_grabacion = "./Detalles_de_pantalla/captura.png"
        self.imagen_boton_iniciar_grabacion = tk.PhotoImage(file=self.ruta_imagen_boton_iniciar_grabacion)
        self.boton_iniciar_grabacion = tk.Button(self.pantalla, text="Capturar", image=self.imagen_boton_iniciar_grabacion, width=90, height=50, font=("Calibri", 10))
        self.boton_iniciar_grabacion.place(x=45, y=115)
        self.boton_iniciar_grabacion.config(state=tk.DISABLED)

        self.ruta_imagen_boton_detener_grabacion = "./Detalles_de_pantalla/parar.png"
        self.imagen_boton_detener_grabacion = tk.PhotoImage(file=self.ruta_imagen_boton_detener_grabacion)
        self.boton_detener_grabacion = tk.Button(self.pantalla, text="Detener Grabacion", image=self.imagen_boton_detener_grabacion, width=90, height=50, font=("Calibri", 10))
        self.boton_detener_grabacion.place(x=160, y=115)
        self.boton_detener_grabacion.config(state=tk.DISABLED)

        self.ruta_imagen_boton_rgb = "./Detalles_de_pantalla/rgb.png"
        self.imagen_boton_rgb = tk.PhotoImage(file=self.ruta_imagen_boton_rgb)
        self.boton_rgb = tk.Button(self.pantalla, text="RGB", image=self.imagen_boton_rgb, width=200, height=40, font=("Calibri", 10))
        self.boton_rgb.place(x=45, y=210)

        self.ruta_imagen_boton_grises = "./Detalles_de_pantalla/grises.png"
        self.imagen_boton_grises = tk.PhotoImage(file=self.ruta_imagen_boton_grises)
        self.boton_grises = tk.Button(self.pantalla, text="Grises", image=self.imagen_boton_grises, width=200, height=40, font=("Calibri", 10))
        self.boton_grises.place(x=45, y=255)

        self.ruta_imagen_boton_canny = "./Detalles_de_pantalla/canny.png"
        self.imagen_boton_canny = tk.PhotoImage(file=self.ruta_imagen_boton_canny)
        self.boton_canny = tk.Button(self.pantalla, text="Canny", image=self.imagen_boton_canny, width=200, height=40, font=("Calibri", 10))
        self.boton_canny.place(x=45, y=300)

        self.ruta_imagen_boton_ia = "./Detalles_de_pantalla/ia.png"
        self.imagen_boton_ia = tk.PhotoImage(file=self.ruta_imagen_boton_ia)
        self.boton_ia = tk.Button(self.pantalla, text="Activar Clasificador", image=self.imagen_boton_ia, width=165, height=35, font=("Calibri", 10))
        self.boton_ia.place(x=345, y=420)

        self.ruta_imagen_extraer_frames = "./Detalles_de_pantalla/extraer_frames.png"
        self.imagen_extraer_frames = tk.PhotoImage(file=self.ruta_imagen_extraer_frames)
        self.boton_extraer_frames = tk.Button(self.pantalla, text="Extraer Frames", image=self.imagen_extraer_frames, width=165, height=35, font=("Calibri", 10))
        self.boton_extraer_frames.place(x=565, y=420)

        #Sliders para controlar el valor de los umbrales alto y bajo del filtro de cámara: "Canny"
        self.slider_umbral_alto = tk.Scale(self.pantalla, from_=0, to=255, orient=tk.HORIZONTAL)
        self.slider_umbral_alto.place(x=45, y=375, width=205)

        self.slider_umbral_bajo = tk.Scale(self.pantalla, from_=0, to=255, orient=tk.HORIZONTAL)
        self.slider_umbral_bajo.place(x=45, y=425, width=205)

        #Ubicacion de la camara de video
        # Área recomendada para frames redimensionados a 360x270.
        self.lblVideo = tk.Label(self.pantalla, bg="black")
        self.lblVideo.place(x=390, y=75, width=self.VIDEO_ANCHO, height=self.VIDEO_ALTO)

    def ajustar_frame_video(self, frame):
        """
        Redimensiona el frame de OpenCV al tamaño del recuadro de video.
        Esta línea evita que el video se muestre demasiado grande en la pantalla.
        """
        frame = cv2.resize(frame, (360, 270))
        return frame

    def mostrar_frame_en_pantalla(self, frame):
        """
        Convierte y muestra un frame de OpenCV en el Label de video.
        Puedes llamar esta función desde la parte del código donde lees la cámara.
        """
        frame = cv2.resize(frame, (360, 270))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imagen = Image.fromarray(frame)
        imagen = ImageTk.PhotoImage(image=imagen)
        self.lblVideo.configure(image=imagen)
        self.lblVideo.image = imagen
