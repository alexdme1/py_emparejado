"""
routes/pairing.py — Endpoints de emparejado de imágenes.
Port directo de los endpoints del app.py original.
"""

import os
import io
from flask import Blueprint, jsonify, request, send_file
from PIL import Image, ImageOps
from backend.services import pairing_service as ps

pairing_bp = Blueprint('pairing', __name__)

# ── Session state (se configura con /api/pairing/start) ──
_session = {
    'frontales_dir': '',
    'traseras_dir': '',
    'paired_dir': '',
    'state_file': '',
    'active': False,
}


def _get_dirs():
    return _session['frontales_dir'], _session['traseras_dir'], _session['paired_dir'], _session['state_file']


def _ensure_active():
    if not _session['active']:
        return jsonify({'error': 'Sesión de emparejado no iniciada. Usa /api/pairing/start'}), 400
    return None


@pairing_bp.route('/api/pairing/start', methods=['POST'])
def start_pairing():
    """Inicia una sesión de emparejado con las carpetas indicadas."""
    data = request.json or {}
    frontales_dir = data.get('frontales_dir', '')
    traseras_dir = data.get('traseras_dir', '')
    output_dir = data.get('output_dir', '')

    if not frontales_dir or not traseras_dir or not output_dir:
        return jsonify({'error': 'Faltan carpetas: frontales_dir, traseras_dir, output_dir'}), 400

    if not os.path.isdir(frontales_dir):
        return jsonify({'error': f'Carpeta no encontrada: {frontales_dir}'}), 400
    if not os.path.isdir(traseras_dir):
        return jsonify({'error': f'Carpeta no encontrada: {traseras_dir}'}), 400

    os.makedirs(output_dir, exist_ok=True)

    state_file = os.path.join(output_dir, 'state.json')

    _session['frontales_dir'] = frontales_dir
    _session['traseras_dir'] = traseras_dir
    _session['paired_dir'] = output_dir
    _session['state_file'] = state_file
    _session['active'] = True

    # Cargar o inicializar estado
    state = ps.load_state(state_file)
    if state is None:
        state = ps.init_state(frontales_dir, traseras_dir, state_file)

    from backend.utils import get_sorted_images
    return jsonify({
        'success': True,
        'frontales': len(get_sorted_images(frontales_dir)),
        'traseras': len(get_sorted_images(traseras_dir)),
    })


@pairing_bp.route('/api/pairing/session')
def get_session():
    """Devuelve info de la sesión activa."""
    return jsonify({
        'active': _session['active'],
        'frontales_dir': _session['frontales_dir'],
        'traseras_dir': _session['traseras_dir'],
        'paired_dir': _session['paired_dir'],
    })


@pairing_bp.route('/api/state')
def api_state():
    """Devuelve el estado actual para el frontend."""
    err = _ensure_active()
    if err:
        return err

    _, _, _, state_file = _get_dirs()
    state = ps.load_state(state_file)
    if state is None:
        return jsonify({'error': 'No hay estado guardado'}), 400

    result = ps.get_state_for_frontend(state, state_file)
    return jsonify(result)


@pairing_bp.route('/api/pair', methods=['POST'])
def api_pair():
    err = _ensure_active()
    if err:
        return err

    _, _, paired_dir, state_file = _get_dirs()
    state = ps.load_state(state_file)
    result = ps.do_pair(state, paired_dir, state_file)

    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@pairing_bp.route('/api/next', methods=['POST'])
def api_next_trasera():
    err = _ensure_active()
    if err:
        return err

    _, _, _, state_file = _get_dirs()
    state = ps.load_state(state_file)
    result = ps.do_next_trasera(state, state_file)
    return jsonify(result)


@pairing_bp.route('/api/prev', methods=['POST'])
def api_prev_trasera():
    err = _ensure_active()
    if err:
        return err

    _, _, _, state_file = _get_dirs()
    state = ps.load_state(state_file)
    result = ps.do_prev_trasera(state, state_file)
    return jsonify(result)


@pairing_bp.route('/api/skip', methods=['POST'])
def api_skip():
    err = _ensure_active()
    if err:
        return err

    _, _, _, state_file = _get_dirs()
    state = ps.load_state(state_file)
    result = ps.do_skip_frontal(state, state_file)
    return jsonify(result)


@pairing_bp.route('/api/skip_trasera', methods=['POST'])
def api_skip_trasera():
    err = _ensure_active()
    if err:
        return err

    _, _, _, state_file = _get_dirs()
    state = ps.load_state(state_file)
    result = ps.do_skip_trasera(state, state_file)
    return jsonify(result)


@pairing_bp.route('/api/undo', methods=['POST'])
def api_undo():
    err = _ensure_active()
    if err:
        return err

    _, _, paired_dir, state_file = _get_dirs()
    state = ps.load_state(state_file)
    result = ps.do_undo(state, paired_dir, state_file)

    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@pairing_bp.route('/api/review', methods=['POST'])
def api_review():
    err = _ensure_active()
    if err:
        return err

    _, _, _, state_file = _get_dirs()
    state = ps.load_state(state_file)
    result = ps.do_review(state, state_file)
    return jsonify(result)


@pairing_bp.route('/api/reset', methods=['POST'])
def api_reset():
    err = _ensure_active()
    if err:
        return err

    frontales_dir, traseras_dir, paired_dir, state_file = _get_dirs()
    result = ps.do_reset(paired_dir, frontales_dir, traseras_dir, state_file)
    return jsonify(result)


@pairing_bp.route('/api/pairing/rename', methods=['POST'])
def api_rename():
    """Ejecuta el renombrado de parejas."""
    err = _ensure_active()
    if err:
        return err

    data = request.json or {}
    _, _, paired_dir, state_file = _get_dirs()
    output_dir = data.get('output_dir', os.path.join(os.path.dirname(paired_dir), 'dataset_final'))

    from backend.services.rename_service import run_rename
    result = run_rename(paired_dir, output_dir, state_file)

    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


# ── Servir imágenes con rotación ──────────────────────


@pairing_bp.route('/images/frontales/<path:filename>')
def serve_frontal(filename):
    """Sirve imagen frontal rotada 90° a la izquierda."""
    frontales_dir = _session.get('frontales_dir', '')
    filepath = os.path.join(frontales_dir, filename)
    if not os.path.exists(filepath):
        return 'Not found', 404
    img = Image.open(filepath)
    img = img.rotate(90, expand=True)
    buf = io.BytesIO()
    fmt = 'PNG' if filename.lower().endswith('.png') else 'JPEG'
    img.save(buf, format=fmt)
    buf.seek(0)
    mime = 'image/png' if fmt == 'PNG' else 'image/jpeg'
    return send_file(buf, mimetype=mime)


@pairing_bp.route('/images/traseras/<path:filename>')
def serve_trasera(filename):
    """Sirve imagen trasera rotada 90° a la izquierda y espejada."""
    traseras_dir = _session.get('traseras_dir', '')
    filepath = os.path.join(traseras_dir, filename)
    if not os.path.exists(filepath):
        return 'Not found', 404
    img = Image.open(filepath)
    img = img.rotate(90, expand=True)
    img = ImageOps.mirror(img)
    buf = io.BytesIO()
    fmt = 'PNG' if filename.lower().endswith('.png') else 'JPEG'
    img.save(buf, format=fmt)
    buf.seek(0)
    mime = 'image/png' if fmt == 'PNG' else 'image/jpeg'
    return send_file(buf, mimetype=mime)
