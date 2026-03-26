"""
testing_service.py
Wraps the `proyecto_h_lib` functions for model testing and inference.
"""

import os
import sys
import glob
import cv2
import numpy as np
import base64
from backend.config import PROJECT_ROOT

PROYECTO_H_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "py_PROYECTO_H"))
SCRIPTS_DIR = os.path.join(PROYECTO_H_DIR, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DECISION_TREE_DIR = os.path.join(SCRIPTS_DIR, "05-logica_conteo_tallos")
if DECISION_TREE_DIR not in sys.path:
    sys.path.insert(0, DECISION_TREE_DIR)

# Intentar importar la librería unificada
try:
    import proyecto_h_lib as phl
except ImportError as e:
    print(f"[!] No se pudo importar proyecto_h_lib desde {SCRIPTS_DIR}. Error: {e}")
    phl = None

MASKRCNN_BASE = os.path.join(PROYECTO_H_DIR, "models", "maskrcnn")
CONVNEXT_BASE = os.path.join(PROYECTO_H_DIR, "models", "convnext")
TREE_BASE = os.path.join(PROYECTO_H_DIR, "models", "tree_conteo")
COCO_JSON = os.path.join(PROYECTO_H_DIR, "data", "coco_unified", "annotations", "test.json")

# Helpers
def _bgr_to_base64_png(img_bgr) -> str:
    if img_bgr is None:
        return ""
    success, encoded = cv2.imencode('.png', img_bgr)
    if not success:
        return ""
    return base64.b64encode(encoded).decode('ascii')


def _get_class_names():
    if phl:
        return phl.CLASS_NAMES
    return ["Flores", "ticket", "Balda", "Planta", "tallo_grupo"]


# ─── Listado de Modelos ───
def list_maskrcnn_runs():
    if not os.path.exists(MASKRCNN_BASE):
        return []
    runs = sorted([d for d in glob.glob(os.path.join(MASKRCNN_BASE, "*")) if os.path.isdir(d)], reverse=True)
    return [{"id": os.path.basename(r), "path": r} for r in runs]


def list_maskrcnn_checkpoints(run_id: str):
    run_dir = os.path.join(MASKRCNN_BASE, run_id)
    if not os.path.exists(run_dir):
        return []
    models = sorted(glob.glob(os.path.join(run_dir, "*.pth")))
    return [{"id": os.path.basename(m), "path": m} for m in models]


def list_convnext_runs():
    if not os.path.exists(CONVNEXT_BASE):
        return []
    runs = sorted([d for d in glob.glob(os.path.join(CONVNEXT_BASE, "*")) if os.path.isdir(d)], reverse=True)
    return [{"id": os.path.basename(r), "path": r} for r in runs]


def list_convnext_checkpoints(run_id: str):
    run_dir = os.path.join(CONVNEXT_BASE, run_id)
    if not os.path.exists(run_dir):
        return []
    models = sorted(glob.glob(os.path.join(run_dir, "*.pth")))
    return [{"id": os.path.basename(m), "path": m} for m in models]


def list_tree_models():
    if not os.path.exists(TREE_BASE):
        return []
    models = sorted(glob.glob(os.path.join(TREE_BASE, "*.pkl")))
    return [{"id": os.path.basename(m), "path": m} for m in models]


# ─── Inferencia por módulos ───
def run_maskrcnn_test(image_bytes: bytes, model_path: str, threshold: float, nms_thresh: float):
    if not phl:
        raise RuntimeError("proyecto_h_lib no está disponible.")
    
    # Decodificar
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Cargar predictor 
    config_yaml = os.path.join(PROYECTO_H_DIR, "configs", "config_maskrcnn.yaml")
    predictor = phl.load_maskrcnn(
        model_path=model_path, 
        score_thresh=threshold, 
        config_yaml=config_yaml,
        nms_thresh=nms_thresh
    )

    # Renderizar (usamos Detectron2 Visualizer como en app.py original)
    from detectron2.utils.visualizer import Visualizer
    from detectron2.data import MetadataCatalog
    
    outputs = predictor(img_bgr)
    class_names = _get_class_names()
    
    tmp_dataset = "__tmp_test_area__"
    try:
        MetadataCatalog.get(tmp_dataset).thing_classes = class_names
    except:
        pass

    v = Visualizer(img_bgr[:, :, ::-1], metadata=MetadataCatalog.get(tmp_dataset), scale=1.0)
    out = v.draw_instance_predictions(outputs["instances"].to("cpu"))
    res_bgr = out.get_image()[:, :, ::-1]

    # Devolvemos base64 al frontend
    return _bgr_to_base64_png(res_bgr)


def run_convnext_test(image_bytes: bytes, model_path: str, run_dir: str):
    if not phl:
        raise RuntimeError("proyecto_h_lib no está disponible.")
    
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    clasificador = phl.load_convnext(run_dir=run_dir, model_name=os.path.basename(model_path))
    cnx_model, cnx_transform, cnx_classes, cnx_device = clasificador
    
    # Extraída de app.py para devolver top5
    import torch
    from PIL import Image as PILImage
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = PILImage.fromarray(img_rgb)
    input_tensor = cnx_transform(pil_img).unsqueeze(0).to(cnx_device)

    with torch.no_grad():
        output = cnx_model(input_tensor)
        probs = torch.softmax(output, dim=1)[0]

    top5_probs, top5_indices = probs.topk(min(5, len(cnx_classes)))
    
    results = []
    for prob, idx in zip(top5_probs, top5_indices):
        results.append({"class": cnx_classes[idx.item()], "prob": prob.item()})
        
    return results


def _draw_boxes(img, elements):
    if img is None: return None
    out = img.copy()
    COLORS = {
        "flor": (50, 205, 50),
        "planta": (255, 165, 0),
        "tallo_grupo": (200, 50, 50),
        "balda": (255, 0, 0),
        "ticket": (0, 0, 255)
    }

    for item in elements:
        bbox = item['bbox']
        label_str = str(item.get('label', item.get('class', ''))).lower()
        display_text = str(item.get('label', item.get('class', '')))
        conf = item.get('conf', item.get('score', None))
        if conf is not None:
            display_text += f" ({conf:.2f})"

        color = (200, 200, 200)
        for k, c in COLORS.items():
            if k in label_str:
                color = c
                break
        
        x1, y1 = int(bbox[0]), int(bbox[1])
        x2, y2 = int(bbox[2]), int(bbox[3])
        
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 3)
        
        # Acotar el tamaño máximo de la fuente para que cajas grandes (como 'balda') no tapen la imagen
        font_scale = min(1.0, max(0.5, (x2 - x1) / 300))
        thick = max(1, int(font_scale * 2))
        (tw, th), _ = cv2.getTextSize(display_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thick)
        cv2.rectangle(out, (x1, y1 - th - 10), (x1 + tw + 10, y1), color, -1)
        cv2.putText(out, display_text, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thick)
        
    return out


def run_pipeline_test(bytes_f: bytes, bytes_b: bytes, 
                      mrcnn_path: str, threshold: float, nms_thresh: float,
                      cnx_path: str, cnx_run_dir: str, tree_pkl_path: str = None):
    if not phl:
        raise RuntimeError("proyecto_h_lib no está disponible.")

    img_f = cv2.imdecode(np.frombuffer(bytes_f, np.uint8), cv2.IMREAD_COLOR)
    img_b = cv2.imdecode(np.frombuffer(bytes_b, np.uint8), cv2.IMREAD_COLOR)

    # 1. Mask R-CNN
    config_yaml = os.path.join(PROYECTO_H_DIR, "configs", "config_maskrcnn.yaml")
    predictor = phl.load_maskrcnn(
        model_path=mrcnn_path, 
        score_thresh=threshold, 
        config_yaml=config_yaml,
        nms_thresh=nms_thresh
    )
    
    det_f = phl.predict_maskrcnn(predictor, img_f)
    det_b = phl.predict_maskrcnn(predictor, img_b)

    # 2. ConvNeXt
    clasificador = phl.load_convnext(run_dir=cnx_run_dir, model_name=os.path.basename(cnx_path))

    # 3. Decision Tree Pipeline Completo
    import decision_tree_lib as dtd
    if tree_pkl_path and os.path.exists(tree_pkl_path):
        import joblib
        import sys
        
        # HACK: Inyectar la clase CascadeCountingModel en __main__ dado que el modelo
        # fue serializado en un script principal y pickle lo buscará allí.
        class CascadeCountingModel:
            def __init__(self, model_s1, model_s2):
                self.stage1 = model_s1
                self.stage2 = model_s2
            def predict(self, X):
                y_bin = self.stage1.predict(X)
                result = np.zeros(len(y_bin), dtype=int)
                mask_pos = y_bin == 1
                if mask_pos.any() and self.stage2 is not None:
                    # Funciona tanto si X es array (X[mask_pos]) como si es DF
                    X_copy = X.values if hasattr(X, 'values') else X
                    X_pos = X_copy[mask_pos]
                    result[mask_pos] = self.stage2.predict(X_pos)
                return result
            def predict_proba(self, X):
                return self.stage1.predict_proba(X)

        setattr(sys.modules['__main__'], 'CascadeCountingModel', CascadeCountingModel)

        dtd._TREE_PIPELINE = joblib.load(tree_pkl_path)
        print(f"[testing_service] Árbol de decisión cargado: {tree_pkl_path}")
    resultado = dtd.procesar_pareja_imagenes(det_f, det_b)
    conteo_final, ticket_mapping, bbox_labels = dtd.contar_articulos_tree(
        det_f, det_b, resultado['asignacion_base'],
        img_frontal=img_f, img_trasera=img_b, clasificador=clasificador
    )

    # Renderizados
    # Estado 1: Raw
    vis_f_raw = _draw_boxes(img_f, det_f)
    vis_b_raw = _draw_boxes(img_b, det_b)

    # Estado 2: Árbol
    tree_f = [x for x in bbox_labels if x.get('vista') == 'frontal']
    tree_b = [x for x in bbox_labels if x.get('vista') == 'trasera']
    vis_f_tree = _draw_boxes(img_f, tree_f)
    vis_b_tree = _draw_boxes(img_b, tree_b)

    return {
        "json": {"Items": conteo_final},
        "images": {
            "f_raw": _bgr_to_base64_png(vis_f_raw),
            "b_raw": _bgr_to_base64_png(vis_b_raw),
            "f_tree": _bgr_to_base64_png(vis_f_tree),
            "b_tree": _bgr_to_base64_png(vis_b_tree),
        }
    }
