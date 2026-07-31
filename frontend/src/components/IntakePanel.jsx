import { useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { analyzeFile, analyzeText, resetIntake } from '../store/intakeSlice'

const ACCEPT = '.pdf,.eml,.txt,.md,.png,.jpg,.jpeg'

export default function IntakePanel() {
  const dispatch = useDispatch()
  const { status, sourceName, sourceType } = useSelector((state) => state.intake)
  const [text, setText] = useState('')
  const [over, setOver] = useState(false)
  const fileInput = useRef(null)
  const busy = status === 'analyzing'

  const submitFile = (file) => {
    if (file) dispatch(analyzeFile(file))
  }

  return (
    <section className="card intake">
      <div className="card__head">
        <h2>Complaint source</h2>
        {sourceName && (
          <span className="mono" style={{ color: 'var(--ink-3)', fontSize: 11 }}>
            {sourceType} · {sourceName}
          </span>
        )}
      </div>

      <div className="card__body">
        <label className="eyebrow" htmlFor="intake-text">
          Paste the complaint email, call note or letter
        </label>
        <textarea
          id="intake-text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Dear Quality Assurance team, we are writing to raise a complaint regarding batch…"
          style={{ marginTop: 6 }}
        />

        <div
          className={`dropzone ${over ? 'dropzone--over' : ''}`}
          onClick={() => fileInput.current?.click()}
          onKeyDown={(event) => event.key === 'Enter' && fileInput.current?.click()}
          onDragOver={(event) => {
            event.preventDefault()
            setOver(true)
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(event) => {
            event.preventDefault()
            setOver(false)
            submitFile(event.dataTransfer.files?.[0])
          }}
          role="button"
          tabIndex={0}
        >
          <strong>Drop a complaint PDF or .eml here</strong>
          <small>or click to browse · PDF, email, text and images up to 10 MB</small>
          <input
            ref={fileInput}
            type="file"
            accept={ACCEPT}
            hidden
            onChange={(event) => submitFile(event.target.files?.[0])}
          />
        </div>

        <div className="intake__row">
          <button
            className="btn"
            disabled={busy || text.trim().length < 25}
            onClick={() => dispatch(analyzeText(text))}
          >
            {busy ? 'Reading complaint…' : 'Read and fill the form'}
          </button>
          <button
            className="btn btn--ghost"
            onClick={() => {
              setText('')
              dispatch(resetIntake())
            }}
          >
            Clear
          </button>
          {text.trim().length > 0 && text.trim().length < 25 && (
            <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>
              Add a little more detail before running the agent.
            </span>
          )}
        </div>
      </div>
    </section>
  )
}
