"""
routes/upload.py — Endpoints de upload a Google Drive.
"""

import os
import threading
from flask import Blueprint, jsonify, request
from backend.services.drive_service import upload_to_drive

upload_bp = Blueprint('upload', __name__)

# ── Estado del job de upload ──
_drive_job = {
    'running': False,
    'status': None,
    'result': None,
    'error': None,
}


def _update_status(status_dict):
    _drive_job['status'] = status_dict


@upload_bp.route('/api/upload/drive', methods=['POST'])
def start_drive_upload():
    """
    Inicia la subida a Google Drive.
    Body JSON:
        dataset_dir, credentials_path, folder_id, start_index (optional)
    """
    if _drive_job['running']:
        return jsonify({'error': 'Ya hay un job de upload en curso'}), 409

    data = request.json or {}
    dataset_dir = data.get('dataset_dir', '')
    credentials_path = data.get('credentials_path', '')
    folder_id = data.get('folder_id', '')
    start_index = data.get('start_index', None)

    if not dataset_dir:
        return jsonify({'error': 'Falta dataset_dir'}), 400
    if not credentials_path:
        return jsonify({'error': 'Falta credentials_path'}), 400
    if not folder_id:
        return jsonify({'error': 'Falta folder_id'}), 400

    _drive_job['running'] = True
    _drive_job['status'] = {'phase': 'starting'}
    _drive_job['result'] = None
    _drive_job['error'] = None

    def run_job():
        try:
            result = upload_to_drive(
                dataset_dir, credentials_path, folder_id,
                start_index=start_index,
                progress_callback=_update_status
            )
            _drive_job['result'] = result
        except Exception as e:
            _drive_job['error'] = str(e)
        finally:
            _drive_job['running'] = False

    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()

    return jsonify({'success': True, 'message': 'Upload a Drive iniciado'})


@upload_bp.route('/api/upload/drive/status')
def drive_status():
    """Devuelve el estado del job de upload a Drive."""
    return jsonify({
        'running': _drive_job['running'],
        'status': _drive_job['status'],
        'result': _drive_job['result'],
        'error': _drive_job['error'],
    })
