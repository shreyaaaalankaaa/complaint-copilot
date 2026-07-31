import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  changeStatus, clearSelection, fetchComplaint, fetchComplaints, fetchStats, filterChanged,
} from '../store/complaintsSlice'

const STATUSES = ['Draft', 'Under Investigation', 'Pending CAPA', 'Closed', 'Rejected']

export default function ComplaintRegister() {
  const dispatch = useDispatch()
  const { items, stats, selected, loading, filters } = useSelector((state) => state.complaints)

  useEffect(() => {
    dispatch(fetchComplaints(filters))
    dispatch(fetchStats())
  }, [dispatch, filters])

  return (
    <>
      <header className="page-head">
        <div>
          <p className="eyebrow">Quality management · Register</p>
          <h1>Complaint register</h1>
          <p>Every complaint logged in the system, with the AI risk classification it was saved with.</p>
        </div>
        <input
          placeholder="Search product, batch or customer"
          onChange={(event) => dispatch(filterChanged({ q: event.target.value }))}
          style={{ padding: '8px 10px', border: '1px solid var(--rule)', borderRadius: 3, minWidth: 260 }}
          aria-label="Search complaints"
        />
      </header>

      {stats && (
        <div className="stats">
          <div className="stat">
            <span className="eyebrow">Total</span>
            <b>{stats.total}</b>
          </div>
          <div className="stat">
            <span className="eyebrow">Open</span>
            <b>{stats.open}</b>
          </div>
          <div className="stat">
            <span className="eyebrow">Critical</span>
            <b style={{ color: 'var(--critical)' }}>{stats.by_severity?.Critical || 0}</b>
          </div>
          <div className="stat">
            <span className="eyebrow">Major</span>
            <b style={{ color: 'var(--major)' }}>{stats.by_severity?.Major || 0}</b>
          </div>
        </div>
      )}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Complaint</th>
              <th>Customer</th>
              <th>Product</th>
              <th>Batch</th>
              <th>Category</th>
              <th>Severity</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id} onClick={() => dispatch(fetchComplaint(row.id))}>
                <td className="mono">{row.complaint_no}</td>
                <td>{row.customer_name || '—'}</td>
                <td>{row.product_name || '—'}</td>
                <td className="mono">{row.batch_no || '—'}</td>
                <td>{row.complaint_category || '—'}</td>
                <td>
                  <span className={`pill pill--${(row.severity || 'muted').toLowerCase()}`}>
                    {row.severity || 'Unclassified'}
                  </span>
                </td>
                <td>
                  <span className="pill pill--muted">{row.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && items.length === 0 && (
          <div className="empty">
            <strong>No complaints yet</strong>
            Log one from the intake screen, or run the seed script to load history.
          </div>
        )}
      </div>

      {selected && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="card__head">
            <h2>
              <span className="mono">{selected.complaint.complaint_no}</span> ·{' '}
              {selected.complaint.product_name}
            </h2>
            <button className="btn btn--ghost btn--sm" onClick={() => dispatch(clearSelection())}>
              Close
            </button>
          </div>
          <div className="card__body">
            <p style={{ marginTop: 0 }}>{selected.complaint.complaint_description}</p>

            {selected.assessment && (
              <>
                <p className="eyebrow">AI assessment at time of logging</p>
                <p style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>
                  <strong>{selected.assessment.risk_level}</strong> ({Math.round(selected.assessment.risk_score ?? 0)}/100) —{' '}
                  {selected.assessment.rationale}
                </p>
                <p style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>{selected.assessment.summary}</p>
              </>
            )}

            <p className="eyebrow" style={{ marginTop: 16 }}>Audit trail</p>
            <ul className="checklist">
              {selected.audit_trail.map((entry) => (
                <li key={entry.id}>
                  <span>
                    <span className="mono">{new Date(entry.at).toLocaleString()}</span> · {entry.action} by{' '}
                    {entry.actor}
                    {entry.reason ? ` — ${entry.reason}` : ''}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="actionbar">
            <span className="spacer">Change status</span>
            {STATUSES.filter((status) => status !== selected.complaint.status).map((status) => (
              <button
                key={status}
                className="btn btn--ghost btn--sm"
                onClick={() =>
                  dispatch(
                    changeStatus({
                      id: selected.complaint.id,
                      status,
                      reason: 'Updated from complaint register',
                    }),
                  ).then(() => dispatch(fetchComplaint(selected.complaint.id)))
                }
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
