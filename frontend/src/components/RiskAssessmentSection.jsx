import { useSelector } from 'react-redux'

/**
 * Section 5 of the form, not a sidebar card. The risk assessment belongs on the
 * record because it is part of what gets committed, and the reviewer reads it in
 * the same eye-line as the defect description it is judging.
 */
export default function RiskAssessmentSection() {
  const { assessment } = useSelector((state) => state.intake)
  const risk = assessment?.risk
  if (!risk?.risk_level) return null
  const level = risk.risk_level.toLowerCase()

  return (
    <section className={`riskpanel riskpanel--${level}`}>
      <h3>
        <span className="riskpanel__mark" aria-hidden="true">◈</span> AI copilot risk assessment
      </h3>

      <div className="grid">
        <div className="readout">
          <span className="readout__label">Severity (Suggested)</span>
          <output className={`readout__value readout__value--${level}`}>{risk.risk_level}</output>
        </div>
        <div className="readout">
          <span className="readout__label">Suggested Next Action</span>
          <output className="readout__value">{risk.suggested_next_action || '—'}</output>
        </div>
      </div>

      <div className="readout" style={{ marginTop: 12 }}>
        <span className="readout__label">Initial Risk Assessment</span>
        <output className="readout__prose">
          {risk.rationale}
          {risk.patient_safety_impact ? ` ${risk.patient_safety_impact}` : ''}
        </output>
      </div>

      <div className="flags">
        {risk.regulatory_flags?.potential_field_alert_report && <span className="flag flag--on">Field Alert Report review</span>}
        {risk.regulatory_flags?.potential_recall_evaluation && <span className="flag flag--on">Recall evaluation</span>}
        {risk.regulatory_flags?.requires_regulatory_reporting_review && <span className="flag">Regulatory reporting review</span>}
        {risk.regulatory_flags?.target_closure_days && (
          <span className="flag">Close within {risk.regulatory_flags.target_closure_days} days</span>
        )}
      </div>
    </section>
  )
}
