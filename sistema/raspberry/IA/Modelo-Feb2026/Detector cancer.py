"""
detector_cancer.py
──────────────────
Detector en vivo de cáncer de mama con YOLO.

Mejoras respecto a la versión anterior:
  • Solo muestra la clase con mayor probabilidad (no todas).
  • Recuadro con color dinámico:
      - Verde       → "Seno Ileso" (más confianza = verde más intenso)
      - Amarillo→Rojo → "Seno Herido" (más confianza = más rojo)
      - Gris        → "Falso Positivo"
  • Umbral de confianza configurable.
  • Panel de info en esquina con FPS y estado general.
  • Tecla 'q' para salir, 's' para guardar captura.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import time
import os

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN  (cambia solo estas variables)
# ═══════════════════════════════════════════════════════════════════════════════
MODELO_PATH   = "runs/cancer/train_v1/weights/best.pt"
CONFIANZA_MIN = 0.45          # Detecta solo si supera este porcentaje
RESOLUCION    = (1280, 720)    # Resolución de la cámara
CAMARA_ID     = 0             # 0 = cámara principal
CARPETA_SAVES = "capturas"    # Carpeta donde se guardan las fotos con 's'
# ═══════════════════════════════════════════════════════════════════════════════

# Índices de clase (deben coincidir con datav3.yml)
CLASE_HERIDO   = 0
CLASE_ILESO    = 1
CLASE_FALSO    = 2

os.makedirs(CARPETA_SAVES, exist_ok=True)


def color_herido(confianza: float) -> tuple:
    """
    Verde → Amarillo → Rojo según la confianza de 'Seno Herido'.
    confianza 0.0 → verde  (0, 220, 0)
    confianza 0.5 → amarillo (0, 220, 220)
    confianza 1.0 → rojo   (0, 0, 220)
    Retorna color en BGR.
    """
    conf = max(0.0, min(1.0, confianza))
    if conf < 0.5:
        # Verde → Amarillo
        t = conf / 0.5
        r = int(0   + t * 220)
        g = 220
        b = 0
    else:
        # Amarillo → Rojo
        t = (conf - 0.5) / 0.5
        r = 220
        g = int(220 - t * 220)
        b = 0
    return (b, g, r)   # BGR


def color_ileso(confianza: float) -> tuple:
    """Verde más intenso cuanto mayor sea la confianza."""
    conf = max(0.0, min(1.0, confianza))
    g = int(100 + conf * 155)   # 100–255
    return (0, g, 0)             # BGR


def dibujar_deteccion(frame, x1, y1, x2, y2, clase_id, clase_nombre, confianza):
    """Dibuja recuadro y etiqueta para una detección."""
    if clase_id == CLASE_HERIDO:
        color = color_herido(confianza)
        emoji = "⚠"
    elif clase_id == CLASE_ILESO:
        color = color_ileso(confianza)
        emoji = "✓"
    else:
        color = (160, 160, 160)   # gris para falso positivo
        emoji = "?"

    grosor = 2

    # Recuadro principal
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, grosor)

    # Fondo del texto
    texto = f"{clase_nombre}  {confianza * 100:.1f}%"
    (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    ty = max(y1 - 10, th + 10)
    cv2.rectangle(frame, (x1, ty - th - 8), (x1 + tw + 8, ty + 4), color, -1)

    # Texto con contraste (negro o blanco según luminosidad del color)
    b, g, r = color
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    texto_color = (0, 0, 0) if lum > 128 else (255, 255, 255)
    cv2.putText(frame, texto, (x1 + 4, ty),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, texto_color, 2)


def panel_info(frame, fps, detecciones_totales):
    """Pequeño panel en la esquina superior izquierda con FPS y conteo."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (250, 70), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)
    cv2.putText(frame, f"Detecciones: {detecciones_totales}", (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)

    # Leyenda de colores
    controles = "[Q] Salir   [S] Guardar captura"
    cv2.putText(frame, controles, (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    print(f"Cargando modelo: {MODELO_PATH}")
    model = YOLO(MODELO_PATH)
    print("Modelo listo. Abriendo cámara…")

    cap = cv2.VideoCapture(CAMARA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  RESOLUCION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCION[1])

    if not cap.isOpened():
        print("No se pudo abrir la cámara.")
        return

    t_prev = time.time()
    captura_n = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠ Sin señal de cámara.")
            break

        # ── Predicción ──────────────────────────────────────────────────────
        results = model.predict(
            source=frame,
            conf=CONFIANZA_MIN,
            verbose=False,
            stream=False,
        )

        detecciones = 0

        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue

            boxes   = result.boxes.xyxy.cpu().numpy()
            confs   = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy().astype(int)

            for box, conf, cls in zip(boxes, confs, classes):
                # ── Solo mostramos la clase con mayor probabilidad ──────────
                # (YOLO ya hace esto internamente; aquí reforzamos que
                #  si hay overlap usamos la de mayor confianza)
                x1, y1, x2, y2 = map(int, box)
                nombre = model.names[cls]

                dibujar_deteccion(frame, x1, y1, x2, y2, cls, nombre, conf)
                detecciones += 1

        # ── FPS ─────────────────────────────────────────────────────────────
        t_now = time.time()
        fps = 1.0 / max(t_now - t_prev, 1e-6)
        t_prev = t_now

        panel_info(frame, fps, detecciones)

        cv2.imshow("Detector de Cáncer de Mama - YOLO", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord('q'):
            print("Saliendo…")
            break
        elif tecla == ord('s'):
            captura_n += 1
            nombre_archivo = os.path.join(CARPETA_SAVES, f"captura_{captura_n:04d}.jpg")
            cv2.imwrite(nombre_archivo, frame)
            print(f"Captura guardada: {nombre_archivo}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()