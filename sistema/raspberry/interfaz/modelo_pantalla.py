# -*- coding: utf-8 -*-
# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/raspberry/interfaz/modelo_pantalla.py
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# OBJETIVO:
# Controlar la camara de la Raspberry, mostrar video en la interfaz Tkinter,
# aplicar filtros, grabar video, extraer frames y ejecutar la IA en la Raspberry.
# La IA publica su resultado por MQTT para que el ESP32 controle LEDs y buzzer.
# =============================================================================

import os
import json
import time
from datetime import datetime
from tkinter import filedialog

import cv2
import numpy as np
from PIL import Image as PILImage
from PIL import ImageTk

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


class ModeloPantalla:
    """
    Modelo de la pantalla de captura.

    Importante:
    - No crea otro Label de video. Usa el lblVideo que ya existe en la vista.
    - No ejecuta IA en la ESP32. La IA corre aqui, en Raspberry/Python.
    - Solo publica resultados IA cuando el boton Activar IA esta encendido.
    """

    T_IA_RESULTADO = "sistema/ia/resultado"
    T_ALERTA_ULTIMA = "sistema/alertas/ultima"

    def __init__(self):
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

        self.publicar_mqtt = None
        self._ultimo_envio_ia = 0
        self._intervalo_envio_ia = 1.0

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ruta_videos = os.path.join(self.base_dir, "Videos_grabados")
        self.ruta_capturas = os.path.join(self.base_dir, "Imagenes_capturas")

        self.rutas_modelo = [
            os.path.abspath(os.path.join(
                self.base_dir,
                "..", "IA", "Modelo-Feb2026", "runs", "cancer", "train_v1", "weights", "best.pt"
            )),
            os.path.abspath(os.path.join(
                self.base_dir,
                "..", "IA", "Modelo-Feb2026", "runs", "cancer_SinFalsosPositivos", "weights", "best.pt"
            )),
            os.path.abspath(os.path.join(self.base_dir, "Modelo", "best.pt")),
        ]

    def configurar_publicador_mqtt(self, funcion_publicar):
        """Configura la funcion para publicar datos de IA por MQTT."""
        self.publicar_mqtt = funcion_publicar

    def activar_camara(self):
        """Abre la camara fisica y empieza a mostrar video."""
        if self.camara is not None and self.camara.isOpened():
            return True

        for indice in (0, 1):
            camara = cv2.VideoCapture(indice, cv2.CAP_V4L2)
            camara.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            if camara.isOpened():
                self.camara = camara
                print("Camara seleccionada en indice", indice)
                self.visualizar()
                return True

            camara.release()

        print("No se pudo abrir la camara. Revisa conexion, permisos o indice.")
        self.camara = None
        self._mostrar_texto_video("Sin camara")
        return False

    def desactivar_camara(self):
        """Apaga IA, grabacion y camara de forma segura."""
        self.desactivar_clasificador(publicar=True)
        self.detener_grabacion()

        if self.camara is not None:
            try:
                self.camara.release()
            except Exception:
                pass
            self.camara = None

        if self.lblVideo is not None:
            self.lblVideo.configure(image="")
            self.lblVideo.image = None

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        print("Camara apagada")

    def visualizar(self):
        """Lee un frame, aplica filtro/IA y lo muestra en Tkinter."""
        if self.camara is None:
            return

        validar, frame_original = self.camara.read()

        if not validar or frame_original is None:
            print("No se pudo leer frame de camara")
            if self.lblVideo is not None:
                self.lblVideo.after(100, self.visualizar)
            return

        self.frame = frame_original.copy()
        frame_mostrar = self._aplicar_filtro(frame_original.copy())

        if self.grabando and self.video_writer is not None:
            try:
                self.video_writer.write(frame_original)
            except Exception as error:
                print("Error grabando video:", error)

        if self.clasificando and self.modelo_ia is not None:
            frame_mostrar = self._procesar_frame_ia(frame_original.copy())

        self._mostrar_frame(frame_mostrar)

        if self.lblVideo is not None and self.camara is not None:
            self.lblVideo.after(30, self.visualizar)

    def _aplicar_filtro(self, frame):
        """Devuelve el frame con el filtro visual seleccionado."""
        if self.rgb == 1:
            return frame

        if self.gray == 1:
            gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gris, cv2.COLOR_GRAY2BGR)

        if self.canny == 1:
            grises = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            alto = 150
            bajo = 60

            if self.slider_umbral_alto is not None:
                alto = int(self.slider_umbral_alto.get())
            if self.slider_umbral_bajo is not None:
                bajo = int(self.slider_umbral_bajo.get())

            bordes = cv2.Canny(grises, bajo, alto)
            return cv2.bitwise_and(frame, frame, mask=bordes)

        return frame

    def _procesar_frame_ia(self, frame):
        """Ejecuta YOLO, calcula lectura mayoritaria y publica MQTT."""
        try:
            resultados = self.modelo_ia.predict(
                source=frame,
                imgsz=320,
                conf=0.25,
                verbose=False,
                stream=False,
            )
        except Exception as error:
            print("Error ejecutando IA:", error)
            self._publicar_resultado_ia("sin_lectura", "Error IA", 0)
            return frame

        resultado = resultados[0]
        frame_anotado = resultado.plot()
        lectura, clase, confianza = self._calcular_lectura_mayoritaria(resultado)
        self._publicar_resultado_ia(lectura, clase, confianza)
        return frame_anotado

    def _calcular_lectura_mayoritaria(self, resultado):
        """Decide si domina herido, ileso o sin clasificacion."""
        if resultado.boxes is None or len(resultado.boxes) == 0:
            return "sin_lectura", "Sin deteccion", 0

        puntajes = {
            "herido": 0.0,
            "ileso": 0.0,
            "sin_clasificacion": 0.0,
        }
        mejor_clase = "Sin deteccion"
        mejor_confianza = 0.0

        try:
            clases = resultado.boxes.cls.cpu().numpy().astype(int)
            confianzas = resultado.boxes.conf.cpu().numpy()
        except Exception:
            return "sin_lectura", "Sin deteccion", 0

        for clase_id, confianza in zip(clases, confianzas):
            nombre = str(self.modelo_ia.names.get(int(clase_id), str(clase_id)))
            lectura = self._normalizar_clase(nombre)
            confianza = float(confianza)
            puntajes[lectura] = puntajes.get(lectura, 0.0) + confianza

            if confianza > mejor_confianza:
                mejor_confianza = confianza
                mejor_clase = nombre

        lectura_ganadora = max(puntajes, key=puntajes.get)
        if puntajes[lectura_ganadora] <= 0:
            lectura_ganadora = "sin_lectura"

        return lectura_ganadora, mejor_clase, round(mejor_confianza, 3)

    def _normalizar_clase(self, clase):
        """Convierte el nombre de clase del modelo en lectura del sistema."""
        texto = str(clase).lower().strip()

        if "herid" in texto or "cancer" in texto or "lesion" in texto or "lesión" in texto:
            return "herido"
        if "iles" in texto or "sano" in texto or "salud" in texto:
            return "ileso"
        if "falso" in texto or "otro" in texto or "sin" in texto:
            return "sin_clasificacion"

        return "sin_clasificacion"

    def _publicar_resultado_ia(self, lectura, clase, confianza):
        """Publica resultado de IA a MQTT sin saturar el broker."""
        if self.publicar_mqtt is None:
            return

        ahora = time.time()
        if ahora - self._ultimo_envio_ia < self._intervalo_envio_ia:
            return

        self._ultimo_envio_ia = ahora
        datos = {
            "estado_ia": "activa" if self.clasificando else "apagada",
            "lectura": lectura,
            "clase": clase,
            "confianza": confianza,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        if lectura == "herido":
            alerta = "IA: posible hallazgo visual detectado"
        elif lectura == "ileso":
            alerta = "IA: lectura sin alerta visual"
        else:
            alerta = "IA: sin lectura confiable"

        mensaje = json.dumps(datos, ensure_ascii=False)
        print("Resultado IA MQTT:", mensaje)
        self.publicar_mqtt(self.T_IA_RESULTADO, mensaje)
        self.publicar_mqtt(self.T_ALERTA_ULTIMA, alerta)

    def activar_clasificador(self):
        """Carga el modelo YOLO y activa clasificacion."""
        if YOLO is None:
            print("No esta instalado ultralytics. Instala con: python3 -m pip install ultralytics")
            return False

        if self.modelo_ia is None:
            ruta_elegida = None
            for ruta in self.rutas_modelo:
                if os.path.exists(ruta):
                    ruta_elegida = ruta
                    break

            if ruta_elegida is None:
                print("No se encontro best.pt en rutas conocidas:")
                for ruta in self.rutas_modelo:
                    print(" -", ruta)
                return False

            print("Cargando modelo IA:", ruta_elegida)
            self.modelo_ia = YOLO(ruta_elegida)

        self.clasificando = True
        self._ultimo_envio_ia = 0
        print("Clasificador activado")
        return True

    def desactivar_clasificador(self, publicar=False):
        """Apaga la clasificacion IA."""
        estaba_activa = self.clasificando
        self.clasificando = False

        if publicar and estaba_activa and self.publicar_mqtt is not None:
            datos = {
                "estado_ia": "apagada",
                "lectura": "sin_lectura",
                "clase": "IA apagada",
                "confianza": 0,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            self.publicar_mqtt(self.T_IA_RESULTADO, json.dumps(datos, ensure_ascii=False))
            self.publicar_mqtt(self.T_ALERTA_ULTIMA, "IA apagada")

        print("Clasificador desactivado")

    def filtro_rgb(self):
        """Selecciona imagen RGB normal."""
        self.rgb = 1
        self.gray = 0
        self.canny = 0

    def filtro_gray(self):
        """Selecciona filtro en grises."""
        self.rgb = 0
        self.gray = 1
        self.canny = 0

    def filtro_canny(self):
        """Selecciona filtro Canny."""
        self.rgb = 0
        self.gray = 0
        self.canny = 1

    def iniciar_grabacion(self):
        """Inicia grabacion de video en carpeta Videos_grabados."""
        if self.camara is None:
            print("No se puede grabar porque la camara esta apagada")
            return False

        os.makedirs(self.ruta_videos, exist_ok=True)
        nombre = "video_{}.avi".format(len(os.listdir(self.ruta_videos)) + 1)
        ruta_completa = os.path.join(self.ruta_videos, nombre)
        fourcc = cv2.VideoWriter_fourcc(*"XVID")

        self.video_writer = cv2.VideoWriter(ruta_completa, fourcc, 20.0, (640, 480))
        self.grabando = True
        print("Grabando en:", ruta_completa)
        return True

    def detener_grabacion(self):
        """Detiene grabacion si estaba activa."""
        self.grabando = False
        if self.video_writer is not None:
            try:
                self.video_writer.release()
            except Exception:
                pass
            self.video_writer = None

    def extraer_frames(self, ruta_video, salto=30):
        """Extrae frames de un video seleccionado."""
        os.makedirs(self.ruta_capturas, exist_ok=True)
        cap = cv2.VideoCapture(ruta_video)
        contador = 0
        guardados = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if contador % salto == 0:
                nombre_frame = "frame_{}.jpg".format(contador)
                ruta_frame = os.path.join(self.ruta_capturas, nombre_frame)
                cv2.imwrite(ruta_frame, frame)
                guardados += 1
            contador += 1

        cap.release()
        print("Frames extraidos:", guardados, "en", self.ruta_capturas)

    def seleccionar_video(self):
        """Abre dialogo para seleccionar video y extraer frames."""
        ruta_video = filedialog.askopenfilename(
            initialdir=self.ruta_videos,
            title="Seleccionar video",
            filetypes=(("Archivos de video", "*.avi;*.mp4"), ("Todos los archivos", "*.*")),
        )
        if ruta_video:
            self.extraer_frames(ruta_video)

    def _mostrar_frame(self, frame):
        """Muestra un frame BGR o gris en el Label de video."""
        if self.lblVideo is None:
            return

        frame = cv2.resize(frame, (360, 270))
        if len(frame.shape) == 2:
            imagen = PILImage.fromarray(frame).convert("RGB")
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imagen = PILImage.fromarray(frame_rgb)

        imagen_a_video = ImageTk.PhotoImage(image=imagen)
        self.lblVideo.configure(image=imagen_a_video)
        self.lblVideo.image = imagen_a_video

    def _mostrar_texto_video(self, texto):
        """Muestra un recuadro negro con texto cuando no hay camara."""
        frame = np.zeros((270, 360, 3), dtype=np.uint8)
        cv2.putText(frame, texto, (60, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        self._mostrar_frame(frame)
