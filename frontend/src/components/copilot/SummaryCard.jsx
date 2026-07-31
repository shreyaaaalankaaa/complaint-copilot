export default function SummaryCard({ summary }) {
  if (!summary) return null
  return (
    <section className="card">
      <div className="card__head">
        <h2>Complaint summary</h2>
        <span className="eyebrow">For QA review</span>
      </div>
      <div className="card__body">
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--ink-2)' }}>{summary}</p>
      </div>
    </section>
  )
}
