export default function CompletenessCard({ report }) {
  if (!report) return null

  return (
    <section className="card">
      <div className="card__head">
        <h2>Completeness</h2>
        <span className="eyebrow">{report.investigation_ready ? 'Ready' : 'Blocked'}</span>
      </div>
      <div className="card__body">
        <div className="progress">
          <div className="progress__track">
            <i style={{ width: `${report.score}%` }} />
          </div>
          <strong>{report.score}%</strong>
        </div>

        <ul className="checklist">
          {report.missing_mandatory?.map((item) => (
            <li key={item} className="miss">
              {item} — required before the investigation can open
            </li>
          ))}
          {report.missing_mandatory?.length === 0 && (
            <li className="ok">All mandatory fields captured</li>
          )}
          {report.missing_recommended?.slice(0, 4).map((item) => (
            <li key={item}>{item} — recommended</li>
          ))}
        </ul>

        {report.follow_up_questions?.length > 0 && (
          <>
            <p className="eyebrow" style={{ marginTop: 14 }}>Ask the complainant</p>
            <ul className="checklist">
              {report.follow_up_questions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  )
}
