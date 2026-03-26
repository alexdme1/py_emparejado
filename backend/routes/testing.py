"""
Routes for testing models (Mask R-CNN, ConvNeXt, y Pipeline completo).
Blueprint: /api/testing/
"""

import os
from flask import Blueprint, jsonify, request
from backend.services.testing_service import (
    list_maskrcnn_runs,
    list_maskrcnn_checkpoints,
    list_convnext_runs,
    list_convnext_checkpoints,
    list_tree_models,
    run_maskrcnn_test,
    run_convnext_test,
    run_pipeline_test
)

testing_bp = Blueprint('testing', __name__, url_prefix='/api/testing')

# ─── Listados ───
@testing_bp.route('/maskrcnn/runs')
def api_list_mrcnn_runs():
    try:
        return jsonify(list_maskrcnn_runs())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@testing_bp.route('/maskrcnn/runs/<path:run_id>/checkpoints')
def api_list_mrcnn_checkpoints(run_id):
    try:
        return jsonify(list_maskrcnn_checkpoints(run_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@testing_bp.route('/convnext/runs')
def api_list_cnx_runs():
    try:
        return jsonify(list_convnext_runs())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@testing_bp.route('/convnext/runs/<path:run_id>/checkpoints')
def api_list_cnx_checkpoints(run_id):
    try:
        return jsonify(list_convnext_checkpoints(run_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@testing_bp.route('/tree/models')
def api_list_tree_models():
    try:
        return jsonify(list_tree_models())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Inferencias ───
@testing_bp.route('/maskrcnn/infer', methods=['POST'])
def api_infer_mrcnn():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    model_path = request.form.get('model_path')
    threshold = float(request.form.get('threshold', 0.5))
    nms_thresh = float(request.form.get('nms_thresh', 0.5))
    
    if not model_path:
        return jsonify({"error": "No model_path provided"}), 400

    try:
        b64_img = run_maskrcnn_test(file.read(), model_path, threshold, nms_thresh)
        return jsonify({"image_base64": b64_img})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@testing_bp.route('/convnext/infer', methods=['POST'])
def api_infer_cnx():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    model_path = request.form.get('model_path')
    run_dir = request.form.get('run_dir')
    
    if not model_path or not run_dir:
        return jsonify({"error": "Missing model_path or run_dir"}), 400

    try:
        results = run_convnext_test(file.read(), model_path, run_dir)
        return jsonify({"predictions": results})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@testing_bp.route('/pipeline/infer', methods=['POST'])
def api_infer_pipeline():
    if 'image_f' not in request.files or 'image_b' not in request.files:
        return jsonify({"error": "Both image_f and image_b must be provided"}), 400
    
    file_f = request.files['image_f']
    file_b = request.files['image_b']
    
    mrcnn_path = request.form.get('mrcnn_path')
    threshold = float(request.form.get('threshold', 0.5))
    nms_thresh = float(request.form.get('nms_thresh', 0.5))
    cnx_path = request.form.get('cnx_path')
    cnx_run_dir = request.form.get('cnx_run_dir')

    if not mrcnn_path or not cnx_path or not cnx_run_dir:
        return jsonify({"error": "Missing model parameters"}), 400

    try:
        print(f"[pipeline/infer] mrcnn={mrcnn_path}, cnx={cnx_path}, cnx_run={cnx_run_dir}, "
              f"thresh={threshold}, nms={nms_thresh}, tree={request.form.get('tree_path')}")
        res = run_pipeline_test(file_f.read(), file_b.read(), 
                                mrcnn_path, threshold, nms_thresh,
                                cnx_path, cnx_run_dir,
                                tree_pkl_path=request.form.get('tree_path'))
        return jsonify(res)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
