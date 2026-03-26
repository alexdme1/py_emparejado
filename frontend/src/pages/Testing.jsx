import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Toast, { showToast } from '../components/Toast'

const Dropzone = ({ label, file, preview, setFile, setPreview }) => {
  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (f) {
      setFile(f)
      setPreview(URL.createObjectURL(f))
    }
  }

  return (
    <div style={{marginTop: 16}}>
      <label style={s.label}>{label}</label>
      <div 
        style={{
          height: 80, border: '2px dashed var(--border-primary)', borderRadius: 'var(--radius-md)',
          background: preview ? 'var(--bg-tertiary)' : 'var(--bg-primary)', position: 'relative',
          display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s',
          overflow: 'hidden'
        }}
        onDragOver={e => e.preventDefault()}
        onDrop={e => {
          e.preventDefault()
          const f = e.dataTransfer.files[0]
          if (f) { setFile(f); setPreview(URL.createObjectURL(f)) }
        }}
      >
        {preview && <img src={preview} style={{position: 'absolute', opacity: 0.2, width: '100%', height: '100%', objectFit: 'cover'}} alt="bg" />}
        <span style={{zIndex: 1, pointerEvents: 'none', color: 'var(--text-secondary)', fontSize: 13, background: 'rgba(0,0,0,0.6)', padding: '4px 8px', borderRadius: 4, textAlign: 'center'}}>
          {file ? `✅ ${file.name}` : 'Arrastra una imagen o haz clic'}
        </span>
        <input type="file" accept=".png,.jpg,.jpeg,.webp" 
               onChange={handleFileChange} 
               style={{opacity: 0, position: 'absolute', width: '100%', height: '100%', cursor: 'pointer', left: 0, top: 0}} />
      </div>
    </div>
  )
}

export default function Testing() {
  const navigate = useNavigate()

  const [mode, setMode] = useState('maskrcnn') // maskrcnn, convnext, pipeline
  const [loading, setLoading] = useState(false)

  // -- Model Lists --
  const [mrcnnRuns, setMrcnnRuns] = useState([])
  const [mrcnnCheckpoints, setMrcnnCheckpoints] = useState([])
  const [cnxRuns, setCnxRuns] = useState([])
  const [cnxCheckpoints, setCnxCheckpoints] = useState([])

  // -- Selections --
  const [selMrcnnRun, setSelMrcnnRun] = useState('')
  const [selMrcnnCkpt, setSelMrcnnCkpt] = useState('')
  const [selCnxRun, setSelCnxRun] = useState('')
  const [selCnxCkpt, setSelCnxCkpt] = useState('')
  const [treeModels, setTreeModels] = useState([])
  const [selTree, setSelTree] = useState('')

  // -- Params --
  const [thresh, setThresh] = useState(0.5)
  const [nmsThresh, setNmsThresh] = useState(0.5)

  // -- Images & Results --
  const [imgF, setImgF] = useState(null)
  const [imgB, setImgB] = useState(null)
  const [previewF, setPreviewF] = useState('')
  const [previewB, setPreviewB] = useState('')

  const [mrcnnResult, setMrcnnResult] = useState('') // base64
  const [cnxResult, setCnxResult] = useState([]) // array of {class: str, prob: float}
  const [pipelineResult, setPipelineResult] = useState(null) // { json, images: { f_raw, b_raw, f_tree, b_tree } }

  // Load Runs on Mount
  useEffect(() => {
    fetch('/api/testing/maskrcnn/runs')
      .then(r => r.json())
      .then(data => {
        if (!data.error && data.length > 0) {
          setMrcnnRuns(data)
          setSelMrcnnRun(data[0].path)
        }
      })
      .catch(e => console.error(e))

    fetch('/api/testing/convnext/runs')
      .then(r => r.json())
      .then(data => {
        if (!data.error && data.length > 0) {
          setCnxRuns(data)
          setSelCnxRun(data[0].path)
        }
      })
      .catch(e => console.error(e))

    fetch('/api/testing/tree/models')
      .then(r => r.json())
      .then(data => {
        if (!data.error && data.length > 0) {
          setTreeModels(data)
          setSelTree(data[0].path)
        }
      })
      .catch(e => console.error(e))
  }, [])

  // Load Mask RCNN Checkpoints when Run changes
  useEffect(() => {
    if (!selMrcnnRun) return
    const runId = selMrcnnRun.split('/').pop() || selMrcnnRun.split('\\').pop()
    fetch(`/api/testing/maskrcnn/runs/${runId}/checkpoints`)
      .then(r => r.json())
      .then(data => {
        if (!data.error && data.length > 0) {
          setMrcnnCheckpoints(data)
          setSelMrcnnCkpt(data[0].path)
        } else {
          setMrcnnCheckpoints([])
          setSelMrcnnCkpt('')
        }
      })
      .catch(e => console.error('Error loading MRCNN checkpoints:', e))
  }, [selMrcnnRun])

  // Load ConvNeXt Checkpoints when Run changes
  useEffect(() => {
    if (!selCnxRun) return
    const runId = selCnxRun.split('/').pop() || selCnxRun.split('\\').pop()
    fetch(`/api/testing/convnext/runs/${runId}/checkpoints`)
      .then(r => r.json())
      .then(data => {
        if (!data.error && data.length > 0) {
          setCnxCheckpoints(data)
          setSelCnxCkpt(data[0].path)
        } else {
          setCnxCheckpoints([])
          setSelCnxCkpt('')
        }
      })
      .catch(e => console.error('Error loading CNX checkpoints:', e))
  }, [selCnxRun])

  // Ejecutar Mask R-CNN
  const runMaskRCNN = async () => {
    if (!imgF || !selMrcnnCkpt) return showToast('Error', 'Falta imagen o modelo', 'error')
    setLoading(true)
    setMrcnnResult('')
    
    try {
      const fd = new FormData()
      fd.append('image', imgF)
      fd.append('model_path', selMrcnnCkpt)
      fd.append('threshold', thresh)
      fd.append('nms_thresh', nmsThresh)

      const res = await fetch('/api/testing/maskrcnn/infer', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.error) showToast('Error', data.error, 'error')
      else setMrcnnResult(data.image_base64)
    } catch (e) {
      showToast('Error', String(e), 'error')
    }
    setLoading(false)
  }

  // Ejecutar ConvNeXt
  const runConvNeXt = async () => {
    if (!imgF || !selCnxCkpt || !selCnxRun) return showToast('Error', 'Falta imagen o modelo', 'error')
    setLoading(true)
    setCnxResult([])
    
    try {
      const fd = new FormData()
      fd.append('image', imgF)
      fd.append('model_path', selCnxCkpt)
      fd.append('run_dir', selCnxRun)

      const res = await fetch('/api/testing/convnext/infer', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.error) showToast('Error', data.error, 'error')
      else setCnxResult(data.predictions)
    } catch (e) {
      showToast('Error', String(e), 'error')
    }
    setLoading(false)
  }

  // Ejecutar Pipeline Completo
  const runPipeline = async () => {
    if (!imgF || !imgB || !selMrcnnCkpt || !selCnxCkpt) {
      return showToast('Error', 'Faltan imágenes o modelos', 'error')
    }
    setLoading(true)
    setPipelineResult(null)
    console.log('[Pipeline] Starting with:', { selMrcnnCkpt, selCnxCkpt, selCnxRun, selTree })
    
    try {
      const fd = new FormData()
      fd.append('image_f', imgF)
      fd.append('image_b', imgB)
      fd.append('mrcnn_path', selMrcnnCkpt)
      fd.append('threshold', thresh)
      fd.append('nms_thresh', nmsThresh)
      fd.append('cnx_path', selCnxCkpt)
      fd.append('cnx_run_dir', selCnxRun)
      if (selTree) fd.append('tree_path', selTree)

      const res = await fetch('/api/testing/pipeline/infer', { method: 'POST', body: fd })
      const data = await res.json()
      console.log('[Pipeline] Response:', data)
      if (data.error) showToast('Error', data.error, 'error')
      else setPipelineResult(data)
    } catch (e) {
      showToast('Error', String(e), 'error')
    }
    setLoading(false)
  }

  return (
    <div style={s.container}>
      <Toast />
      
      {/* ── Header ── */}
      <div style={s.header}>
        <div style={s.headerLeft}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')}>
            ← Volver
          </button>
          <h1 style={s.title}>🧪 Test de Modelos</h1>
        </div>
      </div>

      <div style={s.mainWrapper}>
        <div style={s.content}>
          
          {/* Tabs */}
          <div style={s.tabs}>
            <button 
              style={mode === 'maskrcnn' ? s.tabActive : s.tab} 
              onClick={() => setMode('maskrcnn')}
            >
              🎭 Mask R-CNN
            </button>
            <button 
              style={mode === 'convnext' ? s.tabActive : s.tab} 
              onClick={() => setMode('convnext')}
            >
              🔬 ConvNeXt
            </button>
            <button 
              style={mode === 'pipeline' ? s.tabActive : s.tab} 
              onClick={() => setMode('pipeline')}
            >
              📊 Pipeline Completo
            </button>
          </div>

          <div style={s.panel}>
            {/* -- MASK RCNN MODE -- */}
            {mode === 'maskrcnn' && (
              <div style={s.grid2}>
                <div style={s.settingsCol}>
                  <h3 style={s.sectionTitle}>Model Options</h3>
                  
                  <label style={s.label}>1. Selecciona Run (Mask R-CNN)</label>
                  <select style={s.select} value={selMrcnnRun} onChange={e => setSelMrcnnRun(e.target.value)}>
                    {mrcnnRuns.map(r => <option key={r.path} value={r.path}>{r.id}</option>)}
                  </select>

                  <label style={{...s.label, marginTop: 12}}>2. Selecciona Checkpoint</label>
                  <select style={s.select} value={selMrcnnCkpt} onChange={e => setSelMrcnnCkpt(e.target.value)}>
                    {mrcnnCheckpoints.map(c => <option key={c.path} value={c.path}>{c.id}</option>)}
                  </select>

                  <div style={{marginTop: 16, display: 'flex', gap: 16}}>
                    <div style={{flex: 1}}>
                      <label style={s.label}>Confianza</label>
                      <input type="range" min="0.05" max="0.95" step="0.05" value={thresh} 
                        onChange={e => setThresh(Number(e.target.value))} style={{width: '100%'}}/>
                      <div style={{fontSize: 12, textAlign: 'right'}}>{thresh.toFixed(2)}</div>
                    </div>
                    <div style={{flex: 1}}>
                      <label style={s.label}>NMS IoU</label>
                      <input type="range" min="0.1" max="0.95" step="0.05" value={nmsThresh} 
                        onChange={e => setNmsThresh(Number(e.target.value))} style={{width: '100%'}}/>
                      <div style={{fontSize: 12, textAlign: 'right'}}>{nmsThresh.toFixed(2)}</div>
                    </div>
                  </div>

                  <Dropzone label="Imagen a testear" file={imgF} preview={previewF} setFile={setImgF} setPreview={setPreviewF} />

                  <button className="btn btn-primary" style={{marginTop: 24, width: '100%'}} 
                    disabled={loading || !imgF || !selMrcnnCkpt} onClick={runMaskRCNN}>
                    {loading ? 'Procesando...' : '🚀 Ejecutar Mask R-CNN'}
                  </button>
                </div>

                <div style={s.visualCol}>
                  <div style={{display: 'flex', gap: 16, height: '100%'}}>
                    <div style={{flex: 1, border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)', padding: 8, background: 'var(--bg-tertiary)'}}>
                      <h4 style={{fontSize: 12, textAlign: 'center', marginBottom: 8}}>Original</h4>
                      {previewF ? <img src={previewF} style={s.imgFit} alt="Original"/> : <div style={s.placeholder}>Sube una imagen</div>}
                    </div>
                    <div style={{flex: 1, border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)', padding: 8, background: 'var(--bg-tertiary)'}}>
                      <h4 style={{fontSize: 12, textAlign: 'center', marginBottom: 8}}>Predicción</h4>
                      {mrcnnResult ? <img src={`data:image/png;base64,${mrcnnResult}`} style={s.imgFit} alt="Resultado"/> : <div style={s.placeholder}>Ejecuta para ver resultados</div>}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* -- CONVNEXT MODE -- */}
            {mode === 'convnext' && (
              <div style={s.grid2}>
                <div style={s.settingsCol}>
                  <h3 style={s.sectionTitle}>Model Options</h3>
                  
                  <label style={s.label}>1. Selecciona Run (ConvNeXt)</label>
                  <select style={s.select} value={selCnxRun} onChange={e => setSelCnxRun(e.target.value)}>
                    {cnxRuns.map(r => <option key={r.path} value={r.path}>{r.id}</option>)}
                  </select>

                  <label style={{...s.label, marginTop: 12}}>2. Selecciona Checkpoint</label>
                  <select style={s.select} value={selCnxCkpt} onChange={e => setSelCnxCkpt(e.target.value)}>
                    {cnxCheckpoints.map(c => <option key={c.path} value={c.path}>{c.id}</option>)}
                  </select>

                  <Dropzone label="Crop a testear (Flor/Planta)" file={imgF} preview={previewF} setFile={setImgF} setPreview={setPreviewF} />

                  <button className="btn btn-primary" style={{marginTop: 24, width: '100%'}} 
                    disabled={loading || !imgF || !selCnxCkpt} onClick={runConvNeXt}>
                    {loading ? 'Procesando...' : '🚀 Clasificar'}
                  </button>
                </div>

                <div style={s.visualCol}>
                  <div style={{display: 'flex', gap: 16, height: '100%'}}>
                    <div style={{flex: 1, border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)', padding: 8, background: 'var(--bg-tertiary)'}}>
                       {previewF ? <img src={previewF} style={s.imgFit} alt="Original"/> : <div style={s.placeholder}>Sube un crop</div>}
                    </div>
                    <div style={{flex: 1, display: 'flex', flexDirection: 'column', padding: 16}}>
                        <h4 style={{fontSize: 16, marginBottom: 16}}>Predicciones:</h4>
                        {cnxResult.length > 0 ? cnxResult.map((res, i) => (
                           <div key={i} style={{marginBottom: 12}}>
                             <div style={{display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600}}>
                               <span>{res.class}</span>
                               <span style={{color: 'var(--accent-blue)'}}>{(res.prob * 100).toFixed(1)}%</span>
                             </div>
                             <div className="progress-bar" style={{height: 6, marginTop: 4, background: 'var(--border-primary)'}}>
                                <div className="progress-fill" style={{width: `${res.prob * 100}%`, background: 'var(--accent-blue)'}}/>
                             </div>
                           </div>
                        )) : <div style={{color: 'var(--text-muted)', fontSize: 13}}>Ejecuta para ver resultados</div>}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* -- PIPELINE MODE -- */}
            {mode === 'pipeline' && (
              <div>
                <div style={{display: 'flex', gap: 24, marginBottom: 24}}>
                  {/* Selectors and Inputs */}
                  <div style={{flex: 1, background: 'var(--bg-tertiary)', padding: 16, borderRadius: 'var(--radius-md)'}}>
                    <h4 style={s.sectionTitle}>Modelos</h4>
                    
                    <label style={s.label}>Mask R-CNN Run</label>
                    <select style={s.select} value={selMrcnnRun} onChange={e => setSelMrcnnRun(e.target.value)}>
                      {mrcnnRuns.map(r => <option key={r.path} value={r.path}>{r.id}</option>)}
                    </select>
                    <select style={{...s.select, marginTop: 8}} value={selMrcnnCkpt} onChange={e => setSelMrcnnCkpt(e.target.value)}>
                      {mrcnnCheckpoints.map(c => <option key={c.path} value={c.path}>{c.id}</option>)}
                    </select>

                    <div style={{height: 16}}/>

                    <label style={s.label}>ConvNeXt Run</label>
                    <select style={s.select} value={selCnxRun} onChange={e => setSelCnxRun(e.target.value)}>
                      {cnxRuns.map(r => <option key={r.path} value={r.path}>{r.id}</option>)}
                    </select>
                    <select style={{...s.select, marginTop: 8}} value={selCnxCkpt} onChange={e => setSelCnxCkpt(e.target.value)}>
                      {cnxCheckpoints.map(c => <option key={c.path} value={c.path}>{c.id}</option>)}
                    </select>

                    <div style={{height: 16}}/>

                    <label style={s.label}>Árbol de Decisión</label>
                    <select style={s.select} value={selTree} onChange={e => setSelTree(e.target.value)}>
                      {treeModels.map(t => <option key={t.path} value={t.path}>{t.id}</option>)}
                    </select>
                  </div>

                  <div style={{flex: 1, background: 'var(--bg-tertiary)', padding: 16, borderRadius: 'var(--radius-md)'}}>
                    <h4 style={s.sectionTitle}>Par de Imágenes</h4>
                    <Dropzone label="Imagen Frontal" file={imgF} preview={previewF} setFile={setImgF} setPreview={setPreviewF} />
                    <Dropzone label="Imagen Trasera" file={imgB} preview={previewB} setFile={setImgB} setPreview={setPreviewB} />

                    <div style={{height: 16}}/>

                    <button className="btn btn-primary" style={{width: '100%'}} 
                      disabled={loading || !imgF || !imgB || !selMrcnnCkpt || !selCnxCkpt} onClick={runPipeline}>
                      {loading ? 'Procesando pipeline...' : '🚀 Ejecutar Conteo Múltiple'}
                    </button>
                  </div>
                </div>

                {pipelineResult && (
                  <div>
                    <h3 style={{fontSize: 16, fontWeight: 700, marginBottom: 12, borderBottom: '1px solid var(--border-primary)', paddingBottom: 8}}>
                      🔍 Estado 1: Detección Pura (Mask R-CNN)
                    </h3>
                    <div style={{display: 'flex', gap: 16, marginBottom: 24}}>
                      <img src={`data:image/jpeg;base64,${pipelineResult?.images?.f_raw || ''}`} style={s.imgPipe} alt="Front Raw"/>
                      <img src={`data:image/jpeg;base64,${pipelineResult?.images?.b_raw || ''}`} style={s.imgPipe} alt="Back Raw"/>
                    </div>

                    <h3 style={{fontSize: 16, fontWeight: 700, marginBottom: 12, borderBottom: '1px solid var(--border-primary)', paddingBottom: 8}}>
                      🌳 Estado 2: Filtrado y Conteo (Árbol de Decisión)
                    </h3>
                    <div style={{display: 'flex', gap: 16, marginBottom: 24}}>
                      <img src={`data:image/jpeg;base64,${pipelineResult?.images?.f_tree || ''}`} style={s.imgPipe} alt="Front Tree"/>
                      <img src={`data:image/jpeg;base64,${pipelineResult?.images?.b_tree || ''}`} style={s.imgPipe} alt="Back Tree"/>
                    </div>

                    <h3 style={{fontSize: 16, fontWeight: 700, marginBottom: 12, borderBottom: '1px solid var(--border-primary)', paddingBottom: 8}}>
                      📋 Resultados: Tabla y JSON
                    </h3>
                    <div style={{display: 'flex', gap: 24}}>
                      <div style={{flex: 1}}>
                        <table style={{width: '100%', borderCollapse: 'collapse', fontSize: 13, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', overflow: 'hidden'}}>
                          <thead>
                            <tr style={{background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-primary)', textAlign: 'left'}}>
                              <th style={{padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)'}}>Clase</th>
                              <th style={{padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)'}}>Conteo</th>
                            </tr>
                          </thead>
                          <tbody>
                            {pipelineResult?.json?.Items ? (
                              Object.entries(pipelineResult.json.Items).map(([ticket, baldas]) => (
                                <React.Fragment key={ticket}>
                                  <tr style={{background: 'var(--bg-primary)'}}>
                                    <td colSpan="2" style={{padding: '10px 16px', color: 'var(--text-primary)', fontWeight: 700}}>{ticket}</td>
                                  </tr>
                                  {Object.entries(baldas).map(([balda, baldaData]) => (
                                    <React.Fragment key={`${ticket}-${balda}`}>
                                      <tr style={{background: 'var(--bg-secondary)'}}>
                                        <td colSpan="2" style={{padding: '6px 24px', color: 'var(--text-primary)', fontWeight: 600}}>📦 {balda}</td>
                                      </tr>
                                      {baldaData?.resumen_productos && Object.entries(baldaData.resumen_productos).map(([item, count]) => (
                                        <tr key={`${ticket}-${balda}-${item}`} style={{borderBottom: '1px solid var(--border-primary)'}}>
                                          <td style={{padding: '6px 32px', color: 'var(--text-secondary)'}}>↳ {item}</td>
                                          <td style={{padding: '6px 16px', color: 'var(--accent-blue)', fontWeight: 700}}>{count}</td>
                                        </tr>
                                      ))}
                                    </React.Fragment>
                                  ))}
                                </React.Fragment>
                              ))
                            ) : (
                              <tr>
                                <td colSpan="2" style={{padding: '10px 16px', textAlign: 'center', color: 'var(--text-muted)'}}>
                                  No hay resultados válidos.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                      <div style={{flex: 1}}>
                        <pre style={{
                          margin: 0, background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 'var(--radius-md)',
                          overflowX: 'auto', fontSize: 13, fontFamily: 'monospace', height: '100%'
                        }}>
                          {JSON.stringify(pipelineResult?.json || pipelineResult, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const s = {
  container: {
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    background: 'var(--bg-primary)',
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
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
  },
  mainWrapper: {
    flex: 1,
    overflowY: 'auto',
    padding: 24,
  },
  content: {
    maxWidth: 1200,
    margin: '0 auto',
    background: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-primary)',
    overflow: 'hidden',
  },
  tabs: {
    display: 'flex',
    background: 'var(--bg-tertiary)',
    borderBottom: '1px solid var(--border-primary)',
  },
  tab: {
    flex: 1,
    padding: '14px 0',
    background: 'transparent',
    border: 'none',
    color: 'var(--text-secondary)',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
    borderBottom: '2px solid transparent',
    transition: 'all 0.2s',
  },
  tabActive: {
    flex: 1,
    padding: '14px 0',
    background: 'var(--bg-secondary)',
    border: 'none',
    color: 'var(--accent-blue)',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
    borderBottom: '2px solid var(--accent-blue)',
    transition: 'all 0.2s',
  },
  panel: {
    padding: 24,
  },
  grid2: {
    display: 'flex',
    gap: 24,
    height: 480,
  },
  settingsCol: {
    width: 300,
    flexShrink: 0,
  },
  visualCol: {
    flex: 1,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 16,
    color: 'var(--text-muted)'
  },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: 6,
  },
  select: {
    width: '100%',
    padding: '8px 12px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--text-primary)',
    fontSize: 14,
  },
  imgFit: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
  },
  placeholder: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-muted)',
    fontSize: 13,
  },
  imgPipe: {
    flex: 1,
    width: '50%',
    objectFit: 'contain',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-primary)',
    background: 'var(--bg-tertiary)'
  }
}
