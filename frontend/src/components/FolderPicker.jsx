import { useState } from 'react'

export default function FolderPicker({ label, value, onChange, id }) {
  const [validating, setValidating] = useState(false)
  const [valid, setValid] = useState(null)

  const pickFolder = async () => {
    try {
      const res = await fetch('/api/folders/pick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: label || 'Seleccionar carpeta' }),
      })
      const data = await res.json()
      if (data.success && data.path) {
        onChange(data.path)
        setValid(true)
      }
    } catch (e) {
      console.error('Error picking folder:', e)
    }
  }

  const validatePath = async (path) => {
    if (!path) { setValid(null); return }
    setValidating(true)
    try {
      const res = await fetch('/api/folders/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      const data = await res.json()
      setValid(data.valid)
    } catch {
      setValid(false)
    }
    setValidating(false)
  }

  return (
    <div className="input-group">
      {label && <label htmlFor={id}>{label}</label>}
      <div className="folder-picker">
        <input
          id={id}
          type="text"
          className="input"
          value={value}
          onChange={e => {
            onChange(e.target.value)
            setValid(null)
          }}
          onBlur={() => validatePath(value)}
          placeholder="/ruta/a/carpeta"
          style={{
            borderColor: valid === true ? 'var(--accent-green)' :
                          valid === false ? 'var(--accent-red)' : undefined
          }}
        />
        <button
          type="button"
          className="btn btn-sm"
          onClick={pickFolder}
          title="Explorar..."
          style={{ flexShrink: 0 }}
        >
          📁
        </button>
      </div>
      {validating && (
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Validando...</span>
      )}
      {valid === false && (
        <span style={{ fontSize: 11, color: 'var(--accent-red)' }}>⚠ Carpeta no encontrada</span>
      )}
    </div>
  )
}
