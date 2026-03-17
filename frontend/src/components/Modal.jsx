export default function Modal({ show, children }) {
  if (!show) return null
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && null}>
      <div className="modal">
        {children}
      </div>
    </div>
  )
}
