import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Toast, { showToast } from '../components/Toast'

const api = async (endpoint, method = 'GET', body = null) => {
  const opts = { method, headers: { 'Content-Type': 'application/json' } }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch('/api/labeling/' + endpoint, opts)
  return res.json()
}

// ── Clickable image panel with bbox overlays + count badges (CSS only) ──
function ClickableImagePanel({ pairId, vista, vistaCode, label, accentColor, detections, counts, onClickDetection }) {
  const containerRef = useRef(null)
  const imgRef = useRef(null)
  const [imgRect, setImgRect] = useState(null)

  // Imagen estática: se carga UNA vez por par, sin parámetro de versión ni counts
  const src = `/api/labeling/pair/${pairId}/image/${vista}`

  const vistaDetections = detections.filter(d => d.d_vista === vistaCode)

  const updateRect = useCallback(() => {
    if (!imgRef.current || !containerRef.current) return
    const img = imgRef.current
    const container = containerRef.current.getBoundingClientRect()
    const rect = img.getBoundingClientRect()

    const natW = img.naturalWidth || 1
    const natH = img.naturalHeight || 1
    const scale = Math.min(rect.width / natW, rect.height / natH)
    const renderedW = natW * scale
    const renderedH = natH * scale
    const offsetX = rect.left - container.left + (rect.width - renderedW) / 2
    const offsetY = rect.top - container.top + (rect.height - renderedH) / 2

    setImgRect({ x: offsetX, y: offsetY, w: renderedW, h: renderedH, natW, natH })
  }, [])

  useEffect(() => {
    window.addEventListener('resize', updateRect)
    return () => window.removeEventListener('resize', updateRect)
  }, [updateRect])

  return (
    <div style={s.imagePanel}>
      <div style={s.panelHeader}>
        <span style={{ ...s.panelLabel, color: accentColor }}>▎ {label}</span>
      </div>
      <div ref={containerRef} style={{ ...s.panelBody, position: 'relative' }}>
        <img
          ref={imgRef}
          src={src}
          alt={label}
          style={s.image}
          onLoad={updateRect}
          onError={(e) => { e.target.style.display = 'none' }}
        />
        {/* Clickable bbox overlays + count badges (CSS only, no server re-renders) */}
        {imgRect && imgRect.w > 0 && vistaDetections.map(det => {
          const scX = imgRect.w / imgRect.natW
          const scY = imgRect.h / imgRect.natH
          const bx = imgRect.x + det.raw_bbox_x1 * scX
          const by = imgRect.y + det.raw_bbox_y1 * scY
          const bw = (det.raw_bbox_x2 - det.raw_bbox_x1) * scX
          const bh = (det.raw_bbox_y2 - det.raw_bbox_y1) * scY
          const n = counts[det.detection_id] || 0
          return (
            <div
              key={det.detection_id}
              title={`#${det.detection_id} (${det.d_tipo}) — Click +1`}
              onClick={() => onClickDetection(det.detection_id)}
              style={{
                position: 'absolute',
                left: bx, top: by, width: bw, height: bh,
                cursor: 'pointer',
                border: '2px solid transparent',
                borderRadius: 3,
                transition: 'border-color 0.15s',
                zIndex: 2,
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'transparent' }}
            >
              {/* Count badge — rendered in CSS, not from server */}
              {n > 0 && (
                <div style={{
                  position: 'absolute', top: 0, right: 0,
                  background: 'rgba(220, 38, 38, 0.85)',
                  color: '#fff', fontWeight: 700,
                  fontSize: Math.max(10, Math.min(16, bw / 5)),
                  padding: '1px 5px',
                  borderRadius: '0 3px 0 6px',
                  lineHeight: 1.4,
                  pointerEvents: 'none',
                  minWidth: 20, textAlign: 'center',
                }}>
                  ×{n}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Group detections by vista then balda ──
function groupDetections(detections) {
  const groups = { F: {}, B: {} }
  for (const det of detections) {
    const v = det.d_vista === 'B' ? 'B' : 'F'
    const balda = det.balda_idx >= 0 ? det.balda_idx : -1
    if (!groups[v][balda]) groups[v][balda] = []
    groups[v][balda].push(det)
  }
  return groups
}

export default function Labeling() {
  const navigate = useNavigate()

  // ── State ──
  const [pairs, setPairs] = useState([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [detections, setDetections] = useState([])
  const [counts, setCounts] = useState({})
  const [undoStack, setUndoStack] = useState([])
  const [loading, setLoading] = useState(true)
  const [totalPairs, setTotalPairs] = useState(0)
  const [labeledCount, setLabeledCount] = useState(0)
  const [dirty, setDirty] = useState(false)  // cambios sin guardar
  const [saving, setSaving] = useState(false)

  const countsRef = useRef(counts)
  countsRef.current = counts

  const pairsRef = useRef(pairs)
  pairsRef.current = pairs

  const currentIdxRef = useRef(currentIdx)
  currentIdxRef.current = currentIdx

  const dirtyRef = useRef(dirty)
  dirtyRef.current = dirty

  // ── Load pairs list + auto-resume ──
  useEffect(() => {
    Promise.all([api('pairs'), api('resume')]).then(([pairsData, resumeData]) => {
      if (pairsData.pairs) {
        setPairs(pairsData.pairs)
        setTotalPairs(pairsData.total || 0)
        setLabeledCount(pairsData.labeled_count || 0)
      }
      // Auto-resume: saltar al último par donde dejamos el etiquetado
      const resumeIdx = resumeData.resume_index || 0
      if (resumeIdx > 0 && pairsData.pairs && resumeIdx < pairsData.pairs.length) {
        setCurrentIdx(resumeIdx)
      }
      setLoading(false)
    })
  }, [])

  // ── Load pair data when index changes ──
  useEffect(() => {
    if (pairs.length === 0) return
    const pairId = pairs[currentIdx]?.id
    if (!pairId) return

    api(`pair/${pairId}`).then(data => {
      setDetections(data.detections || [])
      setCounts(data.labels || {})
      setUndoStack([])
      setDirty(false)
    })
  }, [currentIdx, pairs])

  // ── Save current pair labels ──
  const saveCurrentLabels = useCallback(async () => {
    const p = pairsRef.current
    const idx = currentIdxRef.current
    if (p.length === 0) return true
    const pairId = p[idx]?.id
    if (!pairId) return true
    const c = countsRef.current
    if (Object.keys(c).length === 0) return true

    setSaving(true)
    try {
      const res = await api(`pair/${pairId}/labels`, 'POST', { counts: c })
      if (res.success) {
        setDirty(false)
        return true
      } else {
        showToast('❌ Error al guardar', res.error || 'Error desconocido', 'error')
        return false
      }
    } catch (e) {
      showToast('❌ Error de red', String(e), 'error')
      return false
    } finally {
      setSaving(false)
    }
  }, [])

  // ── Explicit save (button or S key) ──
  const explicitSave = useCallback(async () => {
    if (!dirtyRef.current) {
      showToast('ℹ️ Sin cambios', 'No hay cambios pendientes', 'info')
      return
    }
    const ok = await saveCurrentLabels()
    if (ok) {
      showToast('✅ Guardado', `Par ${pairsRef.current[currentIdxRef.current]?.id} guardado correctamente`, 'success')
    }
  }, [saveCurrentLabels])

  // ── Auto-save every 30s ──
  useEffect(() => {
    const interval = setInterval(() => {
      if (dirtyRef.current) {
        saveCurrentLabels()
      }
    }, 30000)
    return () => clearInterval(interval)
  }, [saveCurrentLabels])

  // ── Navigate ──
  const navigatePair = useCallback(async (newIdx) => {
    if (dirtyRef.current) {
      const ok = await saveCurrentLabels()
      if (ok) {
        showToast('✅ Guardado', `Par ${pairsRef.current[currentIdxRef.current]?.id} guardado`, 'success')
      }
    }
    setCurrentIdx(newIdx)
    setUndoStack([])

    api('pairs').then(data => {
      if (data.pairs) {
        setPairs(data.pairs)
        setLabeledCount(data.labeled_count || 0)
      }
    })
  }, [saveCurrentLabels])

  // ── Click item (+1) ──
  const clickItem = useCallback((detId) => {
    setCounts(prev => {
      const old = prev[detId] || 0
      setUndoStack(stack => [...stack, { detId, oldVal: old }])
      setDirty(true)
      return { ...prev, [detId]: old + 1 }
    })
  }, [])

  // ── Undo ──
  const undo = useCallback(() => {
    setUndoStack(stack => {
      if (stack.length === 0) return stack
      const newStack = [...stack]
      const { detId, oldVal } = newStack.pop()
      setCounts(prev => ({ ...prev, [detId]: oldVal }))
      setDirty(true)
      return newStack
    })
  }, [])

  // ── Clear pair ──
  const clearPair = useCallback(() => {
    setCounts(prev => {
      const entries = Object.entries(prev)
      setUndoStack(entries.map(([k, v]) => ({ detId: parseInt(k), oldVal: v })))
      const cleared = {}
      for (const [k] of entries) cleared[k] = 0
      setDirty(true)
      return cleared
    })
  }, [])

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'ArrowLeft' && currentIdxRef.current > 0) {
        e.preventDefault()
        navigatePair(currentIdxRef.current - 1)
      } else if (e.key === 'ArrowRight' && currentIdxRef.current < pairsRef.current.length - 1) {
        e.preventDefault()
        navigatePair(currentIdxRef.current + 1)
      } else if (e.key === 'z' || e.key === 'Z') {
        e.preventDefault()
        undo()
      } else if (e.key === 's' || e.key === 'S') {
        e.preventDefault()
        explicitSave()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [navigatePair, undo, explicitSave])

  // ── Save on unmount ──
  useEffect(() => {
    return () => { saveCurrentLabels() }
  }, [saveCurrentLabels])

  if (loading) {
    return (
      <div style={s.container}>
        <div style={s.loadingBox}>
          <span className="spinner" style={{ width: 32, height: 32 }} />
          <p style={{ marginTop: 16, color: 'var(--text-secondary)' }}>Cargando datos...</p>
        </div>
      </div>
    )
  }

  if (pairs.length === 0) {
    return (
      <div style={s.container}>
        <Toast />
        <div style={s.emptyBox}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')} style={{ alignSelf: 'flex-start', marginBottom: 16 }}>
            ← Volver
          </button>
          <h2 style={{ fontSize: 24, marginBottom: 12 }}>🌳 Sin datos</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            No se encontró <code style={{ color: 'var(--accent-blue)' }}>detections_raw.csv</code>.
            <br />Coloca el archivo en <code style={{ color: 'var(--accent-blue)' }}>data/arbol_conteo/</code> y recarga.
          </p>
        </div>
      </div>
    )
  }

  const pair = pairs[currentIdx]
  const pairId = pair?.id
  const progress = totalPairs > 0 ? ((currentIdx + 1) / totalPairs) * 100 : 0
  const totalUnits = detections.reduce((sum, d) => sum + (counts[d.detection_id] || 0), 0)
  const grouped = groupDetections(detections)

  // Render grouped button section for a vista
  const renderVistaGroup = (vistaCode, vistaLabel, accentColor) => {
    const baldas = grouped[vistaCode]
    const baldaKeys = Object.keys(baldas).map(Number).sort((a, b) => a - b)
    if (baldaKeys.length === 0) return null

    return (
      <div key={vistaCode} style={{ flex: 1 }}>
        <div style={s.vistaHeader}>
          <span style={{ color: accentColor, fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            {vistaLabel}
          </span>
        </div>
        {baldaKeys.map((baldaIdx, i) => (
          <div key={baldaIdx}>
            {i > 0 && <div style={s.baldaSeparator} />}
            <div style={s.baldaLabel}>Balda {baldaIdx >= 0 ? baldaIdx : '?'}</div>
            <div style={s.detGrid}>
              {baldas[baldaIdx].map(det => {
                const n = counts[det.detection_id] || 0
                const emoji = det.d_tipo === 'flor' ? '🌸' : '🌿'
                const isActive = n > 0
                return (
                  <button
                    key={det.detection_id}
                    className="btn"
                    style={{
                      ...s.detBtn,
                      borderColor: isActive ? (det.d_tipo === 'flor' ? 'var(--accent-green)' : 'var(--accent-orange)') : 'var(--border-primary)',
                      background: isActive ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                    }}
                    onClick={() => clickItem(det.detection_id)}
                  >
                    <span style={{ fontSize: 20 }}>{emoji}</span>
                    <span style={{ fontWeight: 700, fontSize: 14 }}>#{det.detection_id}</span>
                    <span style={{
                      fontSize: 13,
                      color: isActive ? 'var(--accent-green)' : 'var(--text-muted)',
                      fontWeight: 600,
                    }}>
                      {n > 0 ? `×${n}` : '—'}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div style={s.container}>
      <Toast />

      {/* ── Header ── */}
      <div style={s.header}>
        <div style={s.headerLeft}>
          <button className="btn btn-ghost btn-sm" onClick={() => { saveCurrentLabels(); navigate('/') }}>
            ← Volver
          </button>
          <h1 style={s.title}>🌳 Etiquetar</h1>
        </div>
        <div style={s.stats}>
          <div className="stat">
            <div className="stat-dot green" />
            Par: <strong>{currentIdx + 1}/{totalPairs}</strong>
          </div>
          <div className="stat">
            <div className="stat-dot blue" />
            Etiquetados: <strong>{labeledCount}</strong>
          </div>
          <div className="stat">
            <div className="stat-dot purple" />
            ID par: <strong>{pairId}</strong>
          </div>
          {/* Save status indicator */}
          <div className="stat" style={{ fontSize: 12 }}>
            {saving ? (
              <span style={{ color: 'var(--accent-orange)' }}>💾 Guardando...</span>
            ) : dirty ? (
              <span style={{ color: 'var(--accent-orange)' }}>● Sin guardar</span>
            ) : (
              <span style={{ color: 'var(--accent-green)' }}>✓ Guardado</span>
            )}
          </div>
        </div>
      </div>

      {/* ── Progress ── */}
      <div className="progress-bar" style={{ height: 3, flexShrink: 0 }}>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      {/* ── Main content ── */}
      <div style={s.main}>
        {/* Nav left */}
        <button
          className="btn btn-icon"
          style={s.navBtn}
          disabled={currentIdx === 0}
          onClick={() => navigatePair(currentIdx - 1)}
        >
          ◀
        </button>

        {/* Images — clickable bboxes with CSS count badges */}
        <div style={s.imagesContainer}>
          <ClickableImagePanel
            pairId={pairId} vista="frontal" vistaCode="F" label="Frontal"
            accentColor="var(--accent-blue)" detections={detections}
            counts={counts}
            onClickDetection={clickItem}
          />
          <ClickableImagePanel
            pairId={pairId} vista="trasera" vistaCode="B" label="Trasera"
            accentColor="var(--accent-purple)" detections={detections}
            counts={counts}
            onClickDetection={clickItem}
          />
        </div>

        {/* Nav right */}
        <button
          className="btn btn-icon"
          style={s.navBtn}
          disabled={currentIdx >= pairs.length - 1}
          onClick={() => navigatePair(currentIdx + 1)}
        >
          ▶
        </button>
      </div>

      {detections.length > 0 && (
        <div style={s.detectionsSection}>
          <p style={s.detSectionTitle}>Pulsa el item o la bbox en la imagen para sumar +1:</p>
          <div style={s.vistaColumns}>
            {renderVistaGroup('F', '📷 Frontal', 'var(--accent-blue)')}
            <div style={s.vistaColumnSeparator} />
            {renderVistaGroup('B', '📷 Trasera', 'var(--accent-purple)')}
          </div>
        </div>
      )}

      {detections.length === 0 && (
        <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
          No hay detecciones flor/planta en este par.
        </div>
      )}

      {/* ── Bottom bar ── */}
      <div style={s.bottomBar}>
        <button
          className="btn"
          style={{ borderColor: 'rgba(251, 191, 36, 0.3)', color: 'var(--accent-orange)' }}
          disabled={undoStack.length === 0}
          onClick={undo}
        >
          ↩️ Deshacer <span className="kbd">Z</span>
        </button>
        <button
          className="btn"
          style={{ borderColor: 'rgba(248, 113, 113, 0.3)', color: 'var(--accent-red)' }}
          onClick={clearPair}
        >
          🗑️ Borrar este par
        </button>
        <button
          className="btn"
          style={{
            borderColor: dirty ? 'rgba(59, 130, 246, 0.5)' : 'var(--border-primary)',
            color: dirty ? 'var(--accent-blue)' : 'var(--text-muted)',
            fontWeight: dirty ? 700 : 400,
          }}
          disabled={saving}
          onClick={explicitSave}
        >
          💾 Guardar <span className="kbd">S</span>
        </button>
        <div style={s.totalBadge}>
          Total: <strong style={{ fontSize: 22, color: 'var(--text-primary)' }}>{totalUnits}</strong>
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════
// Styles
// ═══════════════════════════════════════════════════════════

const s = {
  container: {
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    background: 'var(--bg-primary)',
  },
  loadingBox: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    maxWidth: 500,
    margin: '0 auto',
    textAlign: 'center',
    padding: 40,
  },

  // Header
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 24px',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border-primary)',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
  },
  stats: {
    display: 'flex',
    gap: 20,
  },

  // Main
  main: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 12px',
    minHeight: 0,
  },
  navBtn: {
    flexShrink: 0,
    width: 44,
    height: 44,
    fontSize: 18,
  },
  imagesContainer: {
    flex: 1,
    display: 'flex',
    gap: 8,
    height: '100%',
    minHeight: 0,
  },
  imagePanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-primary)',
    overflow: 'hidden',
  },
  panelHeader: {
    padding: '6px 14px',
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
  panelBody: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    minHeight: 0,
  },
  image: {
    maxWidth: '100%',
    maxHeight: '100%',
    objectFit: 'contain',
    borderRadius: 'var(--radius-sm)',
  },

  // Detections — grouped
  detectionsSection: {
    flexShrink: 0,
    borderTop: '1px solid var(--border-primary)',
    padding: '10px 24px',
    background: 'var(--bg-secondary)',
    maxHeight: 200,
    overflowY: 'auto',
  },
  detSectionTitle: {
    fontSize: 12,
    color: 'var(--text-muted)',
    marginBottom: 8,
    fontWeight: 500,
  },
  vistaColumns: {
    display: 'flex',
    gap: 0,
  },
  vistaColumnSeparator: {
    width: 1,
    background: 'var(--border-secondary)',
    margin: '0 16px',
    flexShrink: 0,
  },
  vistaHeader: {
    marginBottom: 6,
    paddingBottom: 4,
    borderBottom: '1px solid var(--border-primary)',
  },
  baldaSeparator: {
    height: 1,
    background: 'var(--border-primary)',
    margin: '6px 0',
    opacity: 0.5,
  },
  baldaLabel: {
    fontSize: 10,
    color: 'var(--text-muted)',
    marginBottom: 4,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  detGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  detBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 1,
    padding: '6px 12px',
    minWidth: 68,
    borderRadius: 'var(--radius-md)',
    transition: 'all 0.15s ease',
  },

  // Bottom bar
  bottomBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    padding: '10px 24px',
    background: 'var(--bg-secondary)',
    borderTop: '1px solid var(--border-primary)',
    flexShrink: 0,
  },
  totalBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 14,
    color: 'var(--text-secondary)',
    marginLeft: 'auto',
  },
}
