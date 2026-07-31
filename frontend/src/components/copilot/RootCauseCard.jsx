export default function RootCauseCard({ causes }) {
  if (!causes?.length) return null

  return (
    <section className="card">
      <div className="card__head">
        <h2>Root cause hypotheses</h2>
        <span className="eyebrow">Ishikawa</span>
      </div>
      <div className="card__body">
        {causes.map((cause, index) => (
          <div className="cause" key={`${cause.category}-${index}`}>
            <div className="cause__head">
              <span className="cause__cat">{cause.category}</span>
              <span className="cause__conf">{Math.round((cause.confidence ?? 0) * 100)}%</span>
            </div>
            <p>{cause.hypothesis}</p>
            {cause.verification_step && <small>Verify by: {cause.verification_step}</small>}
          </div>
        ))}
      </div>
    </section>
  )
}
