import { useNavigate } from 'react-router-dom'
import Toast from '../components/Toast'

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    background: 'radial-gradient(ellipse at 50% 0%, rgba(74, 158, 255, 0.08) 0%, transparent 60%), var(--bg-primary)',
  },
  header: {
    textAlign: 'center',
    marginBottom: 48,
  },
  title: {
    fontSize: 42,
    fontWeight: 800,
    background: 'linear-gradient(135deg, #4a9eff, #a78bfa, #f472b6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    marginBottom: 12,
    letterSpacing: '-0.02em',
  },
  subtitle: {
    fontSize: 16,
    color: 'var(--text-secondary)',
    fontWeight: 400,
  },
  cards: {
    display: 'flex',
    gap: 28,
    maxWidth: 1100,
    width: '100%',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  card: {
    flex: '1 1 280px',
    maxWidth: 340,
    background: 'var(--bg-card)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-xl)',
    padding: '40px 32px',
    cursor: 'pointer',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    textAlign: 'center',
    position: 'relative',
    overflow: 'hidden',
  },
  cardIcon: {
    fontSize: 56,
    marginBottom: 20,
    display: 'block',
  },
  cardTitle: {
    fontSize: 22,
    fontWeight: 700,
    marginBottom: 12,
  },
  cardDesc: {
    fontSize: 14,
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
  },
  cardGlow: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 3,
    borderRadius: '24px 24px 0 0',
  },
  footer: {
    marginTop: 48,
    textAlign: 'center',
    color: 'var(--text-muted)',
    fontSize: 13,
  },
}

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div style={styles.container}>
      <Toast />

      <header style={styles.header}>
        <h1 style={styles.title}>Image Toolkit</h1>
        <p style={styles.subtitle}>Herramientas de procesamiento de imágenes</p>
      </header>

      <div style={styles.cards}>
        {/* Cropear */}
        <div
          id="card-cropping"
          style={styles.card}
          className="card"
          onClick={() => navigate('/cropping')}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'var(--accent-green)'
            e.currentTarget.style.transform = 'translateY(-4px)'
            e.currentTarget.style.boxShadow = '0 0 40px rgba(52, 211, 153, 0.12)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'var(--border-primary)'
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}
        >
          <div style={{ ...styles.cardGlow, background: 'var(--gradient-green)' }} />
          <span style={styles.cardIcon}>✂️</span>
          <h2 style={styles.cardTitle}>Cropear</h2>
          <p style={styles.cardDesc}>
            Recorte automático de imágenes desde un export de Roboflow.
            Los crops se suben automáticamente a tu proyecto de Roboflow.
          </p>
        </div>

        {/* Emparejar */}
        <div
          id="card-pairing"
          style={styles.card}
          className="card"
          onClick={() => navigate('/pairing')}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'var(--accent-blue)'
            e.currentTarget.style.transform = 'translateY(-4px)'
            e.currentTarget.style.boxShadow = '0 0 40px rgba(74, 158, 255, 0.12)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'var(--border-primary)'
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}
        >
          <div style={{ ...styles.cardGlow, background: 'var(--gradient-blue)' }} />
          <span style={styles.cardIcon}>🔗</span>
          <h2 style={styles.cardTitle}>Emparejar</h2>
          <p style={styles.cardDesc}>
            Empareja visualmente imágenes frontales y traseras.
            Renombra y sube el dataset finalizado a Google Drive.
          </p>
        </div>

        {/* Extraer de Vídeo */}
        <div
          id="card-video"
          style={styles.card}
          className="card"
          onClick={() => navigate('/video')}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'var(--accent-orange)'
            e.currentTarget.style.transform = 'translateY(-4px)'
            e.currentTarget.style.boxShadow = '0 0 40px rgba(251, 191, 36, 0.12)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'var(--border-primary)'
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}
        >
          <div style={{ ...styles.cardGlow, background: 'var(--gradient-warm)' }} />
          <span style={styles.cardIcon}>📹</span>
          <h2 style={styles.cardTitle}>Extraer de Vídeo</h2>
          <p style={styles.cardDesc}>
            Extrae capturas de vídeos de seguridad usando detección
            de personas con YOLOv8n.
          </p>
        </div>
      </div>

      <footer style={styles.footer}>
        <p>Image Toolkit v2.0 — Procesamiento local de imágenes</p>
      </footer>
    </div>
  )
}
