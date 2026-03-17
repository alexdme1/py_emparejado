"""
video_extraction_service.py — Extracción inteligente de capturas desde vídeos de seguridad.

Usa YOLOv8n para detectar personas en los frames. Cuando no se detectan personas,
captura la ROI con la lógica siguiente:
  - Persona detectada → dejar de capturar
  - Persona desaparece → esperar 0.5s → capturar
  - Sin persona → capturar cada 2s, máximo 5 capturas consecutivas
  - Tras 5 capturas → esperar a que vuelva a aparecer persona
"""

import os
import cv2
import time
import threading
from datetime import datetime, timedelta
from ultralytics import YOLO

# ── Estado del job ──
_job = {
    'running': False,
    'stop_requested': False,
    'status': None,
    'result': None,
    'error': None,
}

_job_lock = threading.Lock()

# ── Modelo YOLO (carga lazy para no ralentizar el arranque) ──
_model = None


def _get_model():
    """Carga YOLOv8n una sola vez (lazy)."""
    global _model
    if _model is None:
        _model = YOLO('yolov8n.pt')
    return _model


def _update_status(status_dict):
    """Actualiza el estado del job de forma thread-safe."""
    with _job_lock:
        _job['status'] = status_dict


def get_job_status():
    """Devuelve el estado actual del job."""
    with _job_lock:
        return {
            'running': _job['running'],
            'status': _job['status'],
            'result': _job['result'],
            'error': _job['error'],
        }


def stop_job():
    """Señala al job que debe parar."""
    with _job_lock:
        _job['stop_requested'] = True


def get_video_first_frame(video_path):
    """
    Devuelve el primer frame del vídeo como JPEG bytes.
    El frame se devuelve TAL CUAL (rotado 90° CW, como viene de la cámara).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, None

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return None, None

    h, w = frame.shape[:2]
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes(), (w, h)


def start_extraction(
    video_path,
    output_dir,
    roi,
    camera_type='delantera',
    confidence=0.5,
    analysis_fps=5,
    cooldown_seconds=0.5,
    capture_interval=2.0,
    max_consecutive=5,
    upload_roboflow=False,
    roboflow_api_key='',
    roboflow_workspace='floresverdnatura',
    roboflow_project='proyecto_h',
):
    """
    Inicia la extracción en un hilo separado.

    Args:
        video_path: Ruta al vídeo .mp4
        output_dir: Carpeta base de salida
        roi: dict con {x, y, width, height} en coordenadas del frame original
        camera_type: 'delantera' o 'trasera'
        confidence: Umbral de confianza YOLO (0-1)
        analysis_fps: FPS objetivo para análisis (~5)
        cooldown_seconds: Espera tras perder persona antes de capturar (0.5s)
        capture_interval: Intervalo entre capturas consecutivas (2s)
        max_consecutive: Máximo de capturas seguidas sin persona (5)
        upload_roboflow: Si True, sube capturas a Roboflow al terminar
        roboflow_api_key: API key de Roboflow
        roboflow_workspace: Workspace de Roboflow
        roboflow_project: Proyecto de Roboflow
    """
    with _job_lock:
        if _job['running']:
            return {'error': 'Ya hay un job en curso'}

        _job['running'] = True
        _job['stop_requested'] = False
        _job['status'] = {'phase': 'loading_model'}
        _job['result'] = None
        _job['error'] = None

    def run_job():
        try:
            result = _process_video(
                video_path=video_path,
                output_dir=output_dir,
                roi=roi,
                camera_type=camera_type,
                confidence=confidence,
                analysis_fps=analysis_fps,
                cooldown_seconds=cooldown_seconds,
                capture_interval=capture_interval,
                max_consecutive=max_consecutive,
            )

            # Upload a Roboflow si se pide
            if upload_roboflow and roboflow_api_key and result.get('captures', []):
                _update_status({'phase': 'uploading_roboflow', 'uploaded': 0})
                try:
                    from backend.services.roboflow_service import upload_to_roboflow
                    camera_output_dir = os.path.join(output_dir, camera_type)
                    upload_result = upload_to_roboflow(
                        camera_output_dir,
                        roboflow_api_key,
                        roboflow_workspace,
                        roboflow_project,
                        batch_prefix=f'video_{camera_type}',
                        progress_callback=_update_status,
                    )
                    result['upload'] = upload_result
                except Exception as e:
                    result['upload_error'] = str(e)

            with _job_lock:
                _job['result'] = result

        except Exception as e:
            with _job_lock:
                _job['error'] = str(e)
        finally:
            with _job_lock:
                _job['running'] = False

    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()
    return {'success': True, 'message': 'Extracción iniciada'}


def _process_video(
    video_path,
    output_dir,
    roi,
    camera_type,
    confidence,
    analysis_fps,
    cooldown_seconds,
    capture_interval,
    max_consecutive,
):
    """
    Procesa un vídeo frame a frame con la máquina de estados de captura.

    Retorna dict con estadísticas y lista de capturas.
    """
    model = _get_model()
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f'No se puede abrir el vídeo: {video_path}')

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frame_skip = max(1, int(video_fps / analysis_fps))

    # Timestamp base: mtime del fichero de vídeo
    video_mtime = os.path.getmtime(video_path)
    video_duration = total_frames / video_fps if video_fps > 0 else 0
    # Asumimos que mtime es el final del vídeo → base = mtime - duración
    base_timestamp = datetime.fromtimestamp(video_mtime - video_duration)

    # Carpeta de salida por tipo de cámara
    camera_output = os.path.join(output_dir, camera_type)
    os.makedirs(camera_output, exist_ok=True)

    # ROI
    rx, ry, rw, rh = roi['x'], roi['y'], roi['width'], roi['height']

    # ── Estado de la máquina ──
    # States: WAITING_PERSON, PERSON_VISIBLE, COOLDOWN, CAPTURING, MAX_REACHED
    state = 'WAITING_PERSON'  # Al principio no sabemos si hay persona
    person_ever_seen = False
    last_person_time = None       # Último instante (en tiempo-vídeo) con persona
    last_capture_time = None      # Último instante de captura
    capture_count = 0             # Capturas consecutivas en esta ronda

    # Stats
    captures = []
    total_persons_detected = 0
    frames_analyzed = 0
    frame_idx = 0

    _update_status({
        'phase': 'processing',
        'frame': 0,
        'total_frames': total_frames,
        'captures': 0,
        'persons_detected': 0,
        'current_state': state,
    })

    while True:
        # Check stop
        with _job_lock:
            if _job['stop_requested']:
                break

        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        # Skip frames para mantener analysis_fps
        if (frame_idx - 1) % frame_skip != 0:
            continue

        frames_analyzed += 1
        current_video_time = frame_idx / video_fps  # segundos desde inicio

        # ── Detección YOLO ──
        # Rotar 90° CCW para que YOLO detecte personas "de pie"
        frame_rotated = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        results = model.predict(
            frame_rotated,
            conf=confidence,
            classes=[0],  # Solo persona (COCO class 0)
            verbose=False,
            imgsz=640,
        )

        person_detected = False
        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None and len(boxes) > 0:
                person_detected = True
                total_persons_detected += 1

        # ── Máquina de estados ──
        if person_detected:
            person_ever_seen = True
            last_person_time = current_video_time
            capture_count = 0  # Reset contador al ver persona
            state = 'PERSON_VISIBLE'

        else:
            if state == 'PERSON_VISIBLE':
                # Persona acaba de desaparecer → cooldown
                state = 'COOLDOWN'

            elif state == 'COOLDOWN':
                # ¿Ha pasado el cooldown de 0.5s?
                elapsed_since_person = current_video_time - (last_person_time or 0)
                if elapsed_since_person >= cooldown_seconds:
                    # Hacer captura
                    cap_name = _save_capture(
                        frame, rx, ry, rw, rh,
                        camera_output, base_timestamp, current_video_time,
                    )
                    captures.append(cap_name)
                    capture_count = 1
                    last_capture_time = current_video_time
                    state = 'CAPTURING'

            elif state == 'CAPTURING':
                if capture_count >= max_consecutive:
                    state = 'MAX_REACHED'
                else:
                    # ¿Han pasado 2 segundos desde última captura?
                    elapsed = current_video_time - (last_capture_time or 0)
                    if elapsed >= capture_interval:
                        cap_name = _save_capture(
                            frame, rx, ry, rw, rh,
                            camera_output, base_timestamp, current_video_time,
                        )
                        captures.append(cap_name)
                        capture_count += 1
                        last_capture_time = current_video_time

            elif state == 'MAX_REACHED':
                # Esperamos a volver a ver persona
                pass

            elif state == 'WAITING_PERSON':
                # Primer inicio: si no vemos persona, empezamos a capturar
                if not person_ever_seen:
                    # No hemos visto persona aún → capturar directamente
                    if last_capture_time is None:
                        cap_name = _save_capture(
                            frame, rx, ry, rw, rh,
                            camera_output, base_timestamp, current_video_time,
                        )
                        captures.append(cap_name)
                        capture_count = 1
                        last_capture_time = current_video_time
                        state = 'CAPTURING'
                    elif current_video_time - last_capture_time >= capture_interval:
                        if capture_count < max_consecutive:
                            cap_name = _save_capture(
                                frame, rx, ry, rw, rh,
                                camera_output, base_timestamp, current_video_time,
                            )
                            captures.append(cap_name)
                            capture_count += 1
                            last_capture_time = current_video_time
                        else:
                            state = 'MAX_REACHED'

        # Update status cada 20 frames analizados
        if frames_analyzed % 20 == 0:
            _update_status({
                'phase': 'processing',
                'frame': frame_idx,
                'total_frames': total_frames,
                'captures': len(captures),
                'persons_detected': total_persons_detected,
                'current_state': state,
                'pct': round(frame_idx / max(total_frames, 1) * 100, 1),
            })

    cap.release()

    _update_status({'phase': 'done', 'captures': len(captures)})

    return {
        'success': True,
        'video': os.path.basename(video_path),
        'camera_type': camera_type,
        'frames_analyzed': frames_analyzed,
        'total_frames': total_frames,
        'persons_detected': total_persons_detected,
        'captures': captures,
        'total_captures': len(captures),
        'output_dir': camera_output,
    }


def _save_capture(frame, rx, ry, rw, rh, output_dir, base_timestamp, video_time):
    """
    Recorta la ROI del frame (sin rotar) y la guarda con nombre compatible con
    el formato de captura de Windows: 'Captura YYYY-MM-DD HH-MM-SS.jpg'
    """
    # Recortar ROI del frame original
    h, w = frame.shape[:2]
    x1 = max(0, int(rx))
    y1 = max(0, int(ry))
    x2 = min(w, int(rx + rw))
    y2 = min(h, int(ry + rh))
    crop = frame[y1:y2, x1:x2]

    # Generar timestamp
    capture_time = base_timestamp + timedelta(seconds=video_time)
    timestamp_str = capture_time.strftime('%Y-%m-%d %H-%M-%S')

    # Nombre único (si hay colisión, añadir ms)
    filename = f'Captura {timestamp_str}.jpg'
    filepath = os.path.join(output_dir, filename)

    # Si ya existe, añadir milisegundos
    if os.path.exists(filepath):
        ms = int((video_time % 1) * 1000)
        filename = f'Captura {timestamp_str}_{ms:03d}.jpg'
        filepath = os.path.join(output_dir, filename)

    cv2.imwrite(filepath, crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return filename
