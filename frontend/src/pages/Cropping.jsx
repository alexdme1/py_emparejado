import { useState } from 'react'
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

const DEFAULT_CATEGORIES = ['Flores', 'Planta']
const DEFAULT_SPLITS = ['train', 'valid', 'test']

export default function Cropping() {
  const navigate = useNavigate()

  // ── Config ──
  const [inputDir, setInputDir] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES.join(', '))
  const [splits, setSplits] = useState('train')
  const [apiKey, setApiKey] = useState('')
  const [workspace, setWorkspace] = useState('floresverdnatura')
  const [project, setProject] = useState('proyecto_h_clas')
  const [batchPrefix, setBatchPrefix] = useState('crops')

  // ── Job state ──
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // ── Start job ──
  const startCropping = async () => {
    if (!inputDir || !outputDir) {
      showToast('⚠ Rellena las carpetas de entrada y salida', 'warning')
      return
    }
    if (!apiKey) {
      showToast('⚠ Introduce tu API Key de Roboflow', 'warning')
      return
    }

    setRunning(true)
    setResult(null)
    setError(null)
    setStatus({ phase: 'starting' })

    try {
      const res = await apiPost('cropping/start', {
        input_dir: inputDir,
        output_dir: outputDir,
        categories: categories.split(',').map(c => c.trim()).filter(Boolean),
        splits: splits.split(',').map(s => s.trim()).filter(Boolean),
        roboflow_api_key: apiKey,
        roboflow_workspace: workspace,
        roboflow_project: project,
        roboflow_batch: batchPrefix,
      })

      if (res.error) {
        showToast(`❌ ${res.error}`, 'error')
        setError(res.error)
        setRunning(false)
        return
      }

      // Poll status
      const poll = setInterval(async () => {
        try {
          const st = await fetch('/api/cropping/status').then(r => r.json())
          setStatus(st.status)

          if (!st.running) {
            clearInterval(poll)
            setRunning(false)
            if (st.error) {
              setError(st.error)
              showToast(`❌ ${st.error}`, 'error')
            } else if (st.result) {
              setResult(st.result)
              showToast('✅ Cropping y subida completados')
            }
          }
        } catch {
          clearInterval(poll)
          setRunning(false)
        }
      }, 1500)
    } catch (e) {
      showToast('❌ Error de conexión', 'error')
      setRunning(false)
    }
  }

  // ── Phase label ──
  const getPhaseLabel = () => {
    if (!status) return ''
    switch (status.phase) {
      case 'starting': return '⏳ Iniciando...'
      case 'cropping': return `✂️ Recortando split: ${status.current_split} (${(status.split_index || 0) + 1}/${status.total_splits})`
      case 'cropping_done': return '✅ Recorte completado'
      case 'uploading_roboflow': return `☁️ Subiendo a Roboflow... (${status.uploaded || 0} subidas)`
      case 'upload_done': return '✅ Subida completada'
      default: return status.phase || ''
    }
  }

  return (
    <div style={s.container}>
      <Toast />
      <div style={s.box}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')} style={{ alignSelf: 'flex-start', marginBottom: 16 }}>
          ← Volver
        </button>

        <h1 style={s.title}>✂️ Cropping Automático</h1>
        <p style={s.subtitle}>
          Recorta imágenes desde un export COCO de Roboflow y súbelas automáticamente
        </p>

        {/* Folders */}
        <div style={s.section}>
          <h3 style={s.sectionTitle}>📁 Carpetas</h3>
          <div style={s.formGrid}>
            <FolderPicker id="crop-input" label="Carpeta de entrada (export Roboflow)" value={inputDir} onChange={setInputDir} />
            <FolderPicker id="crop-output" label="Carpeta de salida (crops)" value={outputDir} onChange={setOutputDir} />
          </div>
        </div>

        {/* Categories */}
        <div style={s.section}>
          <h3 style={s.sectionTitle}>🏷️ Categorías</h3>
          <div className="input-group">
            <label htmlFor="categories">Categorías a recortar (separadas por comas)</label>
            <input
              id="categories"
              type="text"
              value={categories}
              onChange={e => setCategories(e.target.value)}
              placeholder="Flores, Planta"
            />
          </div>
          <div className="input-group" style={{ marginTop: 12 }}>
            <label htmlFor="splits">Splits a procesar (separados por comas)</label>
            <input
              id="splits"
              type="text"
              value={splits}
              onChange={e => setSplits(e.target.value)}
              placeholder="train, valid, test"
            />
          </div>
        </div>

        {/* Roboflow config */}
        <div style={s.section}>
          <h3 style={s.sectionTitle}>🤖 Configuración Roboflow</h3>
          <div style={s.formGrid}>
            <div className="input-group">
              <label htmlFor="api-key">API Key *</label>
              <input
                id="api-key"
                type="password"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="Tu API key de Roboflow"
              />
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <div className="input-group" style={{ flex: 1 }}>
                <label htmlFor="workspace">Workspace</label>
                <input id="workspace" type="text" value={workspace} onChange={e => setWorkspace(e.target.value)} />
              </div>
              <div className="input-group" style={{ flex: 1 }}>
                <label htmlFor="project">Proyecto</label>
                <input id="project" type="text" value={project} onChange={e => setProject(e.target.value)} />
              </div>
            </div>
            <div className="input-group">
              <label htmlFor="batch">Prefijo del lote</label>
              <input id="batch" type="text" value={batchPrefix} onChange={e => setBatchPrefix(e.target.value)} />
            </div>
          </div>
        </div>

        {/* Action */}
        <button
          className="btn btn-success btn-lg"
          onClick={startCropping}
          disabled={running}
          style={{ width: '100%', marginTop: 8 }}
        >
          {running ? (
            <><span className="spinner" /> Procesando...</>
          ) : (
            '🚀 Ejecutar Cropping + Upload'
          )}
        </button>

        {/* Status */}
        {running && status && (
          <div className="card" style={{ marginTop: 16, textAlign: 'center' }}>
            <p style={{ fontSize: 14, marginBottom: 8 }}>{getPhaseLabel()}</p>
            <div className="progress-bar" style={{ height: 6 }}>
              <div className="progress-fill animate-pulse" style={{ width: '100%' }} />
            </div>
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
              ✅ Proceso completado
            </h3>

            {result.cropping && (
              <div style={{ marginBottom: 12 }}>
                <p style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Cropping:</p>
                <ul style={s.resultList}>
                  <li>Total crops: <strong>{result.cropping.total_crops}</strong></li>
                  {Object.entries(result.cropping.stats || {}).map(([cat, count]) => (
                    <li key={cat}>{cat}: <strong>{count}</strong></li>
                  ))}
                  {result.cropping.skipped_small > 0 && (
                    <li style={{ color: 'var(--text-muted)' }}>Descartados (pequeños): {result.cropping.skipped_small}</li>
                  )}
                </ul>
              </div>
            )}

            {result.upload && (
              <div>
                <p style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Upload Roboflow:</p>
                <ul style={s.resultList}>
                  <li>Subidas: <strong>{result.upload.total_uploaded}</strong></li>
                  {result.upload.total_errors > 0 && (
                    <li style={{ color: 'var(--accent-red)' }}>Errores: {result.upload.total_errors}</li>
                  )}
                </ul>
                {result.upload.url && (
                  <a href={result.upload.url} target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>
                    Ver en Roboflow →
                  </a>
                )}
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
    background: 'radial-gradient(ellipse at 50% 0%, rgba(52, 211, 153, 0.06) 0%, transparent 50%), var(--bg-primary)',
  },
  box: {
    display: 'flex',
    flexDirection: 'column',
    maxWidth: 580,
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
  formGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  resultList: {
    listStyle: 'none',
    fontSize: 13,
    color: 'var(--text-secondary)',
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
}
