import { useDispatch, useSelector } from 'react-redux'
import ComplaintForm from '../components/ComplaintForm'
import CopilotChat from '../components/CopilotChat'
import { dismissError } from '../store/intakeSlice'

export default function LogComplaint() {
  const dispatch = useDispatch()
  const { error } = useSelector((state) => state.intake)

  return (
    <>
      {error && (
        <div className="notice notice--error" style={{ marginBottom: 14 }}>
          {error}{' '}
          <button className="btn btn--ghost btn--sm" onClick={() => dispatch(dismissError())}>
            Dismiss
          </button>
        </div>
      )}
      <div className="console">
        <ComplaintForm />
        <CopilotChat />
      </div>
    </>
  )
}
