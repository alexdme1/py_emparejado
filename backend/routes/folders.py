"""
routes/folders.py — Endpoint para selección de carpetas mediante diálogo nativo.
"""

import os
import threading
from flask import Blueprint, jsonify, request

folders_bp = Blueprint('folders', __name__)

# Almacén temporal para la última carpeta seleccionada
_pick_result = {
    'pending': False,
    'path': None,
}


@folders_bp.route('/api/folders/pick', methods=['POST'])
def pick_folder():
    """
    Abre un diálogo nativo de selección de carpetas.
    Opcionalmente acepta `initial_dir` en el body para la ruta inicial.
    """
    data = request.json or {}
    initial_dir = data.get('initial_dir', os.path.expanduser('~'))
    title = data.get('title', 'Seleccionar carpeta')

    selected = [None]

    def open_dialog():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askdirectory(
                initialdir=initial_dir,
                title=title,
            )
            root.destroy()
            selected[0] = path if path else None
        except Exception as e:
            selected[0] = None

    # tkinter debe ejecutarse en el hilo principal en algunos SOs,
    # pero en Linux generalmente funciona en threads
    dialog_thread = threading.Thread(target=open_dialog)
    dialog_thread.start()
    dialog_thread.join(timeout=120)  # 2 min timeout

    if selected[0]:
        return jsonify({'success': True, 'path': selected[0]})
    else:
        return jsonify({'success': False, 'path': None, 'message': 'No se seleccionó carpeta'})


@folders_bp.route('/api/folders/validate', methods=['POST'])
def validate_folder():
    """Valida que una ruta de carpeta existe."""
    data = request.json or {}
    path = data.get('path', '')

    if not path:
        return jsonify({'valid': False, 'message': 'Ruta vacía'})

    exists = os.path.isdir(path)
    return jsonify({
        'valid': exists,
        'path': path,
        'message': 'Carpeta válida' if exists else 'Carpeta no encontrada',
    })
