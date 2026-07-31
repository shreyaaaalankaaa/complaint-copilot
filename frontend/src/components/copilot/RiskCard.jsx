const FLAG_LABELS = {
  potential_field_alert_report: 'Field Alert Report review',
  potential_recall_evaluation: 'Recall evaluation',
  requires_regulatory_reporting_review: 'Regulatory reporting review',
}

export default function RiskCard({ risk }) {
  if (!risk?.risk_level) return null
  const level = risk.risk_level.toLowerCase()

  return (
    <section className={`card risk risk--${level}`}>
      <div className="card__head">
        <h2>Risk assessment</h2>
        <span className="eyebrow">AI classified</span>
      </div>
      <div className="card__body">
        <div className="risk__top">
          <span className="risk__level">{risk.risk_level}</span>
          <span className="risk__score">{Math.round(risk.risk_score ?? 0)} / 100</span>
        </div>
        <div className={`risk__bar risk--${level}`} style={{ color: 'currentColor' }}>
          <i style={{ width: `${Math.min(100, risk.risk_score ?? 0)}%` }} />
        </div>
        <p>{risk.rationale}</p>
        {risk.patient_safety_impact && (
          <p>
            <strong>Patient safety: </strong>
            {risk.patient_safety_impact}
          </p>
        )}
        <div className="flags">
          {Object.entries(FLAG_LABELS).map(([key, label]) => (
            <span key={key} className={`flag ${risk.regulatory_flags?.[key] ? 'flag--on' : ''}`}>
              {label}
            </span>
          ))}
          {risk.regulatory_flags?.target_closure_days && (
            <span className="flag">Close within {risk.regulatory_flags.target_closure_days} days</span>
          )}
        </div>
      </div>
    </section>
  )
}
