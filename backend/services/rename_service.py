"""
rename_service.py — Renombra imágenes emparejadas a formato NF/NB.
Adaptado de rename_pairs.py como funciones invocables.
"""

import json
import shutil
import cv2
from pathlib import Path

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}


def load_pairs(state_file: str) -> dict:
    """
    Carga state.json y construye un diccionario:
        { "001": {"frontal": "nombre_sin_ext", "trasera": "nombre_sin_ext"}, ... }
    """
    with open(state_file, 'r') as f:
        state = json.load(f)

    lookup = {}
    for pair in state.get('pairs', []):
        folder = pair['folder']
        frontal_stem = Path(pair['frontal']).stem
        trasera_stem = Path(pair['trasera']).stem
        lookup[folder] = {
            'frontal': frontal_stem,
            'trasera': trasera_stem,
        }

    return lookup


def rename_folder(folder_path: Path, folder_name: str, pair_info: dict,
                  out_dir: Path, dry_run: bool = False) -> dict:
    """
    Renombra los archivos dentro de una carpeta de predicciones y los mueve a out_dir.
    """
    renamed = 0
    skipped = 0

    frontal_stem = pair_info['frontal']
    trasera_stem = pair_info['trasera']

    try:
        folder_num = str(int(folder_name))
    except ValueError:
        folder_num = folder_name

    # Renombrar imágenes
    for f in list(folder_path.iterdir()):
        if f.is_dir():
            continue

        stem = f.stem
        ext = f.suffix

        if stem == frontal_stem:
            new_name = f'{folder_num}F{ext}'
            is_trasera = False
        elif stem == trasera_stem:
            new_name = f'{folder_num}B{ext}'
            is_trasera = True
        else:
            skipped += 1
            continue

        new_path = out_dir / new_name
        if dry_run:
            pass
        else:
            img = cv2.imread(str(f))
            if img is not None:
                img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                if is_trasera:
                    img = cv2.flip(img, 1)
                cv2.imwrite(str(new_path), img)
                f.unlink()
            else:
                shutil.move(str(f), str(new_path))

        renamed += 1

    # Renombrar labels (si existen)
    labels_dir = folder_path / 'labels'
    if labels_dir.exists():
        for f in list(labels_dir.iterdir()):
            if f.is_dir():
                continue

            stem = f.stem
            ext = f.suffix

            if stem == frontal_stem:
                new_name = f'{folder_num}F{ext}'
                is_trasera = False
            elif stem == trasera_stem:
                new_name = f'{folder_num}B{ext}'
                is_trasera = True
            else:
                skipped += 1
                continue

            new_path = out_dir / new_name
            if not dry_run:
                try:
                    with open(f, 'r') as lbl_f:
                        lines = lbl_f.readlines()

                    new_lines = []
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            cls = parts[0]
                            x, y, w, h = map(float, parts[1:5])

                            if is_trasera:
                                new_x = 1.0 - y
                                new_y = 1.0 - x
                                new_w = h
                                new_h = w
                            else:
                                new_x = y
                                new_y = 1.0 - x
                                new_w = h
                                new_h = w

                            extra = " ".join(parts[5:])
                            if extra:
                                new_lines.append(f"{cls} {new_x:.6f} {new_y:.6f} {new_w:.6f} {new_h:.6f} {extra}\n")
                            else:
                                new_lines.append(f"{cls} {new_x:.6f} {new_y:.6f} {new_w:.6f} {new_h:.6f}\n")

                    with open(new_path, 'w') as out_f:
                        out_f.writelines(new_lines)

                    f.unlink()
                except Exception:
                    shutil.move(str(f), str(new_path))
            renamed += 1

        if not dry_run:
            try:
                labels_dir.rmdir()
            except OSError:
                pass

    if not dry_run:
        try:
            folder_path.rmdir()
        except OSError:
            pass

    return {'renamed': renamed, 'skipped': skipped}


def run_rename(input_dir, output_dir, state_file, dry_run=False):
    """
    Ejecuta el renombrado completo de parejas.

    Returns:
        dict con estadísticas
    """
    input_path = Path(input_dir)
    out_path = Path(output_dir)

    if not input_path.exists():
        return {'error': f'Carpeta no encontrada: {input_path}'}

    if not Path(state_file).exists():
        return {'error': f'State file no encontrado: {state_file}'}

    if not dry_run:
        out_path.mkdir(parents=True, exist_ok=True)

    pairs = load_pairs(state_file)
    total_renamed = 0
    total_skipped = 0
    processed_folders = []

    subfolders = sorted([d for d in input_path.iterdir() if d.is_dir()])

    for folder in subfolders:
        folder_name = folder.name

        if folder_name not in pairs:
            continue

        stats = rename_folder(folder, folder_name, pairs[folder_name], out_path, dry_run=dry_run)

        processed_folders.append({
            'folder': folder_name,
            'renamed': stats['renamed'],
            'skipped': stats['skipped'],
        })

        total_renamed += stats['renamed']
        total_skipped += stats['skipped']

    return {
        'success': True,
        'total_renamed': total_renamed,
        'total_skipped': total_skipped,
        'folders_processed': len(processed_folders),
        'details': processed_folders,
    }
