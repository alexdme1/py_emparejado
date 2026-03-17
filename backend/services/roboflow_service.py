"""
roboflow_service.py — Upload de crops a Roboflow.
Adaptado de 03_upload_to_roboflow.py con API key como parámetro.
"""

import os
import glob


def upload_to_roboflow(crops_dir, api_key, workspace, project, batch_prefix="crops",
                       progress_callback=None):
    """
    Sube los crops a Roboflow.

    Args:
        crops_dir: Carpeta con subcarpetas por categoría
        api_key: API key de Roboflow
        workspace: Nombre del workspace
        project: Nombre del proyecto
        batch_prefix: Prefijo para el batch name
        progress_callback: Función(status_dict) para reportar progreso

    Returns:
        dict con estadísticas
    """
    from roboflow import Roboflow

    rf = Roboflow(api_key=api_key)
    rf_project = rf.workspace(workspace).project(project)

    subfolders = [d for d in os.listdir(crops_dir)
                  if os.path.isdir(os.path.join(crops_dir, d))]

    if not subfolders:
        return {'error': f'No se encontraron subcarpetas en {crops_dir}'}

    total_uploaded = 0
    total_errors = 0
    errors = []

    for folder_name in sorted(subfolders):
        folder_path = os.path.join(crops_dir, folder_name)
        images = glob.glob(os.path.join(folder_path, "*.png"))
        images += glob.glob(os.path.join(folder_path, "*.jpg"))
        images += glob.glob(os.path.join(folder_path, "*.jpeg"))

        for i, img_path in enumerate(images):
            try:
                rf_project.upload(
                    img_path,
                    tag_names=[folder_name],
                    batch_name=f"{batch_prefix}_{folder_name}"
                )
                total_uploaded += 1

                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback({
                        'phase': 'uploading_roboflow',
                        'category': folder_name,
                        'uploaded': total_uploaded,
                        'current': i + 1,
                        'total_in_folder': len(images),
                    })
            except Exception as e:
                total_errors += 1
                errors.append({
                    'file': os.path.basename(img_path),
                    'error': str(e),
                })

    result = {
        'success': True,
        'total_uploaded': total_uploaded,
        'total_errors': total_errors,
        'errors': errors[:20],  # Limitar errores reportados
        'url': f'https://app.roboflow.com/{workspace}/{project}/upload',
    }

    if progress_callback:
        progress_callback({'phase': 'upload_done', 'result': result})

    return result
