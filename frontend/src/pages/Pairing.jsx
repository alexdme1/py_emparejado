import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Toast, { showToast } from '../components/Toast'
import Modal from '../components/Modal'
import FolderPicker from '../components/FolderPicker'

const api = async (endpoint, method = 'GET') => {
  const res = await fetch('/api/' + endpoint, {
    method,
    headers: { 'Content-Type': 'application/json' },
  })
  return res.json()
}

const apiPost = async (endpoint, body = {}) => {
  const res = await fetch('/api/' + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return res.json()
}

export default function Pairing() {
  const navigate = useNavigate()

  // ── Setup state ──
  const [setup, setSetup] = useState(true)
  const [frontalesDir, setFrontalesDir] = useState('')
  const [traserasDir, setTraserasDir] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [starting, setStarting] = useState(false)

  // ── Pairing state ──
  const [state, setState] = useState(null)
  const [busy, setBusy] = useState(false)

  // ── Modals ──
  const [showCycleModal, setShowCycleModal] = useState(false)
  const [showResetModal, setShowResetModal] = useState(false)
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [resetCountdown, setResetCountdown] = useState(3)

  // ── Post-pairing ──
  const [renaming, setRenaming] = useState(false)
  const [renameResult, setRenameResult] = useState(null)

  // ── Drive upload ──
  const [credentialsPath, setCredentialsPath] = useState('')
  const [folderId, setFolderId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [uploadResult, setUploadResult] = useState(null)

  // Check if there's an active session on mount
  useEffect(() => {
    fetch('/api/pairing/session')
      .then(r => r.json())
      .then(data => {
        if (data.active) {
          setFrontalesDir(data.frontales_dir)
          setTraserasDir(data.traseras_dir)
          setOutputDir(data.paired_dir)
          setSetup(false)
        }
      })
      .catch(() => {})
  }, [])

  // ── Refresh state ──
  const refresh = useCallback(async () => {
    if (setup) return
    try {
      const s = await api('state')
      setState(s)
      if (s.cycle_complete && !s.completed) {
        setShowCycleModal(true)
      }
    } catch (e) {
      console.error('Error fetching state:', e)
    }
  }, [setup])

  useEffect(() => {
    if (!setup) refresh()
  }, [setup, refresh])

  // ── Start session ──
  const startSession = async () => {
    if (!frontalesDir || !traserasDir || !outputDir) {
      showToast('⚠ Rellena todas las carpetas', 'warning')
      return
    }
    setStarting(true)
    try {
      const res = await apiPost('pairing/start', {
        frontales_dir: frontalesDir,
        traseras_dir: traserasDir,
        output_dir: outputDir,
      })
      if (res.error) {
        showToast(`❌ ${res.error}`, 'error')
      } else {
        showToast(`✅ Sesión iniciada: ${res.frontales} frontales, ${res.traseras} traseras`)
        setSetup(false)
      }
    } catch (e) {
      showToast('❌ Error de conexión', 'error')
    }
    setStarting(false)
  }

  // ── Actions ──
  const doPair = async () => {
    if (busy) return; setBusy(true)
    const res = await apiPost('pair')
    if (res.success) showToast(`✓ Pareja guardada en ${res.folder}/`)
    setBusy(false); refresh()
  }

  const doNext = async () => {
    if (busy) return; setBusy(true)
    const res = await apiPost('next')
    if (res.cycle_complete) showToast('⚠ Fin del ciclo de traseras', 'warning')
    setBusy(false); refresh()
  }

  const doPrev = async () => {
    if (busy) return; setBusy(true)
    await apiPost('prev')
    setBusy(false); refresh()
  }

  const doSkip = async () => {
    if (busy) return; setBusy(true)
    await apiPost('skip')
    showToast('✗ Frontal marcada sin pareja', 'warning')
    setBusy(false); refresh()
  }

  const doSkipTrasera = async () => {
    if (busy) return; setBusy(true)
    await apiPost('skip_trasera')
    showToast('✗ Trasera marcada sin pareja', 'warning')
    setBusy(false); refresh()
  }

  const doUndo = async () => {
    if (busy) return; setBusy(true)
    const res = await apiPost('undo')
    if (res.success) {
      const labels = { pair: 'pareja', skip_frontal: 'skip frontal', skip_trasera: 'skip trasera' }
      showToast('↩ Deshecho: ' + (labels[res.undone] || res.undone), 'warning')
    } else {
      showToast('⚠ Nada que deshacer', 'warning')
    }
    setBusy(false); refresh()
  }

  const doReview = async () => {
    if (busy) return; setBusy(true)
    const res = await apiPost('review')
    if (res.success) showToast(`📋 Revisión iniciada (${res.pairs_kept} parejas mantenidas)`)
    setBusy(false); refresh()
  }

  const doReset = async () => {
    await apiPost('reset')
    setShowResetConfirm(false)
    setShowResetModal(false)
    refresh()
  }

  const restartCycle = async () => {
    setShowCycleModal(false)
    await apiPost('next')
    refresh()
  }

  // ── Rename pairs ──
  const doRename = async () => {
    setRenaming(true)
    try {
      const res = await apiPost('pairing/rename')
      if (res.success) {
        setRenameResult(res)
        showToast(`✅ ${res.total_renamed} archivos renombrados`)
      } else {
        showToast(`❌ ${res.error}`, 'error')
      }
    } catch (e) {
      showToast('❌ Error al renombrar', 'error')
    }
    setRenaming(false)
  }

  // ── Drive upload ──
  const doUploadDrive = async () => {
    if (!credentialsPath) { showToast('Introduce la ruta a credentials.json', 'warning'); return }
    if (!folderId) { showToast('Introduce el folder ID de destino en Drive', 'warning'); return }
    if (!renameResult) { showToast('Primero renombra las parejas', 'warning'); return }

    setUploading(true)
    setUploadResult(null)
    setUploadStatus({ phase: 'starting' })

    const datasetDir = renameResult.output_dir ||
      (outputDir ? outputDir.replace(/paired_images\/?$/, 'dataset_final') : '')

    try {
      const res = await apiPost('upload/drive', {
        dataset_dir: datasetDir,
        credentials_path: credentialsPath,
        folder_id: folderId,
      })

      if (res.error) {
        showToast(`\u274C ${res.error}`, 'error')
        setUploading(false)
        return
      }

      // Poll status
      const poll = setInterval(async () => {
        try {
          const st = await fetch('/api/upload/drive/status').then(r => r.json())
          setUploadStatus(st.status)
          if (!st.running) {
            clearInterval(poll)
            setUploading(false)
            if (st.error) {
              showToast(`\u274C ${st.error}`, 'error')
            } else if (st.result) {
              setUploadResult(st.result)
              if (st.result.success) {
                showToast(`\u2705 ${st.result.uploaded} archivos subidos a Drive`)
              } else {
                showToast(`\u274C ${st.result.error}`, 'error')
              }
            }
          }
        } catch {
          clearInterval(poll)
          setUploading(false)
        }
      }, 1500)
    } catch (e) {
      showToast('\u274C Error de conexion', 'error')
      setUploading(false)
    }
  }

  // ── Keyboard shortcuts ──
  useEffect(() => {
    if (setup) return

    const handleKey = (e) => {
      if (showCycleModal || showResetModal || showResetConfirm) return
      if (state?.completed) return

      const key = e.key.toLowerCase()
      if (key === 'enter') { e.preventDefault(); doPair() }
      else if (key === 'd' || key === 'arrowright') { e.preventDefault(); doNext() }
      else if (key === 'a' || key === 'arrowleft') { e.preventDefault(); doPrev() }
      else if (key === 's') { e.preventDefault(); doSkip() }
      else if (key === 'w') { e.preventDefault(); doSkipTrasera() }
      else if (key === 'z') { e.preventDefault(); doUndo() }
    }

    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  })

  // ── Reset countdown ──
  useEffect(() => {
    if (!showResetConfirm) return
    setResetCountdown(3)
    const timer = setInterval(() => {
      setResetCountdown(c => {
        if (c <= 1) { clearInterval(timer); return 0 }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [showResetConfirm])

  // ═══════════════ RENDER ═══════════════

  // ── Setup view ──
  if (setup) {
    return (
      <div style={s.container}>
        <Toast />
        <div style={s.setupBox}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')} style={{ alignSelf: 'flex-start', marginBottom: 16 }}>
            ← Volver
          </button>
          <h1 style={s.setupTitle}>🔗 Emparejado de Imágenes</h1>
          <p style={s.setupSubtitle}>Selecciona las carpetas de entrada y salida para comenzar</p>

          <div style={s.formGrid}>
            <FolderPicker id="frontales" label="📷 Carpeta de Frontales" value={frontalesDir} onChange={setFrontalesDir} />
            <FolderPicker id="traseras" label="📷 Carpeta de Traseras" value={traserasDir} onChange={setTraserasDir} />
            <FolderPicker id="output" label="📂 Carpeta de Salida (paired_images)" value={outputDir} onChange={setOutputDir} />
          </div>

          <button
            className="btn btn-primary btn-lg"
            onClick={startSession}
            disabled={starting}
            style={{ marginTop: 24, width: '100%' }}
          >
            {starting ? <><span className="spinner" /> Iniciando...</> : '🚀 Comenzar Emparejado'}
          </button>
        </div>
      </div>
    )
  }

  // ── Completed view ──
  if (state?.completed) {
    return (
      <div style={s.container}>
        <Toast />
        <div style={{ ...s.setupBox, maxWidth: 500, textAlign: 'center' }}>
          <h2 style={{ fontSize: 28, color: 'var(--accent-green)', marginBottom: 12 }}>✅ Proceso completado</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
            {state.total_pairs} parejas creadas. {state.unpaired?.length || 0} sin pareja.
          </p>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={doReview}>
              📋 Revisar (mantener parejas)
            </button>
            <button className="btn" onClick={() => { setShowResetModal(true) }}>
              ↺ Reiniciar todo
            </button>
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-primary)', margin: '24px 0' }} />

          <h3 style={{ fontSize: 16, marginBottom: 12 }}>Paso siguiente</h3>
          <button
            className="btn btn-success btn-lg"
            onClick={doRename}
            disabled={renaming}
            style={{ width: '100%', marginBottom: 12 }}
          >
            {renaming ? <><span className="spinner" /> Renombrando...</> : '📝 Renombrar Parejas (NF/NB)'}
          </button>

          {renameResult && (
            <div className="card" style={{ textAlign: 'left', fontSize: 13, marginTop: 8 }}>
              <p>✅ <strong>{renameResult.total_renamed}</strong> archivos renombrados</p>
              <p>📁 <strong>{renameResult.folders_processed}</strong> carpetas procesadas</p>
            </div>
          )}

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-primary)', margin: '20px 0' }} />

          <h3 style={{ fontSize: 16, marginBottom: 12 }}>Subir a Google Drive</h3>

          <div className="input-group" style={{ marginBottom: 8, textAlign: 'left' }}>
            <label style={{ fontSize: 12 }}>Ruta a credentials.json</label>
            <input
              type="text"
              value={credentialsPath}
              onChange={e => setCredentialsPath(e.target.value)}
              placeholder="/ruta/a/credentials.json"
              style={{ fontSize: 13 }}
            />
          </div>

          <div className="input-group" style={{ marginBottom: 12, textAlign: 'left' }}>
            <label style={{ fontSize: 12 }}>Folder ID de destino en Drive</label>
            <input
              type="text"
              value={folderId}
              onChange={e => setFolderId(e.target.value)}
              placeholder="ej: 1A2B3C4D5E6F..."
              style={{ fontSize: 13 }}
            />
          </div>

          <button
            className="btn btn-warning btn-lg"
            disabled={!renameResult || uploading}
            style={{ width: '100%', opacity: renameResult ? 1 : 0.4 }}
            title={renameResult ? 'Subir a Google Drive' : 'Primero renombra las parejas'}
            onClick={doUploadDrive}
          >
            {uploading ? (
              <><span className="spinner" /> Subiendo...
                {uploadStatus && uploadStatus.uploaded ? ` (${uploadStatus.uploaded}/${uploadStatus.total || '?'})` : ''}
              </>
            ) : (
              '☁️ Subir a Google Drive'
            )}
          </button>

          {uploadResult && uploadResult.success && (
            <div className="card" style={{ textAlign: 'left', fontSize: 13, marginTop: 8 }}>
              <p>✅ <strong>{uploadResult.uploaded}</strong> archivos subidos</p>
              <p>📈 Último índice en Drive: <strong>{uploadResult.last_index}</strong></p>
              {uploadResult.errors && uploadResult.errors.length > 0 && (
                <p style={{ color: 'var(--accent-red)' }}>⚠ {uploadResult.errors.length} errores</p>
              )}
            </div>
          )}

          {uploadResult && uploadResult.error && (
            <div className="card" style={{ textAlign: 'left', fontSize: 13, marginTop: 8, borderColor: 'var(--accent-red)' }}>
              <p style={{ color: 'var(--accent-red)' }}>❌ {uploadResult.error}</p>
            </div>
          )}
        </div>

        {/* Reset modals */}
        <Modal show={showResetModal}>
          <h2>¿Reiniciar todo?</h2>
          <p>Se borrarán todas las parejas guardadas y el progreso.</p>
          <div className="modal-buttons">
            <button className="btn btn-danger" onClick={() => { setShowResetModal(false); setShowResetConfirm(true) }}>
              Sí, reiniciar
            </button>
            <button className="btn" onClick={() => setShowResetModal(false)}>Cancelar</button>
          </div>
        </Modal>
        <Modal show={showResetConfirm}>
          <h2>⚠️ ¿Estás completamente seguro?</h2>
          <p>Esta acción <strong>no se puede deshacer</strong>. Se eliminarán todas las carpetas de parejas.</p>
          <div className="modal-buttons">
            <button className="btn btn-danger" onClick={doReset} disabled={resetCountdown > 0}>
              {resetCountdown > 0 ? `Confirmar (${resetCountdown}s)` : '🗑 Confirmar reinicio'}
            </button>
            <button className="btn" onClick={() => setShowResetConfirm(false)}>Cancelar</button>
          </div>
        </Modal>
      </div>
    )
  }

  // ── Main pairing view ──
  const s_state = state || {}
  const pct = s_state.total_frontales > 0
    ? Math.round((s_state.frontal_idx / s_state.total_frontales) * 100)
    : 0

  return (
    <div style={s.pairingContainer}>
      <Toast />

      {/* Header */}
      <header style={s.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')}>←</button>
          <h1 style={s.headerTitle}>🔗 Emparejador <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>Frontales ↔ Traseras</span></h1>
        </div>
        <div style={{ display: 'flex', gap: 20 }}>
          <div className="stat"><div className="stat-dot green" /> Parejas: <strong>{s_state.total_pairs || 0}</strong></div>
          <div className="stat"><div className="stat-dot orange" /> Front. sin: <strong>{s_state.unpaired_count || 0}</strong></div>
          <div className="stat"><div className="stat-dot red" /> Tras. sin: <strong>{s_state.unpaired_traseras_count || 0}</strong></div>
          <div className="stat"><div className="stat-dot blue" /> Pendientes: <strong>{s_state.total_frontales ? s_state.total_frontales - (s_state.frontal_idx || 0) : 0}</strong></div>
        </div>
      </header>

      {/* Progress */}
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: pct + '%' }} />
      </div>

      {/* Panels */}
      <div style={s.panels}>
        {/* Frontal */}
        <div style={s.panel}>
          <div style={s.panelHeader}>
            <span style={{ ...s.panelLabel, color: 'var(--accent-blue)' }}>▎ Frontal</span>
            <span style={s.panelInfo}>
              {s_state.current_frontal
                ? `${(s_state.frontal_idx || 0) + 1}/${s_state.total_frontales}  •  ${s_state.current_frontal}`
                : '—'}
            </span>
          </div>
          <div style={s.panelBody}>
            {s_state.current_frontal ? (
              <img src={'/images/frontales/' + s_state.current_frontal} alt="Frontal" style={s.panelImg} />
            ) : (
              <p style={s.noImage}>Pon imágenes en /frontales</p>
            )}
          </div>
        </div>

        {/* Trasera */}
        <div style={s.panel}>
          <div style={s.panelHeader}>
            <span style={{ ...s.panelLabel, color: 'var(--accent-purple)' }}>▎ Trasera</span>
            <span style={s.panelInfo}>
              {s_state.current_trasera && !s_state.cycle_complete
                ? `${(s_state.trasera_idx || 0) + 1}/${s_state.total_traseras_available}  •  ${s_state.current_trasera}`
                : '—'}
            </span>
          </div>
          <div style={s.panelBody}>
            {s_state.current_trasera && !s_state.cycle_complete ? (
              <img src={'/images/traseras/' + s_state.current_trasera} alt="Trasera" style={s.panelImg} />
            ) : (
              <p style={s.noImage}>No hay más traseras</p>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div style={s.actions}>
        <button className="btn btn-sm" onClick={doUndo} style={{ position: 'absolute', left: 12, borderColor: 'rgba(251,191,36,0.2)', color: 'var(--accent-orange)' }}>
          ← Deshacer <span className="kbd">Z</span>
        </button>

        <button className="btn btn-primary" onClick={doPrev} disabled={!s_state.trasera_idx}>
          ← Anterior <span className="kbd">A</span>
        </button>
        <button className="btn btn-success" onClick={doPair} disabled={!s_state.current_trasera || s_state.cycle_complete}>
          ✓ Es Pareja <span className="kbd">Enter</span>
        </button>
        <button className="btn btn-primary" onClick={doNext} disabled={!s_state.current_trasera || s_state.cycle_complete}>
          → Siguiente <span className="kbd">D</span>
        </button>
        <button className="btn btn-danger" onClick={doSkip}>
          ✗ Frontal Sin Pareja <span className="kbd">S</span>
        </button>
        <button className="btn btn-warning" onClick={doSkipTrasera} disabled={!s_state.current_trasera || s_state.cycle_complete}>
          ✗ Trasera Sin Pareja <span className="kbd">W</span>
        </button>

        <button className="btn btn-sm" onClick={doReview} style={{ position: 'absolute', right: 100, borderColor: 'rgba(74,158,255,0.2)', color: 'var(--accent-blue)' }}>
          📋 Revisar
        </button>
        <button className="btn btn-sm" onClick={() => setShowResetModal(true)} style={{ position: 'absolute', right: 12, borderColor: 'rgba(248,113,113,0.2)', color: 'var(--accent-red)' }}>
          ↺ Reset
        </button>
      </div>

      {/* Cycle modal */}
      <Modal show={showCycleModal}>
        <h2>⚠️ Ciclo completado</h2>
        <p>Has recorrido todas las traseras disponibles sin encontrar pareja para esta frontal.</p>
        <div className="modal-buttons">
          <button className="btn btn-danger" onClick={() => { doSkip(); setShowCycleModal(false) }}>
            Marcar sin pareja
          </button>
          <button className="btn" onClick={restartCycle}>Revisar de nuevo</button>
        </div>
      </Modal>

      {/* Reset modals */}
      <Modal show={showResetModal}>
        <h2>¿Reiniciar todo?</h2>
        <p>Se borrarán todas las parejas guardadas y el progreso.</p>
        <div className="modal-buttons">
          <button className="btn btn-danger" onClick={() => { setShowResetModal(false); setShowResetConfirm(true) }}>
            Sí, reiniciar
          </button>
          <button className="btn" onClick={() => setShowResetModal(false)}>Cancelar</button>
        </div>
      </Modal>
      <Modal show={showResetConfirm}>
        <h2>⚠️ ¿Estás completamente seguro?</h2>
        <p>Esta acción <strong>no se puede deshacer</strong>.</p>
        <div className="modal-buttons">
          <button className="btn btn-danger" onClick={doReset} disabled={resetCountdown > 0}>
            {resetCountdown > 0 ? `Confirmar (${resetCountdown}s)` : '🗑 Confirmar reinicio'}
          </button>
          <button className="btn" onClick={() => setShowResetConfirm(false)}>Cancelar</button>
        </div>
      </Modal>
    </div>
  )
}

// ── Styles ──
const s = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    background: 'radial-gradient(ellipse at 50% 0%, rgba(74, 158, 255, 0.06) 0%, transparent 50%), var(--bg-primary)',
  },
  setupBox: {
    display: 'flex',
    flexDirection: 'column',
    maxWidth: 520,
    width: '100%',
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-xl)',
    padding: '32px',
  },
  setupTitle: {
    fontSize: 26,
    fontWeight: 700,
    marginBottom: 8,
  },
  setupSubtitle: {
    fontSize: 14,
    color: 'var(--text-secondary)',
    marginBottom: 24,
  },
  formGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  pairingContainer: {
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    userSelect: 'none',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 24px',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border-primary)',
    flexShrink: 0,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 600,
    color: 'var(--accent-blue)',
  },
  panels: {
    flex: 1,
    display: 'flex',
    gap: 2,
    padding: 8,
    minHeight: 0,
  },
  panel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-md)',
    overflow: 'hidden',
    border: '1px solid var(--border-primary)',
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 14px',
    background: 'var(--bg-tertiary)',
    borderBottom: '1px solid var(--border-primary)',
    fontSize: 12,
    flexShrink: 0,
  },
  panelLabel: {
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  panelInfo: {
    color: 'var(--text-muted)',
  },
  panelBody: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    minHeight: 0,
    position: 'relative',
  },
  panelImg: {
    maxWidth: '100%',
    maxHeight: '100%',
    objectFit: 'contain',
    borderRadius: 'var(--radius-sm)',
  },
  noImage: {
    color: 'var(--text-muted)',
    fontSize: 14,
    textAlign: 'center',
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: '12px 24px',
    background: 'var(--bg-secondary)',
    borderTop: '1px solid var(--border-primary)',
    flexShrink: 0,
    position: 'relative',
  },
}
