import cv2
import imutils
import os
import numpy as np
import tkinter as tk
import vista_pantalla as vista
from PIL import Image as PILImage
from PIL import ImageTk
from ultralytics import YOLO
from tkinter import filedialog

class ModeloPantalla:    
    def __init__ (self):
        self.pantalla = None
        self.camara = None
        self.frame = None
        
        self.rgb = 1
        self.gray = 0
        self.canny = 0

        self.slider_umbral_alto = None
        self.slider_umbral_bajo = None
        self.lblVideo = None

        self.grabando = False
        self.guardando_frames = False
        self.clasificando = False
        self.video_writer = None
        self.modelo_ia = None

    #Creamos el metodo visualizar para activar los fitros de la camara de video de nuestro dispositivo
    def visualizar(self):
        if self.camara is not None:
            validar, self.frame = self.camara.read()
            if validar:
                frame = self.frame

                # Aplicar filtros según selección
                if self.rgb == 1:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                elif self.gray == 1:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                elif self.canny == 1:
                    grises = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    umbral_alto = self.slider_umbral_alto.get()
                    umbral_bajo = self.slider_umbral_bajo.get()
                    bordes_canny = cv2.Canny(grises, umbral_bajo, umbral_alto)
                    frame = cv2.bitwise_and(frame, frame, mask=bordes_canny)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                frame = cv2.resize(frame, (400,240))


                # Guardado de video/frames si corresponde
                if self.grabando and self.video_writer is not None:
                    self.video_writer.write(self.frame)

                if self.guardando_frames:
                    self.guardar_frame()
            
                if self.clasificando and self.modelo_ia is not None:
                    results = self.modelo_ia(self.frame, imgsz=320)
                    frame = cv2.resize(results[0].plot(),(400,240))

                # Manejo seguro de la imagen para Tkinter
                if len(frame.shape) == 2:
                    imagen = PILImage.fromarray(frame).convert("RGB")
                else:
                    imagen = PILImage.fromarray(frame)

                imagen_a_video = ImageTk.PhotoImage(image=imagen)

                # Mostrar en pantalla
                self.lblVideo.configure(image=imagen_a_video)
                self.lblVideo.image = imagen_a_video
                self.lblVideo.after(10, self.visualizar)
            else:
                self.camara.release()


    #Creamos un metodo para activar la camara del disposiitivo
    def activar_camara(self):
        self.camara = cv2.VideoCapture(0)
        self.lblVideo = tk.Label(self.pantalla)
        self.lblVideo.place(x=345, y=60)
        self.visualizar()
        print("Camara seleccionada")

    #Creamos un metodo para deactivar la camara del dispositivo
    def desactivar_camara(self):
        self.camara.release()
        cv2.destroyAllWindows()
        self.lblVideo.destroy()
        print("Fin")

    #Creamos un metodo para cambiar la imagen de video a un filtro rgb
    def filtro_rgb(self):
        self.rgb = 1
        self.gray = 0
        self.canny = 0

    #Creamos un metodo para cambiar la imagen de video a un filtro en grises
    def filtro_gray(self):
        self.rgb = 0
        self.gray = 1
        self.canny = 0

    #Creamos un metodo para cambiar la imagen de video a un filtro de bordes
    def filtro_canny(self):
        self.rgb = 0
        self.gray = 0
        self.canny = 1

    # Metodo para activar la grabacion del video y guardar el video en la carpeta del proyecto (Videos_grabados)
    def iniciar_grabacion(self):
        ruta = "./Videos_grabados"
        os.makedirs(ruta, exist_ok=True)

        # Generar un nombre único para el video basado en la cantidad de videos existentes en la carpeta
        nombre = f"video_{len(os.listdir(ruta)) + 1}.avi"
        ruta_completa = os.path.join(ruta, nombre)

        # Definir el codec y crear el objeto VideoWriter para guardar el video
        fourcc = cv2.VideoWriter_fourcc(*'XVID')

        # El tamaño del video se establece en 640x480
        self.video_writer = cv2.VideoWriter(
            ruta_completa,
            fourcc,
            20.0,
            (640, 480)
        )

        self.grabando = True
        print("Grabando...")
    
    # Metodo para detener la grabacion del video
    def detener_grabacion(self):
        self.grabando = False
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
        print("Grabación detenida.")

    # Metodo para guardar cada frame del video en la carpeta del proyecto (Imagenes_capturas)
    # El parametro "salto" indica cada cuantos frames se guardara una imagen, por ejemplo, si salto=30, se guardara una imagen cada 30 frames del video.
    def extraer_frames(self, ruta_video, salto=30): 
        ruta_salida = "./Imagenes_capturas"
        os.makedirs(ruta_salida, exist_ok=True)
        cap = cv2.VideoCapture(ruta_video)
        contador = 0
        guardados = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if contador % salto == 0:
                nombre_frame = f"frame_{contador}.jpg"
                ruta_frame = os.path.join(ruta_salida, nombre_frame)
                cv2.imwrite(ruta_frame, frame)
                guardados += 1
            contador += 1
        cap.release()
        print(f"Se han extraído {contador} frames del video y se han guardado en {ruta_salida}")

    # Metodo para activar la IA de clasificacion de imagenes
    def activar_clasificador(self):
        if self.modelo_ia is None:
            self.modelo_ia = YOLO('./Modelo/best.pt')
        self.clasificando = True
        print("Clasificador activado.")

    # Metodo para desactivar la IA de clasificacion de imagenes
    def desactivar_clasificador(self):
        self.clasificando = False
        print("Clasificador desactivado.")

    def seleccionar_video(self):
        # Abrir un cuadro de diálogo para seleccionar un video en la carpeta del proyecto (Videos_grabados)
        ruta_video = filedialog.askopenfilename(initialdir="./Videos_grabados", title="Seleccionar video", filetypes=(("Archivos de video", "*.avi;*.mp4"), ("Todos los archivos", "*.*")))
        if ruta_video:
            self.extraer_frames(ruta_video)  
