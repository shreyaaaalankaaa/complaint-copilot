export default function DuplicatesCard({ duplicates }) {
  return (
    <section className="card">
      <div className="card__head">
        <h2>Possible duplicates</h2>
        <span className="eyebrow">{duplicates?.length || 0} found</span>
      </div>
      <div className="card__body">
        {!duplicates?.length ? (
          <p style={{ margin: 0, fontSize: 12.5, color: 'var(--ink-2)' }}>
            No open or historical complaint matches this batch, product or narrative.
          </p>
        ) : (
          duplicates.map((hit) => (
            <div className="dupe" key={hit.complaint_id}>
              <div className="dupe__head">
                <span className="mono">{hit.complaint_no}</span>
                <span className="dupe__sim">{Math.round(hit.similarity * 100)}% match</span>
              </div>
              <div className="dupe__meta">
                {hit.product_name} · batch <span className="mono">{hit.batch_no}</span> · {hit.status}
              </div>
              <div className="dupe__meta" style={{ color: 'var(--ink-3)' }}>
                Matched on {hit.matched_on.join(', ')}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
