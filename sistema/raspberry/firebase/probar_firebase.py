# =============================================================================
# PROYECTO: CANMA
# ARCHIVO: probar_firebase.py
#
# - INTREGANTES -
# Macias Campos Ariadne Lizett
# Soto Garnica Ari Adair
# Lira Gamiño Luis Fernando
#
# DESCRIPCION:
# Prueba simple de conexion entre Raspberry Pi y Firebase Firestore.
# =============================================================================

import os
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_CREDENCIAL = os.path.join(BASE_DIR, "credenciales", "firebase_key.json")


def inicializar_firebase():
    """
    Recibe:
        Nada.

    Hace:
        Inicializa Firebase usando el archivo de credenciales JSON.

    Devuelve:
        Cliente de Firestore.
    """

    if not os.path.exists(RUTA_CREDENCIAL):
        raise FileNotFoundError(
            "No se encontro la credencial Firebase en: " + RUTA_CREDENCIAL
        )

    if not firebase_admin._apps:
        credencial = credentials.Certificate(RUTA_CREDENCIAL)
        firebase_admin.initialize_app(credencial)

    return firestore.client()


def probar_escritura():
    """
    Recibe:
        Nada.

    Hace:
        Escribe un documento de prueba en Firestore y actualiza el estado actual.

    Devuelve:
        Nada.
    """

    db = inicializar_firebase()

    datos_prueba = {
        "tipo": "prueba_conexion",
        "origen": "raspberry_pi",
        "mensaje": "Conexion correcta entre Raspberry Pi y Firestore",
        "timestamp_local": datetime.now().isoformat(timespec="seconds"),
        "timestamp_firebase": SERVER_TIMESTAMP
    }

    referencia_evento = db.collection("canma_eventos").document()
    referencia_evento.set(datos_prueba)

    db.collection("canma_estado").document("actual").set({
        "estado": "firebase_conectado",
        "ultimo_evento": "prueba_conexion",
        "timestamp_local": datetime.now().isoformat(timespec="seconds"),
        "timestamp_firebase": SERVER_TIMESTAMP
    }, merge=True)

    print("Conexion correcta.")
    print("Documento creado en canma_eventos con ID:", referencia_evento.id)
    print("Documento actualizado: canma_estado/actual")


if __name__ == "__main__":
    probar_escritura()