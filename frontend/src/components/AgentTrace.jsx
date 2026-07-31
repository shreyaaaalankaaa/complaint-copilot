import { useEffect, useState } from 'react'

/**
 * The signature element of this screen.
 *
 * While the request is in flight the nodes light up in graph order so the wait
 * has a shape. When the response lands, the placeholder is replaced by the real
 * trace the backend measured -- node name, which Groq model ran it, and actual
 * latency. Nothing here is invented: the timings shown after completion come
 * from `assessment.trace`, which each node writes as it finishes.
 */
const PIPELINE = [
  ['triage', 'Triage input'],
  ['extract', 'Extract complaint fields'],
  ['check_completeness', 'Check complaint completeness'],
  ['scan_duplicates', 'Scan for duplicates'],
  ['classify_risk', 'Classify risk'],
  ['recommend_root_cause', 'Recommend root causes'],
  ['draft_capa', 'Draft CAPA plan'],
  ['write_summary', 'Write complaint summary'],
  ['assemble', 'Assemble copilot output'],
]

export default function AgentTrace({ trace, running, engine, models = [], latencyMs }) {
  const [cursor, setCursor] = useState(0)

  useEffect(() => {
    if (!running) return undefined
    setCursor(0)
    const timer = setInterval(() => setCursor((n) => Math.min(n + 1, PIPELINE.length - 1)), 420)
    return () => clearInterval(timer)
  }, [running])

  const rows = running
    ? PIPELINE.map(([node, label], index) => ({
        node,
        label,
        status: index < cursor ? 'ok' : index === cursor ? 'running' : 'pending',
      }))
    : trace

  if (!rows?.length) return null

  return (
    <section className="card">
      <div className="card__head">
        <h2>Agent run</h2>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--ink-3)' }}>
          {running ? 'running' : `${engine} · ${latencyMs} ms`}
        </span>
      </div>
      <div className="card__body">
        <ul className="trace">
          {rows.map((step, index) => (
            <li key={`${step.node}-${index}`}>
              <span className={`trace__dot trace__dot--${step.status}`} aria-hidden="true" />
              <span className="trace__label">
                {step.label}
                <span className="trace__node">
                  {step.node}
                  {step.model ? ` · ${step.model}` : ''}
                  {step.note ? ` · ${step.note}` : ''}
                </span>
              </span>
              <span className="trace__timing">
                {step.latency_ms != null ? `${step.latency_ms} ms` : ''}
              </span>
            </li>
          ))}
        </ul>
        {!running && models.length > 0 && (
          <p style={{ margin: '12px 0 0', fontSize: 11.5, color: 'var(--ink-3)' }}>
            Models used: <span className="mono">{models.join(', ')}</span>
          </p>
        )}
      </div>
    </section>
  )
}
