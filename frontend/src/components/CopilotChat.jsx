import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { analyzeFile, analyzeText, correctForm } from '../store/intakeSlice'

const ACCEPT = '.pdf,.eml,.txt,.md,.png,.jpg,.jpeg'

/**
 * The AIVOA Copilot pane.
 *
 * One input does both jobs. Before a form exists, what you type is a complaint to
 * be read; once one exists, it is a correction to be applied. The reviewer never
 * has to say which -- the presence of a thread decides it, the same way the
 * backend's entry router decides which path through the graph to take.
 */
export default function CopilotChat() {
  const dispatch = useDispatch()
  const { messages, status, threadId, assessment } = useSelector((state) => state.intake)
  const [text, setText] = useState('')
  const [over, setOver] = useState(false)
  const fileInput = useRef(null)
  const logEnd = useRef(null)

  const busy = status === 'analyzing' || status === 'correcting'
  const hasForm = Boolean(threadId && assessment)

  useEffect(() => {
    logEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, busy])

  const send = () => {
    const value = text.trim()
    if (!value || busy) return
    dispatch(hasForm ? correctForm({ message: value }) : analyzeText(value))
    setText('')
  }

  return (
    <section
      className={`copilot ${over ? 'copilot--over' : ''}`}
      onDragOver={(event) => {
        event.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault()
        setOver(false)
        const file = event.dataTransfer.files?.[0]
        if (file) dispatch(analyzeFile(file))
      }}
    >
      <header className="copilot__head">
        <div>
          <h2>AIVOA Copilot</h2>
          <p>Drop complaint files or paste text below.</p>
        </div>
        <span className={`copilot__status ${busy ? 'copilot__status--busy' : ''}`} aria-hidden="true" />
      </header>

      <div className="copilot__log">
        {messages.map((message, index) => (
          <div key={index} className={`turn turn--${message.role}`}>
            {message.role === 'copilot' && (
              <span className={`turn__icon ${message.error ? 'turn__icon--error' : ''}`} aria-hidden="true">
                {message.error ? '!' : '✓'}
              </span>
            )}
            <div className={`bubble bubble--${message.role} ${message.error ? 'bubble--error' : ''}`}>
              {message.attachment ? (
                <span className="attachment">
                  <span className="attachment__badge">PDF</span>
                  {message.attachment}
                </span>
              ) : (
                message.text
              )}
              {message.appliedFields?.length > 0 && (
                <span className="bubble__fields">
                  {message.appliedFields.map((field) => (
                    <span className="chip" key={field}>{field}</span>
                  ))}
                </span>
              )}
            </div>
            {message.role === 'user' && <span className="turn__icon turn__icon--user" aria-hidden="true">□</span>}
          </div>
        ))}

        {busy && (
          <div className="turn turn--copilot">
            <span className="turn__icon" aria-hidden="true">•</span>
            <div className="bubble bubble--copilot">
              <span className="working">
                {status === 'correcting' ? 'Applying the correction' : 'Extracting complaint data'}
              </span>
              <span className="progress-line" aria-hidden="true"><i /></span>
            </div>
          </div>
        )}
        <div ref={logEnd} />
      </div>

      <div className="copilot__composer">
        <button
          className="composer__clip"
          onClick={() => fileInput.current?.click()}
          title="Attach a complaint PDF or email"
          aria-label="Attach a complaint PDF or email"
        >
          ⎘
        </button>
        <input
          ref={fileInput}
          type="file"
          accept={ACCEPT}
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) dispatch(analyzeFile(file))
          }}
        />
        <textarea
          value={text}
          rows={1}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              send()
            }
          }}
          placeholder={
            hasForm ? 'Correct a field, or paste another complaint…' : 'Type a message or paste a complaint…'
          }
          aria-label="Message the copilot"
        />
        <button className="composer__send" onClick={send} disabled={busy || !text.trim()} aria-label="Send">
          ➤
        </button>
      </div>

      <footer className="copilot__foot">POWERED BY LANGGRAPH</footer>
    </section>
  )
}
