import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Toast, { showToast } from '../components/Toast'
import FolderPicker from '../components/FolderPicker'

const apiPost = async (endpoint, body = {}) => {
  const res = await fetch('/api/' + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return res.json()
}

export default function VideoExtraction() {
  const navigate = useNavigate()

  // ── Config ──
  const [videoPath, setVideoPath] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [cameraType, setCameraType] = useState('delantera')
  const [confidence, setConfidence] = useState(0.5)
  const [uploadRoboflow, setUploadRoboflow] = useState(false)
  const [apiKey, setApiKey] = useState('')

  // ── Preview & ROI ──
  const [previewFrame, setPreviewFrame] = useState(null)
  const [frameWidth, setFrameWidth] = useState(0)
  const [frameHeight, setFrameHeight] = useState(0)
  const [loadingPreview, setLoadingPreview] = useState(false)

  // ROI state (in frame coordinates)
  const [roi, setRoi] = useState({ x: 100, y: 100, width: 400, height: 400 })
  const [roiSet, setRoiSet] = useState(false)
  const canvasRef = useRef(null)
  const imgRef = useRef(null)

  // ROI drag state
  const [dragging, setDragging] = useState(false)
  const [resizing, setResizing] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  // ── Job state ──
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // ── Pick video file ──
  const pickVideo = async () => {
    try {
      const res = await apiPost('video/pick_file', {})
      if (res.success && res.path) {
        setVideoPath(res.path)
        loadPreview(res.path)
      }
    } catch (e) {
      showToast('Error al seleccionar vídeo', 'error')
    }
  }

  // ── Load preview frame ──
  const loadPreview = async (path) => {
    if (!path) return
    setLoadingPreview(true)
    setPreviewFrame(null)
    try {
      const res = await apiPost('video/preview', { video_path: path })
      if (res.success) {
        setPreviewFrame(res.frame)
        setFrameWidth(res.width)
        setFrameHeight(res.height)
        // Default ROI: center 40% of frame
        const rw = Math.round(res.width * 0.4)
        const rh = Math.round(res.height * 0.4)
        setRoi({
          x: Math.round((res.width - rw) / 2),
          y: Math.round((res.height - rh) / 2),
          width: rw,
          height: rh,
        })
        setRoiSet(true)
      } else {
        showToast(res.error || 'Error cargando preview', 'error')
      }
    } catch (e) {
      showToast('Error de conexión', 'error')
    }
    setLoadingPreview(false)
  }

  // ── Draw ROI on canvas ──
  useEffect(() => {
    if (!previewFrame || !canvasRef.current || !imgRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const img = imgRef.current

    const draw = () => {
      // Scale factor from rendered size to actual frame size
      const renderedWidth = canvas.clientWidth
      const renderedHeight = canvas.clientHeight
      canvas.width = renderedWidth
      canvas.height = renderedHeight

      const scaleX = renderedWidth / frameWidth
      const scaleY = renderedHeight / frameHeight

      ctx.clearRect(0, 0, renderedWidth, renderedHeight)
      ctx.drawImage(img, 0, 0, renderedWidth, renderedHeight)

      // Dark overlay
      ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
      ctx.fillRect(0, 0, renderedWidth, renderedHeight)

      // Clear ROI area (show original)
      const rx = roi.x * scaleX
      const ry = roi.y * scaleY
      const rw = roi.width * scaleX
      const rh = roi.height * scaleY

      ctx.save()
      ctx.beginPath()
      ctx.rect(rx, ry, rw, rh)
      ctx.clip()
      ctx.drawImage(img, 0, 0, renderedWidth, renderedHeight)
      ctx.restore()

      // ROI border
      ctx.strokeStyle = '#4a9eff'
      ctx.lineWidth = 2
      ctx.strokeRect(rx, ry, rw, rh)

      // Corner handles
      const hs = 8
      ctx.fillStyle = '#4a9eff'
      ;[
        [rx - hs/2, ry - hs/2], [rx + rw - hs/2, ry - hs/2],
        [rx - hs/2, ry + rh - hs/2], [rx + rw - hs/2, ry + rh - hs/2],
      ].forEach(([hx, hy]) => {
        ctx.fillRect(hx, hy, hs, hs)
      })

      // Label
      ctx.fillStyle = 'rgba(74, 158, 255, 0.9)'
      ctx.font = '12px Inter, sans-serif'
      ctx.fillText(`ROI: ${roi.width}×${roi.height}`, rx + 4, ry - 6)
    }

    if (img.complete) {
      draw()
    } else {
      img.onload = draw
    }
  }, [previewFrame, roi, frameWidth, frameHeight])

  // ── Canvas mouse handlers ──
  const getFrameCoords = (e) => {
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const scaleX = frameWidth / canvas.clientWidth
    const scaleY = frameHeight / canvas.clientHeight
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    }
  }

  const isInResizeHandle = (fx, fy) => {
    const margin = 20
    const rx2 = roi.x + roi.width
    const ry2 = roi.y + roi.height
    return (
      Math.abs(fx - rx2) < margin && Math.abs(fy - ry2) < margin
    )
  }

  const isInRoi = (fx, fy) => {
    return fx >= roi.x && fx <= roi.x + roi.width &&
           fy >= roi.y && fy <= roi.y + roi.height
  }

  const handleMouseDown = (e) => {
    const { x, y } = getFrameCoords(e)
    if (isInResizeHandle(x, y)) {
      setResizing(true)
      setDragStart({ x, y })
    } else if (isInRoi(x, y)) {
      setDragging(true)
      setDragStart({ x: x - roi.x, y: y - roi.y })
    }
  }

  const handleMouseMove = (e) => {
    if (!dragging && !resizing) return
    const { x, y } = getFrameCoords(e)

    if (dragging) {
      setRoi(prev => ({
        ...prev,
        x: Math.max(0, Math.min(frameWidth - prev.width, x - dragStart.x)),
        y: Math.max(0, Math.min(frameHeight - prev.height, y - dragStart.y)),
      }))
    } else if (resizing) {
      setRoi(prev => ({
        ...prev,
        width: Math.max(50, Math.min(frameWidth - prev.x, x - prev.x)),
        height: Math.max(50, Math.min(frameHeight - prev.y, y - prev.y)),
      }))
    }
  }

  const handleMouseUp = () => {
    setDragging(false)
    setResizing(false)
  }

  // ── Start extraction ──
  const startExtraction = async () => {
    if (!videoPath) { showToast('Selecciona un vídeo', 'warning'); return }
    if (!outputDir) { showToast('Selecciona carpeta de salida', 'warning'); return }
    if (!roiSet) { showToast('Carga un vídeo para configurar la ROI', 'warning'); return }
    if (uploadRoboflow && !apiKey) { showToast('Introduce API Key de Roboflow', 'warning'); return }

    setRunning(true)
    setResult(null)
    setError(null)
    setStatus({ phase: 'starting' })

    try {
      const res = await apiPost('video/start', {
        video_path: videoPath,
        output_dir: outputDir,
        camera_type: cameraType,
        roi,
        confidence,
        upload_roboflow: uploadRoboflow,
        roboflow_api_key: apiKey,
        roboflow_workspace: 'floresverdnatura',
        roboflow_project: 'proyecto_h',
      })

      if (res.error) {
        showToast(res.error, 'error')
        setError(res.error)
        setRunning(false)
        return
      }

      // Poll status
      const poll = setInterval(async () => {
        try {
          const st = await fetch('/api/video/status').then(r => r.json())
          setStatus(st.status)
          if (!st.running) {
            clearInterval(poll)
            setRunning(false)
            if (st.error) {
              setError(st.error)
              showToast(`❌ ${st.error}`, 'error')
            } else if (st.result) {
              setResult(st.result)
              showToast(`✅ ${st.result.total_captures} capturas extraídas`)
            }
          }
        } catch {
          clearInterval(poll)
          setRunning(false)
        }
      }, 1000)
    } catch (e) {
      showToast('Error de conexión', 'error')
      setRunning(false)
    }
  }

  const stopExtraction = async () => {
    await apiPost('video/stop')
    showToast('Deteniendo...', 'warning')
  }

  // ── Phase label ──
  const getPhaseLabel = () => {
    if (!status) return ''
    const s = status
    switch (s.phase) {
      case 'loading_model': return '🧠 Cargando modelo YOLOv8n...'
      case 'processing':
        return `🔍 Frame ${s.frame || 0}/${s.total_frames || '?'} · ${s.captures || 0} capturas · ${s.persons_detected || 0} personas`
      case 'uploading_roboflow': return `☁️ Subiendo a Roboflow (${s.uploaded || 0})`
      case 'done': return `✅ Completado (${s.captures || 0} capturas)`
      default: return s.phase || ''
    }
  }

  const getStateLabel = () => {
    if (!status || !status.current_state) return ''
    const labels = {
      WAITING_PERSON: '👀 Esperando persona...',
      PERSON_VISIBLE: '🚶 Persona visible',
      COOLDOWN: '⏱️ Cooldown 0.5s...',
      CAPTURING: '📸 Capturando',
      MAX_REACHED: '⏸️ Máximo alcanzado (5)',
    }
    return labels[status.current_state] || status.current_state
  }

  // ── Hidden image for canvas drawing ──
  const frameUrl = previewFrame ? `data:image/jpeg;base64,${previewFrame}` : null

  return (
    <div style={s.container}>
      <Toast />
      <div style={s.box}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')} style={{ alignSelf: 'flex-start', marginBottom: 16 }}>
          ← Volver
        </button>

        <h1 style={s.title}>📹 Extracción de Vídeo</h1>
        <p style={s.subtitle}>
          Extrae capturas automáticas de vídeos de cámaras de seguridad usando detección de personas
        </p>

        {/* Video picker */}
        <div style={s.section}>
          <h3 style={s.sectionTitle}>🎬 Vídeo</h3>
          <div className="input-group">
            <label>Archivo de vídeo (.mp4)</label>
            <div className="folder-picker">
              <input
                type="text"
                className="input"
                value={videoPath}
                onChange={e => setVideoPath(e.target.value)}
                placeholder="/ruta/al/video.mp4"
                onBlur={() => videoPath && loadPreview(videoPath)}
              />
              <button className="btn btn-sm" onClick={pickVideo} title="Explorar..." style={{ flexShrink: 0 }}>
                🎬
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
            <div className="input-group" style={{ flex: 1 }}>
              <label>Tipo de cámara</label>
              <select
                value={cameraType}
                onChange={e => setCameraType(e.target.value)}
                style={{
                  padding: '10px 14px', background: 'var(--bg-primary)',
                  border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: 14,
                }}
              >
                <option value="delantera">📷 Delantera</option>
                <option value="trasera">📷 Trasera</option>
              </select>
            </div>
            <FolderPicker id="vid-output" label="Carpeta de salida" value={outputDir} onChange={setOutputDir} />
          </div>
        </div>

        {/* ROI Selection */}
        {loadingPreview && (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <span className="spinner" style={{ display: 'inline-block' }} />
            <p style={{ color: 'var(--text-muted)', marginTop: 8 }}>Cargando preview...</p>
          </div>
        )}

        {previewFrame && (
          <div style={s.section}>
            <h3 style={s.sectionTitle}>🔲 Selección de ROI <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(arrastra para mover, esquina inferior derecha para redimensionar)</span></h3>
            <div style={s.canvasContainer}>
              <img
                ref={imgRef}
                src={frameUrl}
                alt="preview"
                style={{ display: 'none' }}
                crossOrigin="anonymous"
              />
              <canvas
                ref={canvasRef}
                style={s.canvas}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              />
            </div>
            <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
              <span>Posición: ({roi.x}, {roi.y})</span>
              <span>Tamaño: {roi.width} × {roi.height}</span>
              <span>Frame: {frameWidth} × {frameHeight}</span>
            </div>
          </div>
        )}

        {/* Parameters */}
        <div style={s.section}>
          <h3 style={s.sectionTitle}>⚙️ Configuración</h3>
          <div className="input-group">
            <label>Confianza YOLO: {Math.round(confidence * 100)}%</label>
            <input
              type="range" min="0.1" max="0.95" step="0.05"
              value={confidence}
              onChange={e => setConfidence(parseFloat(e.target.value))}
              style={{ accentColor: 'var(--accent-blue)' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
              <span>10%</span><span>50%</span><span>95%</span>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14 }}>
              <input
                type="checkbox"
                checked={uploadRoboflow}
                onChange={e => setUploadRoboflow(e.target.checked)}
                style={{ accentColor: 'var(--accent-green)' }}
              />
              ☁️ Subir capturas a Roboflow automáticamente
            </label>
          </div>

          {uploadRoboflow && (
            <div className="input-group" style={{ marginTop: 12 }}>
              <label>API Key de Roboflow *</label>
              <input
                type="password"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="Tu API key de Roboflow"
              />
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Workspace: floresverdnatura · Proyecto: proyecto_h
              </span>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            className="btn btn-success btn-lg"
            onClick={startExtraction}
            disabled={running}
            style={{ flex: 1 }}
          >
            {running ? (
              <><span className="spinner" /> Procesando...</>
            ) : (
              '🚀 Iniciar Extracción'
            )}
          </button>
          {running && (
            <button className="btn btn-danger btn-lg" onClick={stopExtraction}>
              ⏹ Detener
            </button>
          )}
        </div>

        {/* Status */}
        {running && status && (
          <div className="card" style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 14 }}>{getPhaseLabel()}</span>
              <span style={{ fontSize: 12, padding: '3px 10px', borderRadius: 8, background: 'var(--bg-tertiary)', color: 'var(--accent-blue)' }}>
                {getStateLabel()}
              </span>
            </div>
            {status.pct !== undefined && (
              <div className="progress-bar" style={{ height: 6 }}>
                <div className="progress-fill" style={{ width: `${status.pct}%` }} />
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card" style={{ marginTop: 16, borderColor: 'var(--accent-red)' }}>
            <p style={{ color: 'var(--accent-red)', fontSize: 14 }}>❌ {error}</p>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="card" style={{ marginTop: 16, borderColor: 'var(--accent-green)' }}>
            <h3 style={{ fontSize: 16, color: 'var(--accent-green)', marginBottom: 12 }}>
              ✅ Extracción completada
            </h3>
            <div style={s.resultGrid}>
              <div className="stat"><div className="stat-dot green" /> Capturas: <strong>{result.total_captures}</strong></div>
              <div className="stat"><div className="stat-dot blue" /> Frames analizados: <strong>{result.frames_analyzed}</strong></div>
              <div className="stat"><div className="stat-dot purple" /> Personas detectadas: <strong>{result.persons_detected}</strong></div>
              <div className="stat"><div className="stat-dot orange" /> Cámara: <strong>{result.camera_type}</strong></div>
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12 }}>
              📁 Guardadas en: {result.output_dir}
            </p>

            {result.upload && (
              <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 8, background: 'var(--bg-tertiary)' }}>
                <p style={{ fontSize: 13, color: 'var(--accent-green)' }}>
                  ☁️ Subidas a Roboflow: <strong>{result.upload.total_uploaded}</strong>
                </p>
              </div>
            )}
            {result.upload_error && (
              <p style={{ fontSize: 13, color: 'var(--accent-red)', marginTop: 8 }}>
                ⚠ Error upload: {result.upload_error}
              </p>
            )}

            {result.captures && result.captures.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <h4 style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>
                  Capturas ({result.captures.length}):
                </h4>
                <div style={{ maxHeight: 120, overflowY: 'auto', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.8 }}>
                  {result.captures.map((c, i) => (
                    <div key={i}>📷 {c}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

const s = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    padding: '40px 20px',
    background: 'radial-gradient(ellipse at 50% 0%, rgba(251, 191, 36, 0.06) 0%, transparent 50%), var(--bg-primary)',
  },
  box: {
    display: 'flex',
    flexDirection: 'column',
    maxWidth: 700,
    width: '100%',
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-xl)',
    padding: '32px',
  },
  title: {
    fontSize: 26,
    fontWeight: 700,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: 'var(--text-secondary)',
    marginBottom: 24,
    lineHeight: 1.5,
  },
  section: {
    marginBottom: 20,
    padding: '16px 0',
    borderTop: '1px solid var(--border-primary)',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 12,
    color: 'var(--text-secondary)',
  },
  canvasContainer: {
    position: 'relative',
    borderRadius: 'var(--radius-md)',
    overflow: 'hidden',
    border: '1px solid var(--border-primary)',
    background: '#000',
  },
  canvas: {
    display: 'block',
    width: '100%',
    cursor: 'crosshair',
  },
  resultGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px 16px',
  },
}
