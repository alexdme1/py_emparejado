"""
pairing_service.py — Lógica de emparejado de imágenes frontales/traseras.
Port directo del app.py original, extraído como funciones puras.
"""

import os
import re
import json
import shutil
from datetime import datetime
from backend.utils import get_sorted_images
from backend.config import IMAGE_EXTENSIONS, DEFAULT_TIME_WINDOW


# ── State management ──────────────────────────────────


def parse_timestamp(filename: str):
    """Extrae el datetime del nombre de archivo."""
    match = re.search(r'(\d{4}-\d{2}-\d{2})\s(\d{2}-\d{2}-\d{2})', filename)
    if match:
        return datetime.strptime(
            f"{match.group(1)} {match.group(2).replace('-', ':')}",
            "%Y-%m-%d %H:%M:%S"
        )
    return None


def precompute_candidatas(frontales, traseras, time_window_seconds=DEFAULT_TIME_WINDOW):
    """Calcula candidatas por frontal basándose en proximidad temporal."""
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


def load_state(state_file):
    """Carga estado guardado."""
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return None


def save_state(state, state_file):
    """Persiste estado a disco."""
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def init_state(frontales_dir, traseras_dir, state_file):
    """Crea estado inicial escaneando frontales/ y traseras/."""
    frontales = get_sorted_images(frontales_dir)
    traseras = get_sorted_images(traseras_dir)
    state = {
        'frontales_dir': frontales_dir,
        'traseras_dir': traseras_dir,
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
    save_state(state, state_file)
    return state


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


# ── Pair action ───────────────────────────────────────


def do_pair(state, paired_dir, state_file):
    """Empareja la frontal actual con la trasera mostrada."""
    avail = available_traseras(state)

    if state['current_frontal_idx'] >= len(state['frontales']):
        return {'error': 'No quedan frontales'}
    if not avail or state['current_trasera_idx'] >= len(avail):
        return {'error': 'No hay trasera seleccionada'}

    frontal = state['frontales'][state['current_frontal_idx']]
    trasera = avail[state['current_trasera_idx']]

    frontales_dir = state.get('frontales_dir', '')
    traseras_dir = state.get('traseras_dir', '')

    # Crear carpeta numerada
    state['pair_counter'] += 1
    folder_name = f"{state['pair_counter']:03d}"
    pair_dir = os.path.join(paired_dir, folder_name)
    os.makedirs(pair_dir, exist_ok=True)

    # Copiar imágenes
    shutil.copy2(
        os.path.join(frontales_dir, frontal),
        os.path.join(pair_dir, frontal)
    )
    shutil.copy2(
        os.path.join(traseras_dir, trasera),
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

    save_state(state, state_file)
    return {'success': True, 'folder': folder_name}


def do_next_trasera(state, state_file):
    """Avanza a la siguiente trasera."""
    avail = available_traseras(state)
    state['current_trasera_idx'] += 1
    cycle_complete = state['current_trasera_idx'] >= len(avail)
    save_state(state, state_file)
    return {'success': True, 'cycle_complete': cycle_complete}


def do_prev_trasera(state, state_file):
    """Retrocede a la trasera anterior."""
    if state['current_trasera_idx'] > 0:
        state['current_trasera_idx'] -= 1
    save_state(state, state_file)
    return {'success': True}


def do_skip_frontal(state, state_file):
    """Marca la frontal actual como sin pareja y avanza."""
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

    save_state(state, state_file)
    return {'success': True}


def do_skip_trasera(state, state_file):
    """Marca la trasera actual como sin pareja frontal."""
    avail = available_traseras(state)

    if 'unpaired_traseras' not in state:
        state['unpaired_traseras'] = []

    if avail and state['current_trasera_idx'] < len(avail):
        trasera = avail[state['current_trasera_idx']]
        prev_trasera_idx = state['current_trasera_idx']
        state['unpaired_traseras'].append(trasera)
        state['paired_traseras'].append(trasera)

        state.setdefault('history', []).append({
            'action': 'skip_trasera',
            'trasera': trasera,
            'prev_trasera_idx': prev_trasera_idx,
        })

    save_state(state, state_file)
    return {'success': True}


def do_undo(state, paired_dir, state_file):
    """Deshace la última acción."""
    history = state.get('history', [])
    if not history:
        return {'error': 'No hay acciones que deshacer'}

    last = history.pop()
    action = last['action']

    if action == 'pair':
        frontal = last['frontal']
        trasera = last['trasera']
        folder = last['folder']
        if frontal in state['paired_frontales']:
            state['paired_frontales'].remove(frontal)
        if trasera in state['paired_traseras']:
            state['paired_traseras'].remove(trasera)
        state['pairs'] = [p for p in state['pairs'] if p['folder'] != folder]
        state['pair_counter'] = max(0, state['pair_counter'] - 1)
        state['current_frontal_idx'] -= 1
        state['current_trasera_idx'] = last.get('prev_trasera_idx', 0)
        pair_dir = os.path.join(paired_dir, folder)
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
    save_state(state, state_file)
    return {'success': True, 'undone': action}


def do_review(state, state_file):
    """Reinicia la navegación sin perder parejas existentes."""
    unpaired_tras = set(state.get('unpaired_traseras', []))
    state['paired_traseras'] = [
        t for t in state['paired_traseras'] if t not in unpaired_tras
    ]
    state['current_frontal_idx'] = 0
    state['current_trasera_idx'] = 0
    state['unpaired_frontales'] = []
    state['unpaired_traseras'] = []
    state['history'] = []

    save_state(state, state_file)
    return {'success': True, 'pairs_kept': state['pair_counter']}


def do_reset(paired_dir, frontales_dir, traseras_dir, state_file):
    """Reinicia todo el estado y borra paired_images."""
    if os.path.exists(state_file):
        os.remove(state_file)
    if os.path.exists(paired_dir):
        shutil.rmtree(paired_dir)
    os.makedirs(paired_dir, exist_ok=True)

    new_state = init_state(frontales_dir, traseras_dir, state_file)
    return {
        'success': True,
        'frontales': len(new_state['frontales']),
        'traseras': len(new_state['traseras'])
    }


def get_state_for_frontend(state, state_file):
    """Prepara el estado para enviar al frontend."""
    if 'candidatas_por_frontal' not in state:
        state['candidatas_por_frontal'] = precompute_candidatas(
            state.get('frontales', []), state.get('traseras', [])
        )

    advance_past_paired(state)
    save_state(state, state_file)

    avail = available_traseras(state)

    if state['current_frontal_idx'] >= len(state['frontales']):
        return {
            'completed': True,
            'total_pairs': state['pair_counter'],
            'unpaired': state['unpaired_frontales'],
            'total_frontales': len(state['frontales']),
        }

    current_frontal = state['frontales'][state['current_frontal_idx']]

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

    return {
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
    }
