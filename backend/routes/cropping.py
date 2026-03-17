"""
routes/cropping.py — Endpoints de cropping de imágenes.
"""

import os
import threading
from flask import Blueprint, jsonify, request
from backend.services.cropping_service import run_cropping
from backend.services.roboflow_service import upload_to_roboflow
from backend.config import (
    DEFAULT_CATEGORIES, ROBOFLOW_WORKSPACE, ROBOFLOW_PROJECT,
    ROBOFLOW_BATCH_PREFIX, DEFAULT_SPLITS
)

cropping_bp = Blueprint('cropping', __name__)

# ── Estado del job en curso ──
_job = {
    'running': False,
    'status': None,
    'result': None,
    'error': None,
}


def _update_status(status_dict):
    _job['status'] = status_dict


@cropping_bp.route('/api/cropping/start', methods=['POST'])
def start_cropping():
    """
    Inicia el proceso de cropping + upload a Roboflow.
    Body JSON:
        input_dir, output_dir, categories (optional),
        splits (optional), roboflow_api_key, roboflow_workspace (optional),
        roboflow_project (optional), roboflow_batch (optional)
    """
    if _job['running']:
        return jsonify({'error': 'Ya hay un job de cropping en curso'}), 409

    data = request.json or {}
    input_dir = data.get('input_dir', '')
    output_dir = data.get('output_dir', '')
    categories = data.get('categories', list(DEFAULT_CATEGORIES))
    splits = data.get('splits', list(DEFAULT_SPLITS))
    api_key = data.get('roboflow_api_key', '')
    workspace = data.get('roboflow_workspace', ROBOFLOW_WORKSPACE)
    project = data.get('roboflow_project', ROBOFLOW_PROJECT)
    batch_prefix = data.get('roboflow_batch', ROBOFLOW_BATCH_PREFIX)

    if not input_dir or not output_dir:
        return jsonify({'error': 'Faltan carpetas: input_dir, output_dir'}), 400
    if not os.path.isdir(input_dir):
        return jsonify({'error': f'Carpeta no encontrada: {input_dir}'}), 400
    if not api_key:
        return jsonify({'error': 'Falta roboflow_api_key'}), 400

    _job['running'] = True
    _job['status'] = {'phase': 'starting'}
    _job['result'] = None
    _job['error'] = None

    def run_job():
        try:
            # Paso 1: Cropping
            crop_result = run_cropping(
                input_dir, output_dir, categories, splits,
                progress_callback=_update_status
            )

            if crop_result.get('total_crops', 0) == 0:
                _job['result'] = crop_result
                _job['running'] = False
                return

            # Paso 2: Upload a Roboflow
            _update_status({'phase': 'uploading_roboflow', 'uploaded': 0})
            upload_result = upload_to_roboflow(
                output_dir, api_key, workspace, project, batch_prefix,
                progress_callback=_update_status
            )

            _job['result'] = {
                'cropping': crop_result,
                'upload': upload_result,
            }

        except Exception as e:
            _job['error'] = str(e)
        finally:
            _job['running'] = False

    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()

    return jsonify({'success': True, 'message': 'Job de cropping iniciado'})


@cropping_bp.route('/api/cropping/status')
def cropping_status():
    """Devuelve el estado actual del job de cropping."""
    return jsonify({
        'running': _job['running'],
        'status': _job['status'],
        'result': _job['result'],
        'error': _job['error'],
    })
