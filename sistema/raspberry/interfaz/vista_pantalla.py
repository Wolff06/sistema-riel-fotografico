# =============================================================================
# PROYECTO: CANMA - Garra Robótica con Cámara e IA
#
# - OBJETIVO DEL CÓDIGO -
# Diseñar y configurar la pantalla principal del sistema CANMA,
# permitiendo navegar entre las pestañas de Sensores y Captura.
# La pantalla está adaptada a una resolución de 800x480 para Raspberry Pi.
#
# En la pestaña Sensores se muestran lecturas reales recibidas desde el ESP32:
# distancia aproximada, movimiento del usuario, joystick, estado del sistema
# y grados actuales de la cámara/base.
#
# La vista NO se conecta directamente a MQTT. Para mantener el proyecto ordenado,
# esta vista recibe una función publicadora desde un archivo externo, por ejemplo:
# sistema/raspberry/comunicacion/mqtt_bridge.py
#
# - INTEGRANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
# =============================================================================

import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np
import os

try:
    import modelo_pantalla as modelo_pantalla
except Exception:
    modelo_pantalla = None


class VistaPantalla:
    # =========================================================================
    # TÓPICOS MQTT QUE LA INTERFAZ SOLICITA PUBLICAR
    # =========================================================================

    T_CMD_INICIAR_OP = "sistema/cmd/iniciar"
    T_CMD_BASE_MOVER = "sistema/cmd/base/mover"
    T_CMD_SEGURO = "sistema/cmd/seguro"

    def __init__(self, modelo=None):
        self.modelo = modelo

        # =====================================================================
        # CONFIGURACIÓN DE TAMAÑO
        # =====================================================================

        self.ANCHO_PANTALLA = 800
        self.ALTO_PANTALLA = 480

        self.VIDEO_ANCHO = 360
        self.VIDEO_ALTO = 270

        # =====================================================================
        # TEMA VISUAL
        # =====================================================================

        self.COLOR_FONDO_SUPERIOR = "#fff7fb"
        self.COLOR_FONDO_INFERIOR = "#b75d91"
        self.COLOR_BLANCO = "#ffffff"
        self.COLOR_PANEL = "#f3dce9"
        self.COLOR_PANEL_SUAVE = "#faeef5"
        self.COLOR_ROSA = "#ead3df"
        self.COLOR_ROSA_ACTIVO = "#dfbed0"
        self.COLOR_BORDE = "#111111"
        self.COLOR_TEXTO = "#111111"
        self.COLOR_GRIS = "#9c9c9c"
        self.COLOR_ROJO = "#ff2a2a"
        self.COLOR_AZUL = "#2477c8"
        self.COLOR_AMARILLO = "#c49a00"
        self.COLOR_VERDE = "#1a8f3a"

        # =====================================================================
        # VARIABLES DE ESTADO DE LA INTERFAZ
        # =====================================================================

        # Valores iniciales mientras llegan datos reales por MQTT.
        self.distancia_cm = None
        self.movimiento_usuario = False

        self.estado_sistema = "Sin conexión"
        self.error_sistema = None

        self.joystick_base = None
        self.direccion_base = "CENTRO"

        # Grados de cámara/base.
        self.grados_iniciales = 90
        self.MIN_GRADOS = 0
        self.MAX_GRADOS = 180
        self.PASO_GRADOS = 1

        # Estado del botón ON/OFF.
        self.sistema_activo = False

        # Función que será configurada desde mqtt_bridge.py.
        # Debe recibir: funcion(topico, mensaje)
        self.publicar_comando_mqtt = None

        # =====================================================================
        # CREACIÓN DE VENTANA
        # =====================================================================

        self.pantalla = tk.Tk()

        try:
            self.pantalla.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass

        self.pantalla.title("Escáner Modelador CANMA")
        self.pantalla.geometry(f"{self.ANCHO_PANTALLA}x{self.ALTO_PANTALLA}+0+0")
        self.pantalla.resizable(0, 0)
        self.pantalla.attributes("-fullscreen", False)
        self.pantalla.overrideredirect(True)
        self.pantalla.bind("<Escape>", lambda evento: self.pantalla.destroy())

        self.grados_camara = tk.IntVar(
            master=self.pantalla,
            value=self.grados_iniciales
        )

        self.ruta_imagen_fondo = "./Detalles_de_pantalla/fondo_de_pantalla.png"
        self._crear_fondo_principal()

        self.contenedor = tk.Frame(
            self.pantalla,
            bg=self.COLOR_BLANCO,
            highlightthickness=1,
            highlightbackground=self.COLOR_BORDE,
            highlightcolor=self.COLOR_BORDE,
        )
        self.contenedor.place(x=45, y=25, width=710, height=430)

        self._crear_header()
        self._crear_paginas()
        self.mostrar_pagina("sensores")

        self._programar_actualizacion_sensores()

    # =========================================================================
    # CONFIGURACIÓN EXTERNA MQTT
    # =========================================================================

    def configurar_publicador_mqtt(self, funcion_publicar):
        """
        Parámetros:
            funcion_publicar: función externa que recibe topico y mensaje.

        Hace:
            Guarda una función para publicar comandos MQTT desde la interfaz.

        Ejemplo:
            vista.configurar_publicador_mqtt(bridge.publicar)

        Devuelve:
            Nada.
        """

        self.publicar_comando_mqtt = funcion_publicar

    def _publicar_mqtt(self, topico, mensaje):
        """
        Parámetros:
            topico: tópico MQTT.
            mensaje: mensaje a publicar.

        Hace:
            Envía un comando MQTT usando la función configurada desde fuera.
            Si todavía no hay conexión MQTT configurada, imprime el comando
            en consola para depuración.

        Devuelve:
            Nada.
        """

        if self.publicar_comando_mqtt is not None:
            try:
                self.publicar_comando_mqtt(topico, str(mensaje))
            except Exception as error:
                print("Error publicando desde la interfaz:", error)
        else:
            print("MQTT no configurado:", topico, mensaje)

    # =========================================================================
    # FONDO Y ELEMENTOS GENERALES
    # =========================================================================

    def _crear_fondo_principal(self):
        """Crea el fondo general de la aplicación."""

        if os.path.exists(self.ruta_imagen_fondo):
            try:
                imagen_fondo_original = Image.open(self.ruta_imagen_fondo)

                try:
                    remuestreo = Image.Resampling.LANCZOS
                except AttributeError:
                    remuestreo = Image.LANCZOS

                imagen_fondo_redimensionada = imagen_fondo_original.resize(
                    (self.ANCHO_PANTALLA, self.ALTO_PANTALLA),
                    remuestreo,
                )

                self.imagen_fondo = ImageTk.PhotoImage(imagen_fondo_redimensionada)

                self.background = tk.Label(
                    self.pantalla,
                    image=self.imagen_fondo,
                    text="Fondo"
                )
                self.background.place(
                    x=0,
                    y=0,
                    width=self.ANCHO_PANTALLA,
                    height=self.ALTO_PANTALLA
                )
                return

            except Exception:
                pass

        self.background = tk.Canvas(self.pantalla, highlightthickness=0)
        self.background.place(
            x=0,
            y=0,
            width=self.ANCHO_PANTALLA,
            height=self.ALTO_PANTALLA
        )

        self.background.create_rectangle(
            0,
            0,
            self.ANCHO_PANTALLA,
            int(self.ALTO_PANTALLA * 0.48),
            fill=self.COLOR_FONDO_SUPERIOR,
            outline="",
        )

        self.background.create_rectangle(
            0,
            int(self.ALTO_PANTALLA * 0.48),
            self.ANCHO_PANTALLA,
            self.ALTO_PANTALLA,
            fill=self.COLOR_FONDO_INFERIOR,
            outline="",
        )

    def _crear_header(self):
        """Crea encabezado con logo y pestañas."""

        self.header = tk.Frame(self.contenedor, bg=self.COLOR_BLANCO)
        self.header.place(x=0, y=0, width=710, height=70)

        self.logo = tk.Label(
            self.header,
            text="✣ CANMA",
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_TEXTO,
            font=("Arial", 14, "bold"),
        )
        self.logo.place(x=42, y=23)

        self.boton_tab_sensores = tk.Button(
            self.header,
            text="SENSORES",
            font=("Arial", 9),
            bg=self.COLOR_ROSA,
            fg=self.COLOR_TEXTO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_TEXTO,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=lambda: self.mostrar_pagina("sensores"),
        )
        self.boton_tab_sensores.place(x=455, y=20, width=90, height=28)

        self.boton_tab_captura = tk.Button(
            self.header,
            text="CAPTURA",
            font=("Arial", 9),
            bg=self.COLOR_ROSA,
            fg=self.COLOR_TEXTO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_TEXTO,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=lambda: self.mostrar_pagina("captura"),
        )
        self.boton_tab_captura.place(x=565, y=20, width=90, height=28)

        self.linea_header = tk.Frame(self.contenedor, bg=self.COLOR_BORDE)
        self.linea_header.place(x=0, y=70, width=710, height=1)

    def _crear_paginas(self):
        """Crea los frames principales de Sensores y Captura."""

        self.pagina_sensores = tk.Frame(self.contenedor, bg=self.COLOR_BLANCO)
        self.pagina_sensores.place(x=0, y=71, width=710, height=359)

        self.pagina_captura = tk.Frame(self.contenedor, bg=self.COLOR_BLANCO)
        self.pagina_captura.place(x=0, y=71, width=710, height=359)

        self._crear_pagina_sensores()
        self._crear_pagina_captura()

    def mostrar_pagina(self, nombre_pagina):
        """Cambia entre la pestaña Sensores y Captura."""

        if nombre_pagina == "sensores":
            self.pagina_sensores.tkraise()
            self.boton_tab_sensores.config(
                bg=self.COLOR_ROSA_ACTIVO,
                font=("Arial", 9, "bold")
            )
            self.boton_tab_captura.config(
                bg=self.COLOR_ROSA,
                font=("Arial", 9)
            )
        else:
            self.pagina_captura.tkraise()
            self.boton_tab_captura.config(
                bg=self.COLOR_ROSA_ACTIVO,
                font=("Arial", 9, "bold")
            )
            self.boton_tab_sensores.config(
                bg=self.COLOR_ROSA,
                font=("Arial", 9)
            )

    # =========================================================================
    # PÁGINA SENSORES
    # =========================================================================

    def _crear_pagina_sensores(self):
        """Diseño de la pestaña Sensores ajustado para 800x480."""

        # ---------------------------------------------------------------------
        # Botones ON/OFF del sistema.
        # ---------------------------------------------------------------------

        self.boton_sistema_on = tk.Button(
            self.pagina_sensores,
            text="ON",
            font=("Arial", 9, "bold"),
            bg=self.COLOR_ROSA,
            fg=self.COLOR_TEXTO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_TEXTO,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=self.enviar_sistema_on,
        )
        self.boton_sistema_on.place(x=330, y=8, width=45, height=28)

        self.boton_sistema_off = tk.Button(
            self.pagina_sensores,
            text="OFF",
            font=("Arial", 9, "bold"),
            bg=self.COLOR_ROSA,
            fg=self.COLOR_TEXTO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_TEXTO,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=self.enviar_sistema_off,
        )
        self.boton_sistema_off.place(x=378, y=8, width=45, height=28)

        self.lbl_estado_sistema = tk.Label(
            self.pagina_sensores,
            text="Estado: Sin conexión",
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_GRIS,
            font=("Arial", 8, "bold"),
            anchor="w",
        )
        self.lbl_estado_sistema.place(x=435, y=8, width=250, height=28)

        # ---------------------------------------------------------------------
        # Tarjeta: distancia aproximada.
        # ---------------------------------------------------------------------

        self.frame_distancia = self._crear_tarjeta_sensor(
            self.pagina_sensores,
            x=38,
            y=34,
            ancho=270,
            alto=72,
            titulo="DISTANCIA APROXIMADA",
        )

        self.lbl_distancia_valor = tk.Label(
            self.frame_distancia,
            text="-- cm",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_TEXTO,
            font=("Arial", 18, "bold"),
        )
        self.lbl_distancia_valor.place(x=1, y=31, width=268, height=40)

        self.lbl_distancia_nota = tk.Label(
            self.pagina_sensores,
            text="Distancia aproximada al usuario",
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_GRIS,
            font=("Arial", 8, "bold"),
            anchor="center",
        )
        self.lbl_distancia_nota.place(x=38, y=109, width=270, height=15)

        # ---------------------------------------------------------------------
        # Tarjeta: movimiento del usuario.
        # ---------------------------------------------------------------------

        self.frame_movimiento = self._crear_tarjeta_sensor(
            self.pagina_sensores,
            x=38,
            y=128,
            ancho=270,
            alto=72,
            titulo="MOVIMIENTO EN EL USUARIO",
        )

        self.lbl_movimiento_valor = tk.Label(
            self.frame_movimiento,
            text="NO",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_TEXTO,
            font=("Arial", 18, "bold"),
        )
        self.lbl_movimiento_valor.place(x=1, y=31, width=268, height=40)

        self.lbl_movimiento_nota = tk.Label(
            self.pagina_sensores,
            text="Movimiento en el usuario",
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_GRIS,
            font=("Arial", 8, "bold"),
            anchor="center",
        )
        self.lbl_movimiento_nota.place(x=38, y=203, width=270, height=15)

        # ---------------------------------------------------------------------
        # Tarjeta: grados de la cámara/base.
        # ---------------------------------------------------------------------

        self.frame_grados = self._crear_tarjeta_sensor(
            self.pagina_sensores,
            x=38,
            y=222,
            ancho=270,
            alto=72,
            titulo="GRADOS REQUERIDOS DE LA CÁMARA",
        )

        self.boton_grado_menos = tk.Button(
            self.frame_grados,
            text="◀",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_BLANCO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_BLANCO,
            relief="flat",
            bd=0,
            font=("Arial", 19, "bold"),
            command=lambda: self.cambiar_grados(-self.PASO_GRADOS),
        )
        self.boton_grado_menos.place(x=10, y=35, width=48, height=28)

        self.lbl_grados_valor = tk.Label(
            self.frame_grados,
            textvariable=self.grados_camara,
            bg=self.COLOR_PANEL,
            fg=self.COLOR_TEXTO,
            font=("Arial", 20, "bold"),
        )
        self.lbl_grados_valor.place(x=70, y=31, width=130, height=40)

        self.boton_grado_mas = tk.Button(
            self.frame_grados,
            text="▶",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_BLANCO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_BLANCO,
            relief="flat",
            bd=0,
            font=("Arial", 19, "bold"),
            command=lambda: self.cambiar_grados(self.PASO_GRADOS),
        )
        self.boton_grado_mas.place(x=212, y=35, width=48, height=28)

        self.lbl_rango_grados = tk.Label(
            self.pagina_sensores,
            text="Rango permitido: 0 a 180 grados",
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_GRIS,
            font=("Arial", 8, "bold"),
            anchor="center",
        )
        self.lbl_rango_grados.place(x=50, y=298, width=245, height=15)

        # ---------------------------------------------------------------------
        # Botón de estado seguro.
        # ---------------------------------------------------------------------

        self.boton_estado_seguro = tk.Button(
            self.pagina_sensores,
            text="ESTADO SEGURO",
            font=("Arial", 8, "bold"),
            bg=self.COLOR_ROSA,
            fg=self.COLOR_TEXTO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_TEXTO,
            relief="solid",
            bd=1,
            cursor="hand2",
            command=self.enviar_estado_seguro,
        )
        self.boton_estado_seguro.place(x=38, y=322, width=270, height=26)

        # ---------------------------------------------------------------------
        # Panel de mensajes para el usuario.
        # ---------------------------------------------------------------------

        self.frame_mensajes = tk.Frame(
            self.pagina_sensores,
            bg=self.COLOR_PANEL,
            highlightthickness=1,
            highlightbackground="#efcfe0",
            highlightcolor="#efcfe0",
        )
        self.frame_mensajes.place(x=325, y=42, width=360, height=245)

        self.lbl_titulo_mensajes = tk.Label(
            self.frame_mensajes,
            text="Mensajes para el usuario",
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_TEXTO,
            font=("Times New Roman", 20, "bold"),
        )
        self.lbl_titulo_mensajes.place(x=0, y=0, width=360, height=48)

        self.linea_msg_1 = tk.Frame(self.frame_mensajes, bg=self.COLOR_BLANCO)
        self.linea_msg_1.place(x=0, y=123, width=360, height=1)

        self.linea_msg_2 = tk.Frame(self.frame_mensajes, bg=self.COLOR_BLANCO)
        self.linea_msg_2.place(x=0, y=197, width=360, height=1)

        self.lbl_msg_distancia_titulo = tk.Label(
            self.frame_mensajes,
            text="",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_ROJO,
            font=("Arial", 9, "bold"),
            anchor="w",
            justify="left",
            wraplength=325,
        )
        self.lbl_msg_distancia_titulo.place(x=16, y=60, width=330, height=18)

        self.lbl_msg_distancia_detalle = tk.Label(
            self.frame_mensajes,
            text="",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_TEXTO,
            font=("Arial", 9),
            anchor="nw",
            justify="left",
            wraplength=325,
        )
        self.lbl_msg_distancia_detalle.place(x=16, y=82, width=330, height=35)

        self.lbl_msg_movimiento_titulo = tk.Label(
            self.frame_mensajes,
            text="",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_ROJO,
            font=("Arial", 9, "bold"),
            anchor="w",
            justify="left",
            wraplength=325,
        )
        self.lbl_msg_movimiento_titulo.place(x=16, y=136, width=330, height=18)

        self.lbl_msg_movimiento_detalle = tk.Label(
            self.frame_mensajes,
            text="",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_TEXTO,
            font=("Arial", 9),
            anchor="nw",
            justify="left",
            wraplength=325,
        )
        self.lbl_msg_movimiento_detalle.place(x=16, y=158, width=330, height=34)

        self.lbl_msg_grados = tk.Label(
            self.frame_mensajes,
            text="",
            bg=self.COLOR_PANEL,
            fg=self.COLOR_TEXTO,
            font=("Arial", 9),
            anchor="w",
            justify="left",
            wraplength=325,
        )
        self.lbl_msg_grados.place(x=16, y=213, width=330, height=22)

        self.lbl_info_extra = tk.Label(
            self.pagina_sensores,
            text="Joystick: -- | Dirección: CENTRO",
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_GRIS,
            font=("Arial", 8, "bold"),
            anchor="w",
        )
        self.lbl_info_extra.place(x=325, y=298, width=360, height=18)

        self.actualizar_panel_mensajes()

    def _crear_tarjeta_sensor(self, parent, x, y, ancho, alto, titulo):
        """Crea una tarjeta visual para los datos de sensores sin bordes rotos."""

        frame = tk.Frame(
            parent,
            bg=self.COLOR_PANEL,
            highlightthickness=1,
            highlightbackground=self.COLOR_BORDE,
            highlightcolor=self.COLOR_BORDE,
        )
        frame.place(x=x, y=y, width=ancho, height=alto)

        etiqueta_titulo = tk.Label(
            frame,
            text=titulo,
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_TEXTO,
            font=("Arial", 8, "bold"),
            anchor="center",
        )
        etiqueta_titulo.place(x=1, y=1, width=ancho - 2, height=28)

        linea_titulo = tk.Frame(frame, bg=self.COLOR_BORDE)
        linea_titulo.place(x=0, y=29, width=ancho, height=1)

        return frame

    # =========================================================================
    # COMANDOS DE LA INTERFAZ HACIA MQTT
    # =========================================================================

    def enviar_sistema_on(self):
        """
        Hace:
            Solicita al ESP32 entrar en estado OPERANDO.

        Publica:
            sistema/cmd/iniciar = on
        """

        self.sistema_activo = True
        self.estado_sistema = "Solicitando operación"
        self._actualizar_estilo_onoff()

        self._publicar_mqtt(self.T_CMD_INICIAR_OP, "on")
        self.actualizar_panel_mensajes()

    def enviar_sistema_off(self):
        """
        Hace:
            Solicita al ESP32 volver a estado ESPERA.

        Publica:
            sistema/cmd/iniciar = off
        """

        self.sistema_activo = False
        self.estado_sistema = "Solicitando espera"
        self._actualizar_estilo_onoff()

        self._publicar_mqtt(self.T_CMD_INICIAR_OP, "off")
        self.actualizar_panel_mensajes()

    def enviar_estado_seguro(self):
        """
        Hace:
            Solicita al ESP32 activar estado seguro.

        Publica:
            sistema/cmd/seguro = on
        """

        self.sistema_activo = False
        self.estado_sistema = "Solicitando estado seguro"
        self._actualizar_estilo_onoff()

        self._publicar_mqtt(self.T_CMD_SEGURO, "on")
        self.actualizar_panel_mensajes()

    def cambiar_grados(self, cambio):
        """
        Parámetros:
            cambio: cantidad de grados a aumentar o disminuir.

        Hace:
            Cambia visualmente los grados y publica el nuevo ángulo para que
            el ESP32 mueva físicamente el servomotor de la base.

        Publica:
            sistema/cmd/base/mover = <angulo>
        """

        nuevo_valor = self.grados_camara.get() + cambio
        nuevo_valor = max(self.MIN_GRADOS, min(self.MAX_GRADOS, nuevo_valor))

        self.grados_camara.set(nuevo_valor)
        self.actualizar_panel_mensajes()

        self._publicar_mqtt(self.T_CMD_BASE_MOVER, str(nuevo_valor))

    def _actualizar_estilo_onoff(self):
        """Actualiza el color visual de los botones ON/OFF."""

        if self.sistema_activo:
            self.boton_sistema_on.config(bg=self.COLOR_AZUL, fg=self.COLOR_BLANCO)
            self.boton_sistema_off.config(bg=self.COLOR_ROSA, fg=self.COLOR_TEXTO)
        else:
            self.boton_sistema_on.config(bg=self.COLOR_ROSA, fg=self.COLOR_TEXTO)
            self.boton_sistema_off.config(bg=self.COLOR_ROJO, fg=self.COLOR_BLANCO)

    # =========================================================================
    # ACTUALIZACIÓN DE DATOS RECIBIDOS DESDE ESP32
    # =========================================================================

    def actualizar_datos_esp32(
        self,
        distancia_cm=None,
        movimiento_usuario=None,
        grados_camara=None,
        estado_sistema=None,
        joystick_base=None,
        direccion_base=None,
        error_sistema=None,
    ):
        """
        Parámetros:
            distancia_cm: lectura del ultrasónico en cm.
            movimiento_usuario: lectura del PIR.
            grados_camara: ángulo real publicado por el ESP32.
            estado_sistema: estado publicado por el ESP32.
            joystick_base: valor analógico del joystick.
            direccion_base: DERECHA, IZQUIERDA o CENTRO.
            error_sistema: texto de error del ESP32.

        Hace:
            Actualiza los datos internos de la interfaz. Este método debe ser
            llamado desde mqtt_bridge.py cuando lleguen mensajes MQTT.

        Devuelve:
            Nada.
        """

        if distancia_cm is not None:
            texto_distancia = str(distancia_cm).strip()

            if texto_distancia.lower() == "null":
                self.distancia_cm = None
            else:
                try:
                    self.distancia_cm = float(texto_distancia)
                except ValueError:
                    self.distancia_cm = None

        if movimiento_usuario is not None:
            self.movimiento_usuario = movimiento_usuario

        if grados_camara is not None:
            try:
                grados = int(float(str(grados_camara).strip()))
                grados = max(self.MIN_GRADOS, min(self.MAX_GRADOS, grados))
                self.grados_camara.set(grados)
            except ValueError:
                pass

        if estado_sistema is not None:
            self.estado_sistema = str(estado_sistema)

            estado_lower = self.estado_sistema.strip().lower()

            if estado_lower == "operando":
                self.sistema_activo = True
            elif estado_lower in (
                "esperando instrucciones",
                "estado seguro",
                "error",
                "abortando",
            ):
                self.sistema_activo = False

            self._actualizar_estilo_onoff()

        if joystick_base is not None:
            self.joystick_base = str(joystick_base)

        if direccion_base is not None:
            self.direccion_base = str(direccion_base)

        if error_sistema is not None:
            self.error_sistema = str(error_sistema)

        self.actualizar_panel_mensajes()

    def actualizar_panel_mensajes(self):
        """Actualiza las lecturas y mensajes según datos actuales."""

        distancia = self.distancia_cm
        movimiento = self._normalizar_movimiento(self.movimiento_usuario)
        grados = self.grados_camara.get()

        # ---------------------------------------------------------------------
        # Lectura visual de distancia.
        # ---------------------------------------------------------------------

        if distancia is None:
            texto_distancia = "-- cm"
        else:
            texto_distancia = f"{distancia:.0f} cm"

        self.lbl_distancia_valor.config(text=texto_distancia)

        # ---------------------------------------------------------------------
        # Lectura visual de movimiento.
        # ---------------------------------------------------------------------

        self.lbl_movimiento_valor.config(text="SI" if movimiento else "NO")

        # ---------------------------------------------------------------------
        # Estado del sistema.
        # ---------------------------------------------------------------------

        self.lbl_estado_sistema.config(text=f"Estado: {self.estado_sistema}")

        estado_lower = str(self.estado_sistema).strip().lower()

        if estado_lower == "operando":
            self.lbl_estado_sistema.config(fg=self.COLOR_AZUL)
        elif estado_lower == "error":
            self.lbl_estado_sistema.config(fg=self.COLOR_ROJO)
        elif estado_lower == "estado seguro":
            self.lbl_estado_sistema.config(fg=self.COLOR_AMARILLO)
        else:
            self.lbl_estado_sistema.config(fg=self.COLOR_GRIS)

        # ---------------------------------------------------------------------
        # Mensaje por distancia.
        # ---------------------------------------------------------------------

        if distancia is None:
            titulo_dist = "• sin lectura de distancia"
            detalle_dist = "esperando conexión"
            color_dist = self.COLOR_GRIS

        elif 0 <= distancia <= 25:
            titulo_dist = f"• {distancia:.0f} cm de distancia"
            detalle_dist = "Aléjese un poco del sistema"
            color_dist = self.COLOR_ROJO

        elif 26 <= distancia <= 35:
            titulo_dist = f"• {distancia:.0f} cm de distancia"
            detalle_dist = "Distancia adecuada"
            color_dist = self.COLOR_AZUL

        elif 36 <= distancia <= 50:
            titulo_dist = f"• {distancia:.0f} cm de distancia"
            detalle_dist = "Acérquese un poco al sistema"
            color_dist = self.COLOR_AMARILLO

        elif distancia > 50:
            titulo_dist = f"• {distancia:.0f} cm de distancia"
            detalle_dist = "Acérquese un poco al sistema"
            color_dist = self.COLOR_AMARILLO

        else:
            titulo_dist = "• distancia inválida"
            detalle_dist = "revise el sensor ultrasónico"
            color_dist = self.COLOR_GRIS

        self.lbl_msg_distancia_titulo.config(text=titulo_dist, fg=color_dist)
        self.lbl_msg_distancia_detalle.config(text=detalle_dist)

        # ---------------------------------------------------------------------
        # Mensaje por movimiento.
        # ---------------------------------------------------------------------

        if movimiento:
            titulo_mov = "• Demasiado movimiento"
            detalle_mov = "Colóquese quiet@ frente a cámara"
            color_mov = self.COLOR_ROJO
        else:
            titulo_mov = "• Rigidez adecuada"
            detalle_mov = "Posición correcta, no se mueva"
            color_mov = self.COLOR_AZUL

        self.lbl_msg_movimiento_titulo.config(text=titulo_mov, fg=color_mov)
        self.lbl_msg_movimiento_detalle.config(text=detalle_mov)

        # ---------------------------------------------------------------------
        # Mensaje por grados.
        # ---------------------------------------------------------------------

        self.lbl_msg_grados.config(text=f"Grado actual de la cámara: {grados}°")

        # ---------------------------------------------------------------------
        # Información extra de joystick.
        # ---------------------------------------------------------------------

        if self.joystick_base is None:
            texto_joystick = "Joystick: --"
        else:
            texto_joystick = f"Joystick: {self.joystick_base}"

        texto_direccion = f"Dirección: {self.direccion_base}"

        self.lbl_info_extra.config(text=f"{texto_joystick} | {texto_direccion}")

        # ---------------------------------------------------------------------
        # Si hay error, mostrarlo en la parte de estado.
        # ---------------------------------------------------------------------

        if self.error_sistema:
            self.lbl_estado_sistema.config(
                text=f"Error: {self.error_sistema}",
                fg=self.COLOR_ROJO
            )

    def _normalizar_movimiento(self, valor):
        """Convierte diferentes formatos de movimiento a True/False."""

        if isinstance(valor, bool):
            return valor

        texto = str(valor).strip().lower()

        return texto in (
            "si",
            "sí",
            "s",
            "true",
            "1",
            "movimiento",
            "presencia",
        )

    def _programar_actualizacion_sensores(self):
        """Refresca mensajes de sensores cada 500 ms."""

        self.actualizar_panel_mensajes()
        self.pantalla.after(500, self._programar_actualizacion_sensores)

    # =========================================================================
    # PÁGINA CAPTURA
    # =========================================================================

    def _crear_pagina_captura(self):
        """
        Diseño de la pestaña Captura.
        Se conservan nombres, rutas y tamaños principales del diseño anterior.
        """

        self.panel_controles = tk.Frame(
            self.pagina_captura,
            bg=self.COLOR_PANEL_SUAVE,
            highlightthickness=1,
            highlightbackground=self.COLOR_PANEL,
        )
        self.panel_controles.place(x=25, y=8, width=250, height=345)

        self.etiqueta_control = tk.Label(
            self.panel_controles,
            text="CONTROLES DE VIDEO",
            font=("Calibri", 10, "bold"),
            bg=self.COLOR_PANEL_SUAVE,
            fg=self.COLOR_TEXTO,
        )
        self.etiqueta_control.place(x=0, y=8, width=250, height=18)

        # ---------------------------------------------------------------------
        # Botón abrir cámara.
        # ---------------------------------------------------------------------

        self.ruta_imagen_boton_inicio = "./Detalles_de_pantalla/abierto.png"
        self.imagen_boton_inicio = self._cargar_photoimage(
            self.ruta_imagen_boton_inicio,
            90,
            60
        )

        self.boton_inicio = self._crear_boton_con_imagen(
            self.panel_controles,
            imagen=self.imagen_boton_inicio,
            ancho=90,
            alto=60,
        )
        self.boton_inicio.place(x=25, y=34, width=90, height=60)

        # ---------------------------------------------------------------------
        # Botón cerrar cámara.
        # ---------------------------------------------------------------------

        self.ruta_imagen_boton_fin = "./Detalles_de_pantalla/cerrar.png"
        self.imagen_boton_fin = self._cargar_photoimage(
            self.ruta_imagen_boton_fin,
            90,
            60
        )

        self.boton_fin = self._crear_boton_con_imagen(
            self.panel_controles,
            imagen=self.imagen_boton_fin,
            ancho=90,
            alto=60,
        )
        self.boton_fin.place(x=135, y=34, width=90, height=60)

        # ---------------------------------------------------------------------
        # Botones grabación.
        # ---------------------------------------------------------------------

        self.ruta_imagen_boton_iniciar_grabacion = "./Detalles_de_pantalla/captura.png"
        self.imagen_boton_iniciar_grabacion = self._cargar_photoimage(
            self.ruta_imagen_boton_iniciar_grabacion,
            90,
            50,
        )

        self.boton_iniciar_grabacion = self._crear_boton_con_imagen(
            self.panel_controles,
            imagen=self.imagen_boton_iniciar_grabacion,
            ancho=90,
            alto=50,
        )
        self.boton_iniciar_grabacion.place(x=25, y=103, width=90, height=50)
        self.boton_iniciar_grabacion.config(state=tk.DISABLED)

        self.ruta_imagen_boton_detener_grabacion = "./Detalles_de_pantalla/parar.png"
        self.imagen_boton_detener_grabacion = self._cargar_photoimage(
            self.ruta_imagen_boton_detener_grabacion,
            90,
            50,
        )

        self.boton_detener_grabacion = self._crear_boton_con_imagen(
            self.panel_controles,
            imagen=self.imagen_boton_detener_grabacion,
            ancho=90,
            alto=50,
        )
        self.boton_detener_grabacion.place(x=135, y=103, width=90, height=50)
        self.boton_detener_grabacion.config(state=tk.DISABLED)

        self.etiqueta_filtro = tk.Label(
            self.panel_controles,
            text="FILTROS DE CÁMARA",
            font=("Calibri", 10, "bold"),
            bg=self.COLOR_PANEL_SUAVE,
            fg=self.COLOR_TEXTO,
        )
        self.etiqueta_filtro.place(x=0, y=162, width=250, height=18)

        # ---------------------------------------------------------------------
        # Filtros.
        # ---------------------------------------------------------------------

        self.ruta_imagen_boton_rgb = "./Detalles_de_pantalla/rgb.png"
        self.imagen_boton_rgb = self._cargar_photoimage(
            self.ruta_imagen_boton_rgb,
            200,
            40
        )

        self.boton_rgb = self._crear_boton_con_imagen(
            self.panel_controles,
            imagen=self.imagen_boton_rgb,
            ancho=200,
            alto=40,
        )
        self.boton_rgb.place(x=25, y=184, width=200, height=40)

        self.ruta_imagen_boton_grises = "./Detalles_de_pantalla/grises.png"
        self.imagen_boton_grises = self._cargar_photoimage(
            self.ruta_imagen_boton_grises,
            200,
            40
        )

        self.boton_grises = self._crear_boton_con_imagen(
            self.panel_controles,
            imagen=self.imagen_boton_grises,
            ancho=200,
            alto=40,
        )
        self.boton_grises.place(x=25, y=228, width=200, height=40)

        self.ruta_imagen_boton_canny = "./Detalles_de_pantalla/canny.png"
        self.imagen_boton_canny = self._cargar_photoimage(
            self.ruta_imagen_boton_canny,
            200,
            40
        )

        self.boton_canny = self._crear_boton_con_imagen(
            self.panel_controles,
            imagen=self.imagen_boton_canny,
            ancho=200,
            alto=40,
        )
        self.boton_canny.place(x=25, y=272, width=200, height=40)

        self.etiqueta_canny = tk.Label(
            self.panel_controles,
            text="UMBRALES CANNY",
            font=("Calibri", 8, "bold"),
            bg=self.COLOR_PANEL_SUAVE,
            fg=self.COLOR_TEXTO,
        )
        self.etiqueta_canny.place(x=0, y=316, width=250, height=12)

        self.slider_umbral_alto = tk.Scale(
            self.panel_controles,
            from_=0,
            to=255,
            orient=tk.HORIZONTAL,
            bg=self.COLOR_PANEL_SUAVE,
            troughcolor=self.COLOR_ROSA,
            highlightthickness=0,
            showvalue=0,
            borderwidth=0,
            sliderlength=18,
        )
        self.slider_umbral_alto.place(x=23, y=326, width=93, height=18)

        self.slider_umbral_bajo = tk.Scale(
            self.panel_controles,
            from_=0,
            to=255,
            orient=tk.HORIZONTAL,
            bg=self.COLOR_PANEL_SUAVE,
            troughcolor=self.COLOR_ROSA,
            highlightthickness=0,
            showvalue=0,
            borderwidth=0,
            sliderlength=18,
        )
        self.slider_umbral_bajo.place(x=134, y=326, width=93, height=18)

        # ---------------------------------------------------------------------
        # Video.
        # ---------------------------------------------------------------------

        self.etiqueta_video = tk.Label(
            self.pagina_captura,
            text="VIDEO EN TIEMPO REAL",
            font=("Calibri", 10, "bold"),
            bg=self.COLOR_BLANCO,
            fg=self.COLOR_TEXTO,
        )
        self.etiqueta_video.place(x=330, y=18, width=340, height=18)

        self.lblVideo = tk.Label(
            self.pagina_captura,
            bg="black",
            highlightthickness=2,
            highlightbackground=self.COLOR_PANEL,
        )
        self.lblVideo.place(
            x=320,
            y=44,
            width=self.VIDEO_ANCHO,
            height=self.VIDEO_ALTO
        )

        # ---------------------------------------------------------------------
        # Botones inferiores.
        # Solo estos tienen texto visible.
        # ---------------------------------------------------------------------

        self.boton_ia = tk.Button(
            self.pagina_captura,
            text="Activar IA",
            width=165,
            height=35,
            font=("Calibri", 9, "bold"),
            bg=self.COLOR_ROSA,
            fg=self.COLOR_TEXTO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_TEXTO,
            relief="solid",
            bd=1,
            cursor="hand2",
        )
        self.boton_ia.place(x=320, y=320, width=165, height=35)

        self.boton_extraer_frames = tk.Button(
            self.pagina_captura,
            text="Extraer Frames",
            width=165,
            height=35,
            font=("Calibri", 9, "bold"),
            bg=self.COLOR_ROSA,
            fg=self.COLOR_TEXTO,
            activebackground=self.COLOR_ROSA_ACTIVO,
            activeforeground=self.COLOR_TEXTO,
            relief="solid",
            bd=1,
            cursor="hand2",
        )
        self.boton_extraer_frames.place(x=515, y=320, width=165, height=35)

    # =========================================================================
    # UTILIDADES DE IMAGEN / VIDEO
    # =========================================================================

    def _cargar_photoimage(self, ruta, ancho=None, alto=None):
        """
        Carga una imagen de botón y la ajusta al tamaño indicado.
        Si la imagen no existe, devuelve None.
        """

        if not os.path.exists(ruta):
            return None

        try:
            imagen = Image.open(ruta)

            if ancho is not None and alto is not None:
                try:
                    remuestreo = Image.Resampling.LANCZOS
                except AttributeError:
                    remuestreo = Image.LANCZOS

                imagen.thumbnail(
                    (max(1, ancho - 8), max(1, alto - 8)),
                    remuestreo
                )

            return ImageTk.PhotoImage(imagen)

        except Exception:
            return None

    def _crear_boton_con_imagen(self, parent, imagen, ancho, alto, texto=""):
        """Crea un botón con imagen si existe; si no existe, usa texto."""

        if imagen is not None:
            boton = tk.Button(
                parent,
                image=imagen,
                width=ancho,
                height=alto,
                bg=self.COLOR_ROSA,
                activebackground=self.COLOR_ROSA_ACTIVO,
                relief="solid",
                bd=1,
                cursor="hand2",
            )
        else:
            boton = tk.Button(
                parent,
                text=texto,
                width=ancho,
                height=alto,
                font=("Calibri", 8, "bold"),
                bg=self.COLOR_ROSA,
                activebackground=self.COLOR_ROSA_ACTIVO,
                relief="solid",
                bd=1,
                cursor="hand2",
                wraplength=ancho - 10,
            )

        return boton

    def ajustar_frame_video(self, frame):
        """Redimensiona el frame de OpenCV al tamaño del recuadro de video."""

        frame = cv2.resize(frame, (360, 270))
        return frame

    def mostrar_frame_en_pantalla(self, frame):
        """Convierte y muestra un frame de OpenCV en el Label de video."""

        frame = cv2.resize(frame, (360, 270))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        imagen = Image.fromarray(frame)
        imagen = ImageTk.PhotoImage(image=imagen)

        self.lblVideo.configure(image=imagen)
        self.lblVideo.image = imagen

    # =========================================================================
    # LOOP PRINCIPAL
    # =========================================================================

    def iniciar(self):
        """Inicia el loop principal de Tkinter."""

        self.pantalla.mainloop()


# =============================================================================
# PRUEBA DIRECTA DE LA INTERFAZ
# =============================================================================

if __name__ == "__main__":
    app = VistaPantalla(modelo_pantalla)

    # Publicador de prueba para revisar que los botones sí generan comandos.
    # Cuando conectemos mqtt_bridge.py, esta función se reemplaza por bridge.publicar.
    def publicar_prueba(topico, mensaje):
        print("PUBLICAR MQTT:", topico, mensaje)

    app.configurar_publicador_mqtt(publicar_prueba)
    app.iniciar()
    
