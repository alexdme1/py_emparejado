#!/usr/bin/env python3
"""
Renombrar las imágenes predichas a formato NNN_F / NNN_B
=========================================================
Lee state.json para saber qué imagen es frontal y cuál trasera
en cada carpeta, y renombra los archivos (imágenes + labels) al
formato:
    001_F.jpg  /  001_B.jpg
    001_F.txt  /  001_B.txt

Uso:
    python rename_pairs.py                               # defaults
    python rename_pairs.py --input runs/detect/predicted_pairs
"""

from pathlib import Path
import json
import argparse
import shutil
import cv2

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

STATE_FILE  = 'state.json'
# Por defecto ahora procesamos la carpeta de las parejas (paired_images)
DEFAULT_INPUT = 'paired_images'
DEFAULT_OUTPUT = 'dataset_final'

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}


def load_pairs(state_file: str) -> dict:
    """
    Carga state.json y construye un diccionario:
        { "001": {"frontal": "nombre_original_sin_ext", "trasera": "nombre_original_sin_ext"}, ... }
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


def rename_folder(folder_path: Path, folder_name: str, pair_info: dict, out_dir: Path, dry_run: bool = False) -> dict:
    """
    Renombra los archivos dentro de una carpeta de predicciones y los mueve a out_dir.
    
    Returns:
        dict con estadísticas
    """
    renamed = 0
    skipped = 0

    frontal_stem = pair_info['frontal']
    trasera_stem = pair_info['trasera']

    # Extract numeric value if possible
    try:
        folder_num = str(int(folder_name))
    except ValueError:
        folder_num = folder_name

    # Renombrar imágenes en la carpeta raíz
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
            print(f'     [DRY] {f.name}  →  {new_path} (Rotacion 90 CCW)')
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

    # Renombrar labels (si existen) y adecuarlas a la rotación
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

            # Para los labels, los guardamos en la misma carpeta final de salida
            new_path = out_dir / new_name
            if dry_run:
                print(f'     [DRY] labels/{f.name}  →  {new_path} (Rotated annotations)')
            else:
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
                except Exception as e:
                    print(f"       [WARN] Error procesando label {f.name}: {e}")
                    shutil.move(str(f), str(new_path))
            renamed += 1
            
        # Intentar borrar el dir original de labels si quedó vacío
        if not dry_run:
            try:
                labels_dir.rmdir()
            except OSError:
                pass

    # Intentar borrar el folder original si quedó vacío
    if not dry_run:
        try:
            folder_path.rmdir()
        except OSError:
            pass

    return {'renamed': renamed, 'skipped': skipped}


def main():
    parser = argparse.ArgumentParser(description='Renombrar predicciones a formato NNN_F/NNN_B')
    parser.add_argument('--input', default=DEFAULT_INPUT, help=f'Carpeta de predicciones (default: {DEFAULT_INPUT})')
    parser.add_argument('--output', default=DEFAULT_OUTPUT, help=f'Carpeta de salida (default: {DEFAULT_OUTPUT})')
    parser.add_argument('--state', default=STATE_FILE, help=f'Archivo de estado (default: {STATE_FILE})')
    parser.add_argument('--dry-run', action='store_true', help='Solo mostrar qué haría, sin renombrar')
    args = parser.parse_args()

    input_dir = Path(args.input)
    out_dir = Path(args.output)

    if not input_dir.exists():
        print(f'❌ Carpeta no encontrada: {input_dir}')
        return

    if not Path(args.state).exists():
        print(f'❌ State file no encontrado: {args.state}')
        return

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # Cargar parejas
    pairs = load_pairs(args.state)
    print(f'\n{"=" * 60}')
    print(f'  📝 Renombrando predicciones')
    print(f'{"=" * 60}')
    print(f'   Entrada:  {input_dir}/')
    print(f'   Salida:   {out_dir}/')
    print(f'   Parejas:  {len(pairs)}')
    if args.dry_run:
        print(f'   ⚠️  MODO DRY-RUN (no se renombra nada)')
    print()

    total_renamed = 0
    total_skipped = 0

    subfolders = sorted([d for d in input_dir.iterdir() if d.is_dir()])

    for folder in subfolders:
        folder_name = folder.name

        if folder_name not in pairs:
            print(f'   ⚠️  {folder_name}/ — sin info de pareja en state.json, saltando')
            continue

        stats = rename_folder(folder, folder_name, pairs[folder_name], out_dir, dry_run=args.dry_run)

        icon = '✅' if stats['renamed'] > 0 else '⬚ '
        print(f'   {icon} {folder_name}/  →  {stats["renamed"]} renombrados')

        total_renamed += stats['renamed']
        total_skipped += stats['skipped']

    print(f'\n{"─" * 60}')
    print(f'   Total renombrados: {total_renamed}')
    print(f'   Total saltados:    {total_skipped}')
    print()


if __name__ == '__main__':
    main()
