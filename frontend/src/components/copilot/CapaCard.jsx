const SECTIONS = [
  ['immediate_correction', 'Immediate correction'],
  ['corrective_actions', 'Corrective actions'],
  ['preventive_actions', 'Preventive actions'],
  ['effectiveness_checks', 'Effectiveness checks'],
]

export default function CapaCard({ capa }) {
  if (!capa || !SECTIONS.some(([key]) => capa[key]?.length)) return null

  return (
    <section className="card capa">
      <div className="card__head">
        <h2>Proposed CAPA</h2>
        {capa.target_closure_days && (
          <span className="eyebrow">Close in {capa.target_closure_days} days</span>
        )}
      </div>
      <div className="card__body">
        {SECTIONS.map(([key, label]) =>
          capa[key]?.length ? (
            <div key={key}>
              <h4>{label}</h4>
              <ul>
                {capa[key].map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null,
        )}
      </div>
    </section>
  )
}
