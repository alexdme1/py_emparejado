import { useState, useEffect, useCallback } from 'react'

let toastTimeout = null

export default function Toast() {
  const [message, setMessage] = useState('')
  const [type, setType] = useState('success')
  const [visible, setVisible] = useState(false)

  const show = useCallback((msg, t = 'success') => {
    setMessage(msg)
    setType(t)
    setVisible(true)
    if (toastTimeout) clearTimeout(toastTimeout)
    toastTimeout = setTimeout(() => setVisible(false), 2500)
  }, [])

  // Expose globally
  useEffect(() => {
    window.__showToast = show
    return () => { window.__showToast = null }
  }, [show])

  return (
    <div className="toast-container">
      <div className={`toast toast-${type} ${visible ? 'show' : ''}`}>
        {message}
      </div>
    </div>
  )
}

export function showToast(msg, type = 'success') {
  if (window.__showToast) window.__showToast(msg, type)
}
