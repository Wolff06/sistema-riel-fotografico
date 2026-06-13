
# =============================================================================
# PROYECTO: CANMA - Garra Robotica con Camara e IA
# ARCHIVO: sistema/raspberry/firebase/dashboard_firebase_mqtt.py
#
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# OBJETIVO:
# Mostrar un dashboard tipo app para la entrega E4. Lee el estado actual y las
# ultimas alertas desde Firestore, y permite controlar actuadores por MQTT.
# =============================================================================

import json
import os
import tkinter as tk
from tkinter import messagebox

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    firebase_admin = None
    credentials = None
    firestore = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUTA_CREDENCIAL_FIREBASE = os.environ.get(
    "CANMA_FIREBASE_CRED",
    os.path.join(BASE_DIR, "credenciales", "firebase_key.json")
)

BROKER_HOST = os.environ.get("CANMA_MQTT_HOST", "192.168.4.1")
BROKER_PORT = int(os.environ.get("CANMA_MQTT_PORT", "1884"))
BROKER_USER = os.environ.get("CANMA_MQTT_USER", "admin")
BROKER_PASS = os.environ.get("CANMA_MQTT_PASS", "123")

INTERVALO_REFRESCO_MS = int(os.environ.get("CANMA_DASHBOARD_REFRESCO_MS", "30000"))

T_CMD_BASE_MOVER = "sistema/cmd/base/mover"
T_CMD_BRAZO_MOVER = "sistema/cmd/brazo/mover"
T_CMD_SEGURO = "sistema/cmd/seguro"
T_CMD_IA_ESTADO = "sistema/cmd/ia/estado"
T_CMD_FIREBASE_GUARDAR_IA = "sistema/cmd/firebase/guardar_ia"


class DashboardFirebaseCANMA:
    """Dashboard de monitoreo y control remoto para E4."""

    def __init__(self):
        self.db = self._inicializar_firebase()
        self.mqtt = self._crear_cliente_mqtt()

        self.ventana = tk.Tk()
        self.ventana.title("CANMA - Dashboard Firebase E4")
        self.ventana.geometry("760x520")
        self.ventana.configure(bg="#ffffff")

        self.valor_base = tk.IntVar(value=90)
        self.valor_brazo = tk.IntVar(value=90)

        self._crear_interfaz()
        self._conectar_mqtt()
        self.actualizar_dashboard()

    def _inicializar_firebase(self):
        """
        Recibe:
            Nada.

        Hace:
            Inicializa firebase-admin para leer Firestore.

        Devuelve:
            Cliente Firestore.
        """

        if firebase_admin is None:
            raise ImportError("Falta firebase-admin. Instala con: python3 -m pip install firebase-admin")

        if not os.path.exists(RUTA_CREDENCIAL_FIREBASE):
            raise FileNotFoundError(
                "No se encontro la credencial Firebase en: {}".format(RUTA_CREDENCIAL_FIREBASE)
            )

        if not firebase_admin._apps:
            credencial = credentials.Certificate(RUTA_CREDENCIAL_FIREBASE)
            firebase_admin.initialize_app(credencial)

        return firestore.client()

    def _crear_cliente_mqtt(self):
        """
        Recibe:
            Nada.

        Hace:
            Crea cliente MQTT para enviar comandos remotos al ESP32.

        Devuelve:
            Cliente MQTT configurado.
        """

        if mqtt is None:
            raise ImportError("Falta paho-mqtt. Instala con: python3 -m pip install paho-mqtt")

        try:
            cliente = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                client_id="canma_dashboard_firebase"
            )
        except Exception:
            cliente = mqtt.Client(client_id="canma_dashboard_firebase")

        if BROKER_USER:
            cliente.username_pw_set(BROKER_USER, BROKER_PASS)

        return cliente

    def _conectar_mqtt(self):
        """
        Recibe:
            Nada.

        Hace:
            Conecta el dashboard al broker Mosquitto.

        Devuelve:
            Nada.
        """

        try:
            self.mqtt.connect(BROKER_HOST, BROKER_PORT, 60)
            self.mqtt.loop_start()
        except Exception as error:
            messagebox.showwarning("MQTT", "No se pudo conectar a Mosquitto: {}".format(error))

    def _crear_interfaz(self):
        """Crea etiquetas, paneles y botones del dashboard."""

        tk.Label(
            self.ventana,
            text="CANMA - Dashboard Firebase E4",
            bg="#ffffff",
            fg="#111111",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        self.frame_estado = tk.LabelFrame(
            self.ventana,
            text="Estado actual del sistema",
            bg="#ffffff",
            font=("Arial", 10, "bold")
        )
        self.frame_estado.place(x=20, y=60, width=350, height=210)

        self.lbl_estado = tk.Label(self.frame_estado, text="Estado: --", bg="#ffffff", anchor="w")
        self.lbl_estado.place(x=10, y=10, width=320, height=22)

        self.lbl_pir = tk.Label(self.frame_estado, text="PIR: --", bg="#ffffff", anchor="w")
        self.lbl_pir.place(x=10, y=38, width=320, height=22)

        self.lbl_ultrasonico = tk.Label(self.frame_estado, text="Ultrasonico: -- cm", bg="#ffffff", anchor="w")
        self.lbl_ultrasonico.place(x=10, y=66, width=320, height=22)

        self.lbl_joystick = tk.Label(self.frame_estado, text="Joystick: -- | Direccion: --", bg="#ffffff", anchor="w")
        self.lbl_joystick.place(x=10, y=94, width=320, height=22)

        self.lbl_ia = tk.Label(self.frame_estado, text="IA: --", bg="#ffffff", anchor="w")
        self.lbl_ia.place(x=10, y=122, width=320, height=22)

        self.lbl_timestamp = tk.Label(self.frame_estado, text="Actualizado: --", bg="#ffffff", anchor="w")
        self.lbl_timestamp.place(x=10, y=150, width=320, height=22)

        self.frame_alertas = tk.LabelFrame(
            self.ventana,
            text="Ultimas 5 alertas",
            bg="#ffffff",
            font=("Arial", 10, "bold")
        )
        self.frame_alertas.place(x=390, y=60, width=350, height=210)

        self.txt_alertas = tk.Text(self.frame_alertas, wrap="word", height=8, bg="#fafafa")
        self.txt_alertas.place(x=10, y=10, width=325, height=165)

        self.frame_control = tk.LabelFrame(
            self.ventana,
            text="Control remoto de actuadores por MQTT",
            bg="#ffffff",
            font=("Arial", 10, "bold")
        )
        self.frame_control.place(x=20, y=290, width=720, height=180)

        tk.Label(self.frame_control, text="Base", bg="#ffffff").place(x=15, y=20, width=60, height=25)
        tk.Scale(self.frame_control, from_=0, to=180, orient=tk.HORIZONTAL, variable=self.valor_base, bg="#ffffff").place(x=80, y=10, width=230, height=50)
        tk.Button(self.frame_control, text="Mover base", command=self.mover_base).place(x=320, y=18, width=120, height=28)

        tk.Label(self.frame_control, text="Brazo", bg="#ffffff").place(x=15, y=75, width=60, height=25)
        tk.Scale(self.frame_control, from_=0, to=180, orient=tk.HORIZONTAL, variable=self.valor_brazo, bg="#ffffff").place(x=80, y=65, width=230, height=50)
        tk.Button(self.frame_control, text="Mover brazo", command=self.mover_brazo).place(x=320, y=73, width=120, height=28)

        tk.Button(self.frame_control, text="Estado seguro", command=self.estado_seguro).place(x=475, y=18, width=180, height=28)
        tk.Button(self.frame_control, text="Activar IA", command=lambda: self.publicar(T_CMD_IA_ESTADO, "on")).place(x=475, y=58, width=85, height=28)
        tk.Button(self.frame_control, text="Apagar IA", command=lambda: self.publicar(T_CMD_IA_ESTADO, "off")).place(x=570, y=58, width=85, height=28)
        tk.Button(self.frame_control, text="Guardar ultima deteccion IA", command=self.guardar_ultima_ia).place(x=475, y=98, width=180, height=28)

        tk.Button(self.ventana, text="Actualizar ahora", command=self.actualizar_dashboard).place(x=300, y=480, width=160, height=28)

    def publicar(self, topico, mensaje):
        """
        Recibe:
            topico: topico MQTT.
            mensaje: mensaje para publicar.

        Hace:
            Publica un comando al broker Mosquitto.

        Devuelve:
            Nada.
        """

        try:
            self.mqtt.publish(topico, str(mensaje))
            print("Dashboard publico:", topico, mensaje)
        except Exception as error:
            messagebox.showerror("MQTT", "No se pudo publicar: {}".format(error))

    def mover_base(self):
        """Mueve el servo de base al angulo seleccionado."""
        self.publicar(T_CMD_BASE_MOVER, self.valor_base.get())

    def mover_brazo(self):
        """Mueve el servo de brazo al angulo seleccionado."""
        self.publicar(T_CMD_BRAZO_MOVER, self.valor_brazo.get())

    def estado_seguro(self):
        """Solicita estado seguro al ESP32."""
        self.publicar(T_CMD_SEGURO, "on")

    def guardar_ultima_ia(self):
        """Solicita al gateway guardar la ultima deteccion IA sin imagen."""
        self.publicar(T_CMD_FIREBASE_GUARDAR_IA, "guardar")

    def actualizar_dashboard(self):
        """
        Recibe:
            Nada.

        Hace:
            Lee Firestore y actualiza los paneles del dashboard.

        Devuelve:
            Nada.
        """

        try:
            doc = self.db.collection("estado_actual").document("sistema").get()
            datos = doc.to_dict() or {}
            self._pintar_estado(datos)
            self._pintar_alertas()
        except Exception as error:
            print("Error leyendo Firestore:", error)

        self.ventana.after(INTERVALO_REFRESCO_MS, self.actualizar_dashboard)

    def _pintar_estado(self, datos):
        """Pinta el documento estado_actual/sistema."""

        sensores = datos.get("sensores", {}) or {}
        actuadores = datos.get("actuadores", {}) or {}
        ia = datos.get("ia", {}) or {}

        self.lbl_estado.config(text="Estado: {}".format(datos.get("sistema", "--")))
        self.lbl_pir.config(text="PIR: {}".format(sensores.get("pir", "--")))
        self.lbl_ultrasonico.config(text="Ultrasonico: {} cm".format(sensores.get("ultrasonico_cm", "--")))
        self.lbl_joystick.config(
            text="Joystick: {} | Direccion: {}".format(
                sensores.get("joystick_base", "--"),
                sensores.get("direccion_base", "--")
            )
        )
        self.lbl_ia.config(
            text="IA: {} | {} | confianza {}".format(
                ia.get("lectura", "--"),
                ia.get("clase", "--"),
                ia.get("confianza", "--")
            )
        )
        self.lbl_timestamp.config(text="Actualizado: {}".format(datos.get("timestamp_local", "--")))

        try:
            base = actuadores.get("base_grados")
            if base is not None:
                self.valor_base.set(int(float(base)))
        except Exception:
            pass

        try:
            brazo = actuadores.get("brazo_grados")
            if brazo is not None:
                self.valor_brazo.set(int(float(brazo)))
        except Exception:
            pass

    def _pintar_alertas(self):
        """Lee y muestra las ultimas 5 alertas."""

        self.txt_alertas.delete("1.0", tk.END)

        try:
            consulta = (
                self.db.collection("alertas")
                .order_by("timestamp_servidor", direction=firestore.Query.DESCENDING)
                .limit(5)
                .stream()
            )

            contador = 0
            for alerta in consulta:
                contador += 1
                datos = alerta.to_dict() or {}
                linea = "{}. [{}] {}\n".format(
                    contador,
                    datos.get("timestamp_local", "--"),
                    datos.get("mensaje", "Sin mensaje")
                )
                self.txt_alertas.insert(tk.END, linea)

            if contador == 0:
                self.txt_alertas.insert(tk.END, "Sin alertas registradas")

        except Exception as error:
            self.txt_alertas.insert(tk.END, "No se pudieron leer alertas: {}".format(error))

    def iniciar(self):
        """Inicia la app Tkinter."""
        try:
            self.ventana.mainloop()
        finally:
            try:
                self.mqtt.loop_stop()
                self.mqtt.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    app = DashboardFirebaseCANMA()
    app.iniciar()
