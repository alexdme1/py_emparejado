"""
Emparejador de Imágenes Frontales/Traseras
Aplicación web local para emparejar visualmente imágenes de carros.
"""

from flask import Flask, render_template, jsonify, send_from_directory, request, send_file
import os
import json
import shutil
import io
import re
import subprocess
from datetime import datetime
from PIL import Image, ImageOps

app = Flask(__name__)

# ── Rutas ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTALES_DIR = os.path.join(BASE_DIR, 'frontales')
TRASERAS_DIR = os.path.join(BASE_DIR, 'traseras')
PAIRED_DIR = os.path.join(BASE_DIR, 'paired_images')
STATE_FILE = os.path.join(BASE_DIR, 'state.json')
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff')

# ── Utilidades ─────────────────────────────────────────
def parse_timestamp(filename: str):
    """Extrae el datetime del nombre de archivo."""
    match = re.search(r'(\d{4}-\d{2}-\d{2})\s(\d{2}-\d{2}-\d{2})', filename)
    if match:
        return datetime.strptime(
            f"{match.group(1)} {match.group(2).replace('-', ':')}",
            "%Y-%m-%d %H:%M:%S"
        )
    return None

def precompute_candidatas(frontales, traseras, time_window_seconds=120):
    candidatas_por_frontal = {}
    for f in frontales:
        t_f = parse_timestamp(f)
        if t_f is None:
            candidatas_por_frontal[f] = list(traseras)
            continue
            
        candidatas = []
        valid_traseras_count = 0
        for t in traseras:
            t_t = parse_timestamp(t)
            if t_t is not None:
                valid_traseras_count += 1
                diff = abs((t_t - t_f).total_seconds())
                if diff <= time_window_seconds:
                    candidatas.append((t, diff))
        
        if valid_traseras_count == 0:
            candidatas_por_frontal[f] = list(traseras)
        else:
            candidatas.sort(key=lambda x: x[1])
            c_list = [c[0] for c in candidatas]
            if not c_list:
                fallback = []
                for t in traseras:
                    t_t = parse_timestamp(t)
                    if t_t is not None:
                        diff = abs((t_t - t_f).total_seconds())
                        fallback.append((t, diff))
                fallback.sort(key=lambda x: x[1])
                c_list = [c[0] for c in fallback]
            candidatas_por_frontal[f] = c_list
            
    return candidatas_por_frontal

def get_sorted_images(directory):
    """Lista ordenada de imágenes en un directorio."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        f for f in os.listdir(directory)
        if f.lower().endswith(IMAGE_EXTENSIONS)
    )


def load_state():
    """Carga estado guardado o inicializa uno nuevo escaneando carpetas."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return init_state()


def init_state():
    """Crea estado inicial escaneando frontales/ y traseras/."""
    frontales = get_sorted_images(FRONTALES_DIR)
    traseras = get_sorted_images(TRASERAS_DIR)
    state = {
        'frontales': frontales,
        'traseras': traseras,
        'candidatas_por_frontal': precompute_candidatas(frontales, traseras),
        'current_frontal_idx': 0,
        'current_trasera_idx': 0,
        'paired_traseras': [],
        'paired_frontales': [],
        'unpaired_frontales': [],
        'unpaired_traseras': [],
        'pairs': [],
        'pair_counter': 0,
        'history': [],
    }
    save_state(state)
    return state


def save_state(state):
    """Persiste estado a disco."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def available_traseras(state):
    """Traseras candidatas no emparejadas para la frontal actual."""
    if state.get('frontales') and state.get('current_frontal_idx', 0) < len(state['frontales']):
        current_frontal = state['frontales'][state['current_frontal_idx']]
        candidatas = state.get('candidatas_por_frontal', {}).get(current_frontal, [])
        if current_frontal not in state.get('candidatas_por_frontal', {}):
            candidatas = state.get('traseras', [])
    else:
        return []

    paired = set(state.get('paired_traseras', []))
    unpaired = set(state.get('unpaired_traseras', []))
    
    return [t for t in candidatas if t not in paired and t not in unpaired]


def advance_past_paired(state):
    """Avanza el índice frontal saltando las que ya están emparejadas."""
    paired = set(state.get('paired_frontales', []))
    while (state['current_frontal_idx'] < len(state['frontales']) and
           state['frontales'][state['current_frontal_idx']] in paired):
        state['current_frontal_idx'] += 1


# ── Rutas web ──────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/state')
def api_state():
    """Devuelve el estado actual para el frontend."""
    state = load_state()

    if 'candidatas_por_frontal' not in state:
        state['candidatas_por_frontal'] = precompute_candidatas(state.get('frontales', []), state.get('traseras', []))

    # Saltar frontales ya emparejadas
    advance_past_paired(state)
    save_state(state)

    avail = available_traseras(state)

    # ¿Hemos terminado todas las frontales?
    if state['current_frontal_idx'] >= len(state['frontales']):
        return jsonify({
            'completed': True,
            'total_pairs': state['pair_counter'],
            'unpaired': state['unpaired_frontales'],
            'total_frontales': len(state['frontales']),
        })

    current_frontal = state['frontales'][state['current_frontal_idx']]

    # ¿Ciclo de traseras completado sin emparejar?
    cycle_complete = False
    current_trasera = None
    if avail:
        if state['current_trasera_idx'] >= len(avail):
            cycle_complete = True
        else:
            current_trasera = avail[state['current_trasera_idx']]
    else:
        cycle_complete = True

    suggestion_delta_seconds = None
    if current_trasera:
        tf = parse_timestamp(current_frontal)
        tt = parse_timestamp(current_trasera)
        if tf and tt:
            suggestion_delta_seconds = abs((tt - tf).total_seconds())

    return jsonify({
        'completed': False,
        'current_frontal': current_frontal,
        'current_trasera': current_trasera,
        'frontal_idx': state['current_frontal_idx'],
        'frontal_name': current_frontal,
        'trasera_idx': state['current_trasera_idx'],
        'total_frontales': len(state['frontales']),
        'total_traseras_available': len(avail),
        'total_pairs': state['pair_counter'],
        'cycle_complete': cycle_complete,
        'unpaired_count': len(state['unpaired_frontales']),
        'unpaired_traseras_count': len(state.get('unpaired_traseras', [])),
        'suggestion_delta_seconds': suggestion_delta_seconds,
        'candidates_count': len(avail),
        'candidate_index': state['current_trasera_idx'],
        'no_candidates': len(avail) == 0,
    })


@app.route('/api/pair', methods=['POST'])
def api_pair():
    """Empareja la frontal actual con la trasera mostrada."""
    state = load_state()
    avail = available_traseras(state)

    if state['current_frontal_idx'] >= len(state['frontales']):
        return jsonify({'error': 'No quedan frontales'}), 400
    if not avail or state['current_trasera_idx'] >= len(avail):
        return jsonify({'error': 'No hay trasera seleccionada'}), 400

    frontal = state['frontales'][state['current_frontal_idx']]
    trasera = avail[state['current_trasera_idx']]

    # Crear carpeta numerada
    state['pair_counter'] += 1
    folder_name = f"{state['pair_counter']:03d}"
    pair_dir = os.path.join(PAIRED_DIR, folder_name)
    os.makedirs(pair_dir, exist_ok=True)

    # Copiar imágenes
    shutil.copy2(
        os.path.join(FRONTALES_DIR, frontal),
        os.path.join(pair_dir, frontal)
    )
    shutil.copy2(
        os.path.join(TRASERAS_DIR, trasera),
        os.path.join(pair_dir, trasera)
    )

    # Actualizar estado
    state['paired_frontales'].append(frontal)
    state['paired_traseras'].append(trasera)
    state['pairs'].append({
        'folder': folder_name,
        'frontal': frontal,
        'trasera': trasera,
    })
    prev_trasera_idx = state['current_trasera_idx']
    state['current_frontal_idx'] += 1
    state['current_trasera_idx'] = 0

    state.setdefault('history', []).append({
        'action': 'pair',
        'frontal': frontal,
        'trasera': trasera,
        'folder': folder_name,
        'prev_trasera_idx': prev_trasera_idx,
    })

    save_state(state)
    return jsonify({'success': True, 'folder': folder_name})


@app.route('/api/next', methods=['POST'])
def api_next_trasera():
    """Avanza a la siguiente trasera en el ciclo."""
    state = load_state()
    avail = available_traseras(state)

    state['current_trasera_idx'] += 1
    cycle_complete = state['current_trasera_idx'] >= len(avail)

    save_state(state)
    return jsonify({'success': True, 'cycle_complete': cycle_complete})


@app.route('/api/prev', methods=['POST'])
def api_prev_trasera():
    """Retrocede a la trasera anterior en el ciclo."""
    state = load_state()

    if state['current_trasera_idx'] > 0:
        state['current_trasera_idx'] -= 1

    save_state(state)
    return jsonify({'success': True})


@app.route('/api/skip', methods=['POST'])
def api_skip():
    """Marca la frontal actual como sin pareja y avanza."""
    state = load_state()

    if state['current_frontal_idx'] < len(state['frontales']):
        frontal = state['frontales'][state['current_frontal_idx']]
        prev_trasera_idx = state['current_trasera_idx']
        state['unpaired_frontales'].append(frontal)
        state['current_frontal_idx'] += 1
        state['current_trasera_idx'] = 0

        state.setdefault('history', []).append({
            'action': 'skip_frontal',
            'frontal': frontal,
            'prev_trasera_idx': prev_trasera_idx,
        })

    save_state(state)
    return jsonify({'success': True})


@app.route('/api/skip_trasera', methods=['POST'])
def api_skip_trasera():
    """Marca la trasera actual como sin pareja frontal y avanza."""
    state = load_state()
    avail = available_traseras(state)

    if 'unpaired_traseras' not in state:
        state['unpaired_traseras'] = []

    if avail and state['current_trasera_idx'] < len(avail):
        trasera = avail[state['current_trasera_idx']]
        prev_trasera_idx = state['current_trasera_idx']
        state['unpaired_traseras'].append(trasera)
        state['paired_traseras'].append(trasera)
        # No reiniciamos a 0 si se sale de rango para que el frontend detecte cycle_complete

        state.setdefault('history', []).append({
            'action': 'skip_trasera',
            'trasera': trasera,
            'prev_trasera_idx': prev_trasera_idx,
        })

    save_state(state)
    return jsonify({'success': True})


@app.route('/api/undo', methods=['POST'])
def api_undo():
    """Deshace la última acción (pair, skip_frontal, skip_trasera)."""
    state = load_state()
    history = state.get('history', [])

    if not history:
        return jsonify({'error': 'No hay acciones que deshacer'}), 400

    last = history.pop()
    action = last['action']

    if action == 'pair':
        frontal = last['frontal']
        trasera = last['trasera']
        folder = last['folder']
        # Quitar de listas
        if frontal in state['paired_frontales']:
            state['paired_frontales'].remove(frontal)
        if trasera in state['paired_traseras']:
            state['paired_traseras'].remove(trasera)
        # Quitar la pareja
        state['pairs'] = [p for p in state['pairs'] if p['folder'] != folder]
        state['pair_counter'] = max(0, state['pair_counter'] - 1)
        # Restaurar índices
        state['current_frontal_idx'] -= 1
        state['current_trasera_idx'] = last.get('prev_trasera_idx', 0)
        # Borrar carpeta
        pair_dir = os.path.join(PAIRED_DIR, folder)
        if os.path.exists(pair_dir):
            shutil.rmtree(pair_dir)

    elif action == 'skip_frontal':
        frontal = last['frontal']
        if frontal in state['unpaired_frontales']:
            state['unpaired_frontales'].remove(frontal)
        state['current_frontal_idx'] -= 1
        state['current_trasera_idx'] = last.get('prev_trasera_idx', 0)

    elif action == 'skip_trasera':
        trasera = last['trasera']
        if trasera in state.get('unpaired_traseras', []):
            state['unpaired_traseras'].remove(trasera)
        if trasera in state['paired_traseras']:
            state['paired_traseras'].remove(trasera)
        state['current_trasera_idx'] = last.get('prev_trasera_idx', 0)

    state['history'] = history
    save_state(state)
    return jsonify({'success': True, 'undone': action})



@app.route('/api/review', methods=['POST'])
def api_review():
    """Reinicia la navegación sin perder parejas existentes."""
    state = load_state()

    # Quitar traseras que estaban en unpaired de paired_traseras
    unpaired_tras = set(state.get('unpaired_traseras', []))
    state['paired_traseras'] = [
        t for t in state['paired_traseras'] if t not in unpaired_tras
    ]

    # Resetear navegación y listas de descartados
    state['current_frontal_idx'] = 0
    state['current_trasera_idx'] = 0
    state['unpaired_frontales'] = []
    state['unpaired_traseras'] = []
    state['history'] = []

    save_state(state)
    return jsonify({'success': True, 'pairs_kept': state['pair_counter']})


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reinicia todo el estado y borra paired_images."""
    # 1. Borrar state.json si existe
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        
    # 2. Borrar y recrear paired_images/ vacía
    if os.path.exists(PAIRED_DIR):
        shutil.rmtree(PAIRED_DIR)
    os.makedirs(PAIRED_DIR, exist_ok=True)
    
    # 3. Llamar a init_state() y guardar el nuevo estado
    new_state = init_state()
    
    # 4. Devolver JSON con métricas
    return jsonify({
        'success': True,
        'frontales': len(new_state['frontales']),
        'traseras': len(new_state['traseras'])
    })


@app.route('/images/frontales/<path:filename>')
def serve_frontal(filename):
    """Sirve imagen frontal rotada 90° a la izquierda."""
    filepath = os.path.join(FRONTALES_DIR, filename)
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


@app.route('/images/traseras/<path:filename>')
def serve_trasera(filename):
    """Sirve imagen trasera rotada 90° a la izquierda y espejada horizontalmente."""
    filepath = os.path.join(TRASERAS_DIR, filename)
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


# ── Main ───────────────────────────────────────────────
if __name__ == '__main__':
    os.makedirs(FRONTALES_DIR, exist_ok=True)
    os.makedirs(TRASERAS_DIR, exist_ok=True)
    os.makedirs(PAIRED_DIR, exist_ok=True)
    print(f"\n  Frontales: {FRONTALES_DIR}")
    print(f"  Traseras:  {TRASERAS_DIR}")
    print(f"  Salida:    {PAIRED_DIR}\n")
    app.run(debug=False, port=5000)
