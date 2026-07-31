import { useEffect, useState } from 'react'
import LogComplaint from './pages/LogComplaint'
import ComplaintRegister from './pages/ComplaintRegister'

const PAGES = [
  { id: 'log', label: 'Log complaint' },
  { id: 'register', label: 'Complaint register' },
]

export default function App() {
  const [page, setPage] = useState('log')
  const [engine, setEngine] = useState(null)

  useEffect(() => {
    fetch('/health')
      .then((r) => r.json())
      .then(setEngine)
      .catch(() => setEngine({ status: 'down' }))
  }, [])

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail__mark">
          <strong>AIVOA</strong>
          <span>QMS</span>
        </div>
        <nav>
          {PAGES.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              aria-current={page === item.id}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="rail__foot">
          <div className="rail__engine">
            <span
              className={`rail__dot ${engine?.ai_engine === 'groq' ? '' : 'rail__dot--fallback'}`}
            />
            {engine?.status === 'down'
              ? 'API unreachable'
              : engine?.ai_engine === 'groq'
                ? 'Groq connected'
                : 'Rule engine (no API key)'}
          </div>
          {engine?.fast_model && <div className="mono">{engine.fast_model}</div>}
          {engine?.reasoning_model && <div className="mono">{engine.reasoning_model}</div>}
        </div>
      </aside>

      <main className="main">{page === 'log' ? <LogComplaint /> : <ComplaintRegister />}</main>
    </div>
  )
}
