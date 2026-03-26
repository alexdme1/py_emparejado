"""
labeling_service.py
Gestión portable de CSVs para el etiquetado del árbol de decisión.
Adaptado de decision_tree_lib.py (solo la parte de gestión de datos).
"""

import os
import pandas as pd
from backend.config import PROJECT_ROOT, IMAGE_EXTENSIONS

# ── Rutas de CSVs ──
DATA_DIR   = os.path.join(PROJECT_ROOT, "data", "arbol_conteo")
RAW_CSV    = os.path.join(DATA_DIR, "detections_raw.csv")
LABELS_CSV = os.path.join(DATA_DIR, "detections_labels.csv")
MERGED_CSV = os.path.join(DATA_DIR, "detections_labeled.csv")
KEY_COLS   = ["image_pair_id", "detection_id"]

# ── Ruta de imágenes ──
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset_final")


# ═══════════════════════════════════════════════════════════
# GESTIÓN DE CSVs
# ═══════════════════════════════════════════════════════════

def load_raw() -> pd.DataFrame:
    """Carga detections_raw.csv. Devuelve DataFrame vacío si no existe o está vacío."""
    if os.path.exists(RAW_CSV) and os.path.getsize(RAW_CSV) > 0:
        return pd.read_csv(RAW_CSV)
    return pd.DataFrame()


def load_labels() -> pd.DataFrame:
    """Carga detections_labels.csv. Si no existe o está vacío devuelve DataFrame vacío."""
    if os.path.exists(LABELS_CSV) and os.path.getsize(LABELS_CSV) > 0:
        return pd.read_csv(LABELS_CSV)
    return pd.DataFrame(columns=KEY_COLS + ["unidades_label_d"])


def save_labels(df_labels: pd.DataFrame) -> None:
    """Guarda etiquetas a detections_labels.csv."""
    os.makedirs(DATA_DIR, exist_ok=True)
    df_labels.to_csv(LABELS_CSV, index=False)


def merge_raw_labels() -> pd.DataFrame:
    """
    Join de raw + labels por (image_pair_id, detection_id).
    Rellena unidades_label_d = -1 si no hay etiqueta.
    Guarda detections_labeled.csv y devuelve el DataFrame.
    """
    df_raw = load_raw()
    if df_raw.empty:
        return df_raw

    df_lab = load_labels()

    if "unidades_label_d" in df_raw.columns:
        df_raw = df_raw.drop(columns=["unidades_label_d"])

    if df_lab.empty:
        df = df_raw.copy()
        df["unidades_label_d"] = -1
    else:
        df = df_raw.merge(df_lab[KEY_COLS + ["unidades_label_d"]], on=KEY_COLS, how="left")
        df["unidades_label_d"] = df["unidades_label_d"].fillna(-1).astype(int)

    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(MERGED_CSV, index=False)
    return df


# ═══════════════════════════════════════════════════════════
# FUNCIONES DE ALTO NIVEL PARA LA API
# ═══════════════════════════════════════════════════════════

def get_pair_ids() -> list:
    """Devuelve lista ordenada de pair_ids disponibles en detections_raw.csv."""
    df = load_raw()
    if df.empty:
        return []
    ids = df["image_pair_id"].astype(str).unique().tolist()
    ids.sort(key=lambda x: int(x) if x.isdigit() else x)
    return ids


def get_pair_detections(pair_id: str) -> list:
    """
    Devuelve detecciones flor/planta de un par como lista de dicts:
    [{detection_id, d_tipo, d_vista, d_bbox_x1, d_bbox_y1, d_bbox_x2, d_bbox_y2, ...}]
    """
    df = load_raw()
    if df.empty:
        return []

    df_pair = df[df["image_pair_id"].astype(str) == str(pair_id)]
    plant_rows = df_pair[df_pair["d_tipo"].isin(["flor", "planta"])]

    result = []
    for _, row in plant_rows.iterrows():
        det = {
            "detection_id": int(row["detection_id"]),
            "d_tipo": str(row["d_tipo"]),
            "d_vista": str(row.get("d_vista", "F")),
            "balda_idx": int(row["balda_idx"]) if "balda_idx" in row and not pd.isna(row.get("balda_idx")) else -1,
            "d_bbox_x1": float(row.get("d_bbox_x1", 0)),
            "d_bbox_y1": float(row.get("d_bbox_y1", 0)),
            "d_bbox_x2": float(row.get("d_bbox_x2", 0)),
            "d_bbox_y2": float(row.get("d_bbox_y2", 0)),
            "raw_bbox_x1": float(row.get("raw_bbox_x1", row.get("d_bbox_x1", 0))),
            "raw_bbox_y1": float(row.get("raw_bbox_y1", row.get("d_bbox_y1", 0))),
            "raw_bbox_x2": float(row.get("raw_bbox_x2", row.get("d_bbox_x2", 0))),
            "raw_bbox_y2": float(row.get("raw_bbox_y2", row.get("d_bbox_y2", 0))),
        }
        result.append(det)
    return result


def get_pair_labels(pair_id: str) -> dict:
    """
    Devuelve conteos existentes para un par: {detection_id: count}
    """
    df = load_labels()
    if df.empty:
        return {}

    pair_lab = df[df["image_pair_id"].astype(str) == str(pair_id)]
    counts = {}
    for _, row in pair_lab.iterrows():
        counts[int(row["detection_id"])] = int(row["unidades_label_d"])
    return counts


def save_pair_labels(pair_id: str, counts: dict) -> None:
    """
    Guarda conteos de un par: counts = {detection_id: count}
    Reemplaza las filas existentes de este par.
    """
    rows = []
    for det_id, count in counts.items():
        rows.append({
            "image_pair_id": pair_id,
            "detection_id": int(det_id),
            "unidades_label_d": int(count),
        })
    df_new = pd.DataFrame(rows)

    df_existing = load_labels()
    if not df_existing.empty:
        df_existing = df_existing[df_existing["image_pair_id"].astype(str) != str(pair_id)]
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_all = df_new

    save_labels(df_all)


def get_summary_stats() -> dict:
    """Estadísticas globales para la vista de resumen."""
    df = merge_raw_labels()
    if df.empty:
        return {"total_detections": 0, "labeled": 0, "pairs": 0}

    return {
        "total_detections": len(df),
        "labeled": int((df["unidades_label_d"] >= 0).sum()),
        "pairs": int(df["image_pair_id"].nunique()),
    }


def get_pair_summary(pair_id: str) -> list:
    """Tabla de detecciones de un par con labels para vista de resumen."""
    df = merge_raw_labels()
    if df.empty:
        return []

    df_pair = df[df["image_pair_id"].astype(str) == str(pair_id)]
    df_fp = df_pair[df_pair["d_tipo"].isin(["flor", "planta"])]

    display_cols = [c for c in [
        "detection_id", "d_tipo", "d_vista", "balda_idx",
        "d_pos_rel", "d_volumen", "d_score_mrcnn", "d_score_convnext",
        "d_iou_max", "d_n_solapados", "unidades_label_d",
    ] if c in df_fp.columns]

    return df_fp[display_cols].to_dict(orient="records")


def find_pair_images(pair_id: str) -> dict:
    """
    Busca las imágenes F/B de un par en dataset_final/.
    Devuelve {"frontal": path_or_None, "trasera": path_or_None}
    """
    result = {"frontal": None, "trasera": None}
    for ext in [".png", ".jpg", ".jpeg"]:
        fp = os.path.join(DATASET_DIR, f"{pair_id}F{ext}")
        bp = os.path.join(DATASET_DIR, f"{pair_id}B{ext}")
        if os.path.exists(fp):
            result["frontal"] = fp
        if os.path.exists(bp):
            result["trasera"] = bp
        if result["frontal"] and result["trasera"]:
            break
    return result


def get_labeled_pair_ids() -> set:
    """Devuelve el set de pair_ids que ya tienen alguna etiqueta."""
    df = load_labels()
    if df.empty:
        return set()
    return set(df["image_pair_id"].astype(str).unique())


def get_resume_index() -> int:
    """
    Calcula el índice del par donde continuar el etiquetado.
    Busca la última imagen (pair_id) que tiene sus 5 siguientes sin etiquetar.
    Devuelve ese índice para que el frontend empiece ahí.
    Si todo está etiquetado, devuelve 0.
    """
    pair_ids = get_pair_ids()
    if not pair_ids:
        return 0

    labeled = get_labeled_pair_ids()
    if not labeled:
        return 0

    # Recorrer desde el final hacia atrás para encontrar el último par
    # etiquetado. El punto de reanudación es el siguiente par sin etiquetar.
    for i in range(len(pair_ids) - 1, -1, -1):
        if pair_ids[i] in labeled:
            # Comprobar si los siguientes 5 (o lo que quede) están sin etiquetar
            next_unlabeled = True
            for j in range(i + 1, min(i + 6, len(pair_ids))):
                if pair_ids[j] in labeled:
                    next_unlabeled = False
                    break

            if next_unlabeled:
                # Devolver i: la última imagen con etiqueta cuyas 5 siguientes
                # están pendientes. El usuario retoma desde aquí.
                return i
    return 0
