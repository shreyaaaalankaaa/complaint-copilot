import { useState } from 'react'
import { useSelector } from 'react-redux'
import CompletenessCard from './copilot/CompletenessCard'
import DuplicatesCard from './copilot/DuplicatesCard'
import RootCauseCard from './copilot/RootCauseCard'
import CapaCard from './copilot/CapaCard'
import SummaryCard from './copilot/SummaryCard'
import AgentTrace from './AgentTrace'

/**
 * The bonus AI features, kept out of the main flow on purpose.
 *
 * The core screen mirrors the demo one-to-one. Completeness, duplicate detection,
 * root cause, CAPA and the agent trace are additions, so they live behind a
 * disclosure where they inform the reviewer without competing with the form.
 */
export default function AdditionalAnalysis() {
  const { assessment } = useSelector((state) => state.intake)
  const [open, setOpen] = useState(false)
  if (!assessment) return null

  const duplicateCount = assessment.duplicates?.length || 0

  return (
    <section className="extra">
      <button className="extra__toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className="extra__chevron" aria-hidden="true">{open ? '▾' : '▸'}</span>
        Additional AI analysis
        <span className="extra__hint">
          completeness {assessment.completeness?.score ?? 0}%
          {duplicateCount > 0 && ` · ${duplicateCount} possible duplicate${duplicateCount > 1 ? 's' : ''}`}
          {' · root cause · CAPA'}
        </span>
      </button>

      {open && (
        <div className="extra__body">
          <CompletenessCard report={assessment.completeness} />
          <DuplicatesCard duplicates={assessment.duplicates} />
          <SummaryCard summary={assessment.summary} />
          <RootCauseCard causes={assessment.root_causes} />
          <CapaCard capa={assessment.capa} />
          <AgentTrace
            trace={assessment.trace}
            running={false}
            engine={assessment.engine}
            models={assessment.models_used}
            latencyMs={assessment.latency_ms}
          />
        </div>
      )}
    </section>
  )
}
