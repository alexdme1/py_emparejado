"""
routes/video_extraction.py — Endpoints de extracción de capturas desde vídeo.
"""

import os
import io
import base64
from flask import Blueprint, jsonify, request, send_file
from backend.services.video_extraction_service import (
    get_video_first_frame,
    start_extraction,
    get_job_status,
    stop_job,
)

video_bp = Blueprint('video', __name__)


@video_bp.route('/api/video/preview', methods=['POST'])
def video_preview():
    """
    Devuelve el primer frame de un vídeo como JPEG base64.
    Body: { video_path: string }
    """
    data = request.json or {}
    video_path = data.get('video_path', '')

    if not video_path or not os.path.isfile(video_path):
        return jsonify({'error': f'Vídeo no encontrado: {video_path}'}), 400

    frame_bytes, dimensions = get_video_first_frame(video_path)
    if frame_bytes is None:
        return jsonify({'error': 'No se pudo leer el vídeo'}), 400

    frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
    return jsonify({
        'success': True,
        'frame': frame_b64,
        'width': dimensions[0],
        'height': dimensions[1],
    })


@video_bp.route('/api/video/start', methods=['POST'])
def video_start():
    """
    Inicia la extracción de capturas de un vídeo.
    Body: {
        video_path, output_dir, camera_type,
        roi: {x, y, width, height},
        confidence, upload_roboflow, roboflow_api_key,
        roboflow_workspace, roboflow_project
    }
    """
    data = request.json or {}
    video_path = data.get('video_path', '')
    output_dir = data.get('output_dir', '')
    camera_type = data.get('camera_type', 'delantera')
    roi = data.get('roi')
    confidence = data.get('confidence', 0.5)

    # Upload params
    upload_roboflow = data.get('upload_roboflow', False)
    roboflow_api_key = data.get('roboflow_api_key', '')
    roboflow_workspace = data.get('roboflow_workspace', 'floresverdnatura')
    roboflow_project = data.get('roboflow_project', 'proyecto_h')

    # Validaciones
    if not video_path or not os.path.isfile(video_path):
        return jsonify({'error': f'Vídeo no encontrado: {video_path}'}), 400
    if not output_dir:
        return jsonify({'error': 'Falta output_dir'}), 400
    if not roi or not all(k in roi for k in ('x', 'y', 'width', 'height')):
        return jsonify({'error': 'Falta ROI (x, y, width, height)'}), 400
    if roi['width'] <= 0 or roi['height'] <= 0:
        return jsonify({'error': 'ROI inválida (width/height deben ser > 0)'}), 400

    result = start_extraction(
        video_path=video_path,
        output_dir=output_dir,
        roi=roi,
        camera_type=camera_type,
        confidence=confidence,
        upload_roboflow=upload_roboflow,
        roboflow_api_key=roboflow_api_key,
        roboflow_workspace=roboflow_workspace,
        roboflow_project=roboflow_project,
    )

    if 'error' in result:
        return jsonify(result), 409

    return jsonify(result)


@video_bp.route('/api/video/status')
def video_status():
    """Devuelve el estado actual del job de extracción."""
    return jsonify(get_job_status())


@video_bp.route('/api/video/stop', methods=['POST'])
def video_stop():
    """Detiene el job de extracción actual."""
    stop_job()
    return jsonify({'success': True, 'message': 'Stop requested'})


@video_bp.route('/api/video/pick_file', methods=['POST'])
def pick_video_file():
    """Abre un diálogo nativo para seleccionar un archivo de vídeo."""
    import threading

    data = request.json or {}
    initial_dir = data.get('initial_dir', os.path.expanduser('~'))

    selected = [None]

    def open_dialog():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askopenfilename(
                initialdir=initial_dir,
                title='Seleccionar vídeo',
                filetypes=[
                    ('Vídeos MP4', '*.mp4'),
                    ('Todos los vídeos', '*.mp4 *.avi *.mkv *.mov'),
                    ('Todos los archivos', '*.*'),
                ],
            )
            root.destroy()
            selected[0] = path if path else None
        except Exception:
            selected[0] = None

    dialog_thread = threading.Thread(target=open_dialog)
    dialog_thread.start()
    dialog_thread.join(timeout=120)

    if selected[0]:
        return jsonify({'success': True, 'path': selected[0]})
    else:
        return jsonify({'success': False, 'path': None})
