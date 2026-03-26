"""
Routes de etiquetado del árbol de decisión.
Blueprint: /api/labeling/
"""

import io
import cv2
import numpy as np
from flask import Blueprint, jsonify, request, send_file
from backend.services.labeling_service import (
    get_pair_ids, get_pair_detections, get_pair_labels,
    save_pair_labels, get_summary_stats, get_pair_summary,
    find_pair_images, get_labeled_pair_ids, load_raw, get_resume_index,
)

labeling_bp = Blueprint('labeling', __name__, url_prefix='/api/labeling')

# Colores para dibujar bboxes
COLORS = {
    "flor": (50, 205, 50),     # verde
    "planta": (255, 165, 0),   # naranja
}


@labeling_bp.route('/pairs')
def api_pairs():
    """Lista de pair_ids con estado (etiquetado/pendiente)."""
    pair_ids = get_pair_ids()
    if not pair_ids:
        return jsonify({"pairs": [], "error": "No se encontró detections_raw.csv o está vacío"})

    labeled = get_labeled_pair_ids()
    pairs = []
    for pid in pair_ids:
        pairs.append({
            "id": pid,
            "labeled": pid in labeled,
        })

    return jsonify({
        "pairs": pairs,
        "total": len(pairs),
        "labeled_count": len(labeled),
    })


@labeling_bp.route('/pair/<pair_id>')
def api_pair(pair_id):
    """Detecciones + etiquetas + info de imagen de un par."""
    detections = get_pair_detections(pair_id)
    labels = get_pair_labels(pair_id)
    images = find_pair_images(pair_id)

    pair_ids = get_pair_ids()
    idx = pair_ids.index(pair_id) if pair_id in pair_ids else -1

    return jsonify({
        "pair_id": pair_id,
        "index": idx,
        "total_pairs": len(pair_ids),
        "detections": detections,
        "labels": labels,
        "has_frontal": images["frontal"] is not None,
        "has_trasera": images["trasera"] is not None,
    })


@labeling_bp.route('/pair/<pair_id>/labels', methods=['POST'])
def api_save_labels(pair_id):
    """Guardar conteos: body = {"counts": {detection_id: count}}"""
    data = request.get_json()
    counts = data.get("counts", {})

    # Convertir claves a int
    counts_int = {int(k): int(v) for k, v in counts.items()}

    save_pair_labels(pair_id, counts_int)
    return jsonify({"success": True})


@labeling_bp.route('/pair/<pair_id>/image/<vista>')
def api_pair_image(pair_id, vista):
    """
    Imagen F/B con bboxes dibujadas.
    vista: 'frontal' o 'trasera'
    Query params: counts (JSON) para mostrar badges de conteo
    """
    images = find_pair_images(pair_id)
    img_path = images.get(vista)

    if not img_path:
        return jsonify({"error": f"Imagen {vista} no encontrada para par {pair_id}"}), 404

    img = cv2.imread(img_path)
    if img is None:
        return jsonify({"error": "No se pudo leer la imagen"}), 500

    # Nota: NO flipear la imagen trasera. Las coordenadas raw_bbox son
    # nativas de la imagen original sin transformar.

    # Dibujar bboxes
    detections = get_pair_detections(pair_id)
    labels = get_pair_labels(pair_id)

    # Parsear counts del query param si se proporcionan
    counts_param = request.args.get("counts")
    if counts_param:
        import json
        try:
            counts = {int(k): int(v) for k, v in json.loads(counts_param).items()}
        except Exception:
            counts = labels
    else:
        counts = labels

    vista_code = "F" if vista == "frontal" else "B"

    ALPHA = 0.4  # 40% opacidad del fondo → 60% transparencia

    for det in detections:
        if det["d_vista"] != vista_code:
            continue

        tipo = det["d_tipo"]
        color = COLORS.get(tipo, (200, 200, 200))
        x1 = int(det.get("raw_bbox_x1", det["d_bbox_x1"]))
        y1 = int(det.get("raw_bbox_y1", det["d_bbox_y1"]))
        x2 = int(det.get("raw_bbox_x2", det["d_bbox_x2"]))
        y2 = int(det.get("raw_bbox_y2", det["d_bbox_y2"]))
        did = det["detection_id"]
        n_units = counts.get(did, 0)

        # Bbox (siempre opaco, es solo el borde)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

        # ID grande en el centro — fondo semitransparente
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        label = str(did)
        font_scale = max(1.5, min(3.0, (x2 - x1) / 80))
        thickness = max(2, int(font_scale * 2))
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

        # Rectángulo semitransparente para el ID
        rx1, ry1 = cx - tw // 2 - 6, cy - th // 2 - 6
        rx2, ry2 = cx + tw // 2 + 6, cy + th // 2 + 6
        rx1, ry1 = max(0, rx1), max(0, ry1)
        rx2, ry2 = min(img.shape[1], rx2), min(img.shape[0], ry2)
        overlay = img[ry1:ry2, rx1:rx2].copy()
        cv2.rectangle(img, (rx1, ry1), (rx2, ry2), (0, 0, 0), -1)
        img[ry1:ry2, rx1:rx2] = cv2.addWeighted(overlay, 1 - ALPHA, img[ry1:ry2, rx1:rx2], ALPHA, 0)
        cv2.putText(img, label, (cx - tw // 2, cy + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)

        # Badge con conteo — fondo semitransparente
        if n_units > 0:
            badge = f"x{n_units}"
            (bw, bh), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            bx1, by1 = x2 - bw - 10, y1
            bx2, by2 = x2, y1 + bh + 10
            bx1, by1 = max(0, bx1), max(0, by1)
            bx2, by2 = min(img.shape[1], bx2), min(img.shape[0], by2)
            overlay_b = img[by1:by2, bx1:bx2].copy()
            cv2.rectangle(img, (bx1, by1), (bx2, by2), (0, 0, 255), -1)
            img[by1:by2, bx1:bx2] = cv2.addWeighted(overlay_b, 1 - ALPHA, img[by1:by2, bx1:bx2], ALPHA, 0)
            cv2.putText(img, badge, (bx1 + 5, by1 + bh + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

    # Encode a PNG y devolver
    _, buffer = cv2.imencode('.png', img)
    return send_file(
        io.BytesIO(buffer.tobytes()),
        mimetype='image/png',
        download_name=f'{pair_id}_{vista}.png'
    )


@labeling_bp.route('/summary')
def api_summary():
    """Estadísticas globales."""
    stats = get_summary_stats()
    return jsonify(stats)


@labeling_bp.route('/pair/<pair_id>/summary')
def api_pair_summary(pair_id):
    """Tabla de detecciones de un par con labels."""
    rows = get_pair_summary(pair_id)
    return jsonify({"rows": rows, "pair_id": pair_id})


@labeling_bp.route('/resume')
def api_resume():
    """Índice del par donde continuar el etiquetado."""
    idx = get_resume_index()
    return jsonify({"resume_index": idx})
