import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { askCopilot } from '../../store/copilotSlice'

const SUGGESTIONS = [
  'Is this reportable to the regulator?',
  'What should I ask the customer next?',
  'Which batches should we widen the review to?',
]

export default function CopilotChat({ complaintId }) {
  const dispatch = useDispatch()
  const { messages, pending } = useSelector((state) => state.copilot)
  const [question, setQuestion] = useState('')

  const send = (text) => {
    const value = (text ?? question).trim()
    if (!value || pending) return
    dispatch(askCopilot({ question: value, complaintId }))
    setQuestion('')
  }

  return (
    <section className="card">
      <div className="card__head">
        <h2>Ask the copilot</h2>
        {!complaintId && <span className="eyebrow">Save first for full context</span>}
      </div>
      <div className="card__body chat">
        {messages.length === 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                className="btn btn--ghost btn--sm"
                onClick={() => send(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        ) : (
          <div className="chat__log">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`bubble bubble--${message.role} ${message.error ? 'bubble--error' : ''}`}
              >
                {message.text}
                {message.model && (
                  <span className="mono" style={{ display: 'block', marginTop: 4, fontSize: 10, color: 'var(--ink-3)' }}>
                    {message.model}
                  </span>
                )}
              </div>
            ))}
            {pending && <div className="bubble bubble--copilot">Thinking…</div>}
          </div>
        )}

        <div className="chat__form">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && send()}
            placeholder="Ask about this complaint"
            aria-label="Ask the copilot"
          />
          <button className="btn btn--sm" onClick={() => send()} disabled={pending}>
            Ask
          </button>
        </div>
      </div>
    </section>
  )
}
