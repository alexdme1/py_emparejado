"""
drive_service.py — Upload a Google Drive.
Preparado para integración con credenciales OAuth.
De momento es un placeholder funcional que se activará
cuando el usuario proporcione las credenciales.
"""

import os
import re


def get_last_drive_index(service, folder_id):
    """
    Consulta la carpeta de Drive para obtener el último índice de archivo.
    Busca archivos con formato NF.ext o NB.ext y devuelve el mayor N.
    """
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(name)",
        pageSize=1000,
    ).execute()

    files = results.get('files', [])
    max_index = 0

    pattern = re.compile(r'^(\d+)[FB]\.')
    for f in files:
        match = pattern.match(f['name'])
        if match:
            idx = int(match.group(1))
            if idx > max_index:
                max_index = idx

    return max_index


def upload_to_drive(dataset_dir, credentials_path, folder_id,
                    start_index=None, progress_callback=None):
    """
    Sube los archivos renombrados a Google Drive.

    Args:
        dataset_dir: Carpeta con archivos NF/NB
        credentials_path: Ruta al archivo credentials.json de Google
        folder_id: ID de la carpeta de destino en Drive
        start_index: Índice inicial (si None, se calcula desde Drive)
        progress_callback: Función de progreso

    Returns:
        dict con estadísticas
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import pickle
    except ImportError:
        return {
            'error': 'Dependencias de Google Drive no instaladas. '
                     'Ejecuta: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib'
        }

    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    # Autenticación
    creds = None
    token_path = os.path.join(os.path.dirname(credentials_path), 'token.pickle')

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    # Obtener último índice si no se proporciona
    if start_index is None:
        start_index = get_last_drive_index(service, folder_id)

    if progress_callback:
        progress_callback({
            'phase': 'drive_starting',
            'last_index': start_index,
        })

    # Listar archivos locales a subir
    if not os.path.isdir(dataset_dir):
        return {'error': f'Carpeta no encontrada: {dataset_dir}'}

    files_to_upload = sorted([
        f for f in os.listdir(dataset_dir)
        if os.path.isfile(os.path.join(dataset_dir, f))
    ])

    # Renumerar archivos para que continúen la secuencia del Drive
    pattern = re.compile(r'^(\d+)([FB])(\..+)$')
    local_indices = {}
    for fname in files_to_upload:
        match = pattern.match(fname)
        if match:
            local_idx = int(match.group(1))
            if local_idx not in local_indices:
                local_indices[local_idx] = []
            local_indices[local_idx].append(fname)

    uploaded = 0
    errors = []
    new_index = start_index

    for local_idx in sorted(local_indices.keys()):
        new_index += 1
        for fname in local_indices[local_idx]:
            match = pattern.match(fname)
            if not match:
                continue

            side = match.group(2)   # F or B
            ext = match.group(3)
            new_name = f"{new_index}{side}{ext}"

            file_path = os.path.join(dataset_dir, fname)
            file_metadata = {
                'name': new_name,
                'parents': [folder_id],
            }
            media = MediaFileUpload(file_path, resumable=True)

            try:
                service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                uploaded += 1

                if progress_callback:
                    progress_callback({
                        'phase': 'uploading_drive',
                        'uploaded': uploaded,
                        'total': len(files_to_upload),
                        'current_file': new_name,
                    })
            except Exception as e:
                errors.append({'file': fname, 'error': str(e)})

    return {
        'success': True,
        'uploaded': uploaded,
        'last_index': new_index,
        'errors': errors,
    }
