"""
cropping_service.py — Extrae crops de imágenes desde export Roboflow COCO.
Adaptado de 01_cropping.py para aceptar parámetros dinámicos.
"""

import os
import json
import cv2
from backend.config import EXCLUDE_CATEGORY_IDS, MIN_CROP_SIZE, DEFAULT_SPLITS


def process_split(roboflow_dir, split, output_dir, target_names,
                  min_crop_size=MIN_CROP_SIZE, crop_id_start=0,
                  exclude_ids=None):
    """
    Procesa un split individual de Roboflow.
    Las imágenes están DENTRO de la carpeta del split junto al JSON.
    """
    if exclude_ids is None:
        exclude_ids = EXCLUDE_CATEGORY_IDS

    split_dir = os.path.join(roboflow_dir, split)
    json_path = os.path.join(split_dir, "_annotations.coco.json")

    if not os.path.exists(json_path):
        return {}, 0, 0, 0, crop_id_start

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cat_id_to_name = {cat["id"]: cat["name"] for cat in data.get("categories", [])}
    images_by_id = {img["id"]: img for img in data.get("images", [])}

    stats = {name: 0 for name in target_names}
    skipped_small = 0
    skipped_missing = 0
    skipped_read_error = 0
    img_cache = {}
    crop_global_id = crop_id_start

    for ann in data.get("annotations", []):
        cat_id = ann.get("category_id")
        if cat_id in exclude_ids:
            continue

        cat_name = cat_id_to_name.get(cat_id, "")
        if cat_name not in target_names:
            continue

        img_info = images_by_id.get(ann["image_id"])
        if img_info is None:
            skipped_missing += 1
            continue

        file_name = img_info["file_name"]
        img_path = os.path.join(split_dir, file_name)

        if img_path not in img_cache:
            img = cv2.imread(img_path)
            if img is None:
                skipped_read_error += 1
                img_cache[img_path] = None
                continue
            img_cache[img_path] = img
        else:
            img = img_cache[img_path]
            if img is None:
                continue

        img_h, img_w = img.shape[:2]

        bbox = ann.get("bbox", [])
        if len(bbox) != 4:
            continue

        x, y, w, h = [int(round(float(v))) for v in bbox]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)

        crop_w = x2 - x1
        crop_h = y2 - y1

        if crop_w < min_crop_size or crop_h < min_crop_size:
            skipped_small += 1
            continue

        crop = img[y1:y2, x1:x2]
        crop = cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)

        base_name = os.path.splitext(file_name)[0]
        crop_name = f"{split}_{base_name}_crop_{crop_global_id}.png"
        crop_path = os.path.join(output_dir, cat_name, crop_name)

        cv2.imwrite(crop_path, crop)

        stats[cat_name] += 1
        crop_global_id += 1

    return stats, skipped_small, skipped_missing, skipped_read_error, crop_global_id


def run_cropping(input_dir, output_dir, categories=None, splits=None,
                 progress_callback=None):
    """
    Ejecuta el cropping completo.

    Args:
        input_dir: Carpeta raíz del export de Roboflow
        output_dir: Carpeta de salida para los crops
        categories: Set/list de nombres de categoría a recortar
        splits: Lista de splits a procesar (default: ["train"])
        progress_callback: Función(status_dict) llamada con progreso

    Returns:
        dict con estadísticas del proceso
    """
    if categories is None:
        from backend.config import DEFAULT_CATEGORIES
        categories = set(DEFAULT_CATEGORIES)
    else:
        categories = set(categories)

    if splits is None:
        splits = DEFAULT_SPLITS

    # Crear subcarpetas de salida
    for cat_name in categories:
        os.makedirs(os.path.join(output_dir, cat_name), exist_ok=True)

    total_stats = {name: 0 for name in categories}
    total_skipped_small = 0
    total_skipped_missing = 0
    total_skipped_read_error = 0
    crop_id = 0

    for i, split in enumerate(splits):
        if progress_callback:
            progress_callback({
                'phase': 'cropping',
                'current_split': split,
                'split_index': i,
                'total_splits': len(splits),
            })

        stats, sk_small, sk_miss, sk_err, crop_id = process_split(
            input_dir, split, output_dir, categories, MIN_CROP_SIZE, crop_id
        )

        for name in categories:
            total_stats[name] += stats.get(name, 0)
        total_skipped_small += sk_small
        total_skipped_missing += sk_miss
        total_skipped_read_error += sk_err

    result = {
        'stats': total_stats,
        'total_crops': sum(total_stats.values()),
        'skipped_small': total_skipped_small,
        'skipped_missing': total_skipped_missing,
        'skipped_read_error': total_skipped_read_error,
        'output_dir': os.path.abspath(output_dir),
    }

    if progress_callback:
        progress_callback({'phase': 'cropping_done', 'result': result})

    return result
