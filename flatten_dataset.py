import os
import shutil
from pathlib import Path

INPUT_DIR = Path('paired_images')
OUTPUT_DIR = Path('dataset_final')

def flatten_dataset():
    if not INPUT_DIR.exists():
        print(f"La carpeta {INPUT_DIR} no existe.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    moved_files = 0
    folders_removed = 0

    print(f"Recolectando archivos de {INPUT_DIR}/ y moviéndolos a {OUTPUT_DIR}/...\n")

    for subfolder in sorted(INPUT_DIR.iterdir()):
        if not subfolder.is_dir():
            continue
            
        # Mover todos los archivos de la raíz de la subcarpeta
        for file in subfolder.iterdir():
            if file.is_file():
                dest_path = OUTPUT_DIR / file.name
                # Si por algún motivo ya existe, le ponemos un sufijo o lo sobrescribimos.
                # Aquí lo sobrescribimos directamente
                shutil.move(str(file), str(dest_path))
                moved_files += 1
                
        # Mover archivos de la carpeta labels/ si existe
        labels_dir = subfolder / 'labels'
        if labels_dir.exists():
            for lbl_file in labels_dir.iterdir():
                if lbl_file.is_file():
                    dest_path = OUTPUT_DIR / lbl_file.name
                    shutil.move(str(lbl_file), str(dest_path))
                    moved_files += 1
            # intentar borrar labels/
            try:
                labels_dir.rmdir()
            except OSError:
                pass
                
        # Intentar borrar la subcarpeta si quedó vacía
        try:
            subfolder.rmdir()
            folders_removed += 1
        except OSError:
            pass

    print(f"¡Finalizado!")
    print(f"✅ Se movieron {moved_files} archivos en total a la carpeta '{OUTPUT_DIR}/'.")
    print(f"✅ Se limpiaron y eliminaron {folders_removed} subcarpetas de origen que quedaron vacías.")

if __name__ == '__main__':
    flatten_dataset()
