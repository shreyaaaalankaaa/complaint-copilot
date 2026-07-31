import { useSelector } from 'react-redux'
import AgentTrace from './AgentTrace'
import RiskCard from './copilot/RiskCard'
import CompletenessCard from './copilot/CompletenessCard'
import DuplicatesCard from './copilot/DuplicatesCard'
import RootCauseCard from './copilot/RootCauseCard'
import CapaCard from './copilot/CapaCard'
import SummaryCard from './copilot/SummaryCard'
import CopilotChat from './copilot/CopilotChat'

export default function CopilotRail() {
  const { assessment, status, isValidComplaint, rejectionReason, savedComplaint } = useSelector(
    (state) => state.intake,
  )
  const running = status === 'analyzing'

  return (
    <aside className="copilot" aria-label="AI Copilot">
      <div className="copilot__banner">
        <div>
          <strong>AI Copilot</strong>
          <small style={{ display: 'block' }}>
            Risk assessment and investigation support
          </small>
        </div>
        <small>{assessment ? assessment.engine : 'idle'}</small>
      </div>

      {!isValidComplaint && rejectionReason && (
        <div className="notice notice--warn">
          <strong>Not logged as a complaint.</strong> {rejectionReason} Override by filling the
          form manually if you disagree.
        </div>
      )}

      <AgentTrace
        trace={assessment?.trace}
        running={running}
        engine={assessment?.engine}
        models={assessment?.models_used}
        latencyMs={assessment?.latency_ms}
      />

      {assessment && !running && (
        <>
          <RiskCard risk={assessment.risk} />
          <CompletenessCard report={assessment.completeness} />
          <DuplicatesCard duplicates={assessment.duplicates} />
          <SummaryCard summary={assessment.summary} />
          <RootCauseCard causes={assessment.root_causes} />
          <CapaCard capa={assessment.capa} />
          <CopilotChat complaintId={savedComplaint?.id} />
        </>
      )}

      {!assessment && !running && (
        <div className="card">
          <div className="empty">
            <strong>Nothing to assess yet</strong>
            Paste a complaint or drop a PDF and the copilot will fill the form, classify the risk
            and draft the investigation.
          </div>
        </div>
      )}
    </aside>
  )
}
