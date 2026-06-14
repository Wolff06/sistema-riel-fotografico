# -*- coding: utf-8 -*-
# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/raspberry/interfaz/controlador_pantalla.py
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# OBJETIVO:
# Conectar botones de la interfaz con camara, filtros, grabacion e IA.
# Este controlador respeta el bloqueo:
# - Sensores ON impide entrar a Captura.
# - IA activa impide volver a Sensores hasta apagar IA.
# =============================================================================

import tkinter as tk


class ControladorPantalla:
    """Controlador MVC de la pantalla CANMA."""

    def __init__(self, modelo, vista):
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
        self.vista.boton_ia.config(command=self.alternar_ia_completo)
        self.vista.boton_extraer_frames.config(command=self.extraer_frames)

        self.vista.boton_fin.config(state=tk.DISABLED)
        self.vista.boton_iniciar_grabacion.config(state=tk.DISABLED)
        self.vista.boton_detener_grabacion.config(state=tk.DISABLED)
        self.vista.boton_ia.config(state=tk.DISABLED)

    def activar_camara(self):
        """Abre camara solo si Sensores esta apagado."""
        if self.vista.sensores_activos:
            self.vista.mostrar_aviso("Primero apaga Sensores con OFF")
            return
        if self.vista.modo_actual != "captura":
            self.vista.mostrar_aviso("Entra a Captura para abrir la camara")
            return
        if self.modelo.activar_camara():
            self.vista.boton_inicio.config(state=tk.DISABLED)
            self.vista.boton_fin.config(state=tk.NORMAL)
            self.vista.boton_iniciar_grabacion.config(state=tk.NORMAL)
            self.vista.boton_ia.config(state=tk.NORMAL)
            self.vista.boton_detener_grabacion.config(state=tk.DISABLED)
            self.vista.estado_sistema = "Camara activa"
            self.vista.actualizar_panel_mensajes()
        else:
            self.vista.mostrar_aviso("No se pudo abrir la camara")

    def desactivar_camara(self):
        """Apaga camara e IA antes de cerrar Captura."""
        if self.vista.ia_activa:
            self._apagar_ia()
        self.modelo.desactivar_camara()
        self.vista.boton_fin.config(state=tk.DISABLED)
        self.vista.boton_inicio.config(state=tk.NORMAL)
        self.vista.boton_iniciar_grabacion.config(state=tk.DISABLED)
        self.vista.boton_detener_grabacion.config(state=tk.DISABLED)
        self.vista.boton_ia.config(state=tk.DISABLED)
        self.vista.estado_sistema = "Camara apagada"
        self.vista.actualizar_panel_mensajes()

    def iniciar_grabacion(self):
        """Inicia grabacion de video."""
        if self.modelo.iniciar_grabacion():
            self.vista.boton_iniciar_grabacion.config(state=tk.DISABLED)
            self.vista.boton_fin.config(state=tk.DISABLED)
            self.vista.boton_detener_grabacion.config(state=tk.NORMAL)

    def detener_grabacion(self):
        """Detiene grabacion de video."""
        self.modelo.detener_grabacion()
        self.vista.boton_iniciar_grabacion.config(state=tk.NORMAL)
        self.vista.boton_fin.config(state=tk.NORMAL)
        self.vista.boton_detener_grabacion.config(state=tk.DISABLED)

    def filtro_rgb(self):
        self.modelo.filtro_rgb()

    def filtro_gray(self):
        self.modelo.filtro_gray()

    def filtro_canny(self):
        self.modelo.filtro_canny()

    def alternar_ia_completo(self):
        """Activa o desactiva IA y publica el modo correcto al ESP32."""
        if self.vista.sensores_activos:
            self.vista.mostrar_aviso("Primero apaga Sensores con OFF")
            return

        if not self.vista.ia_activa:
            if self.modelo.camara is None:
                if not self.modelo.activar_camara():
                    self.vista.mostrar_aviso("No se pudo abrir la camara")
                    return
                self.vista.boton_inicio.config(state=tk.DISABLED)
                self.vista.boton_fin.config(state=tk.NORMAL)
                self.vista.boton_iniciar_grabacion.config(state=tk.NORMAL)
                self.vista.boton_ia.config(state=tk.NORMAL)

            if self.modelo.activar_clasificador():
                self.vista.activar_ia_desde_controlador()
            else:
                self.vista.mostrar_aviso("No se pudo activar IA. Revisa ultralytics o best.pt")
        else:
            self._apagar_ia()

    def _apagar_ia(self):
        """Apaga IA del modelo, interfaz y ESP32."""
        self.modelo.desactivar_clasificador(publicar=True)
        self.vista.desactivar_ia_desde_controlador()

    def extraer_frames(self):
        """Selecciona un video y extrae frames."""
        self.modelo.seleccionar_video()
