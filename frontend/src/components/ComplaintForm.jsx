import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api/client'
import { fieldChanged, resetIntake, saveComplaint, selectFormStage } from '../store/intakeSlice'
import Field from './Field'
import RiskAssessmentSection from './RiskAssessmentSection'
import AdditionalAnalysis from './AdditionalAnalysis'

const MANDATORY = ['customer_name', 'product_name', 'batch_no', 'complaint_description', 'received_date']
const AWAITING = 'Awaiting AI extraction…'

export default function ComplaintForm() {
  const dispatch = useDispatch()
  const { draft, confidence, provenance, status, savedComplaint, assessment, lastApplied } =
    useSelector((state) => state.intake)
  const stage = useSelector(selectFormStage)
  const [reference, setReference] = useState({
    categories: [], severities: [], complaint_sources: [], site_blocks: [], npm_options: [],
  })

  useEffect(() => {
    api.reference().then(setReference).catch(() => {})
  }, [])

  const change = (field, value) => dispatch(fieldChanged({ field, value }))
  const props = (name, placeholder = AWAITING) => ({
    name,
    value: draft[name],
    onChange: change,
    provenance: provenance[name],
    confidence: confidence[name],
    missing: MANDATORY.includes(name) && !draft[name] && status !== 'idle',
    required: MANDATORY.includes(name),
    justChanged: lastApplied?.includes(name),
    placeholder,
  })

  return (
    <section className="formpane">
      <header className="formpane__head">
        <div>
          <h1>Log Customer Complaint</h1>
          <p>API &amp; FDF Quality Assurance Module</p>
        </div>
        <span className={`stage stage--${stage.tone}`}>{stage.label}</span>
      </header>

      <div className="formpane__body">
        <fieldset className="fieldset">
          <legend className="section">1. Origin &amp; Customer Details</legend>
          <div className="grid">
            <Field label="Complaint Source" options={reference.complaint_sources} {...props('complaint_source')} />
            <Field label="Customer Name" {...props('customer_name')} />
            <Field label="Date Received" type="date" {...props('received_date')} />
            <Field label="Reported By" {...props('reported_by')} />
            <Field label="Contact Email" type="email" {...props('contact_email')} />
            <Field label="Country" {...props('country')} />
          </div>
        </fieldset>

        <fieldset className="fieldset">
          <legend className="section">2. Product &amp; Batch Identification</legend>
          <div className="grid">
            <Field label="Product Name (API/FDF)" {...props('product_name')} />
            <Field
              label={draft.product_type === 'API' ? 'Product Strength/Grade' : 'Product Strength'}
              {...props('strength')}
            />
            <Field label="Batch / Lot Number" {...props('batch_no')} />
            <Field label="Affected Quantity" {...props('quantity_affected')} />
            <Field label="Manufacturing Date" type="date" {...props('mfg_date')} />
            <Field label="Expiry Date" type="date" {...props('expiry_date')} />
            <Field label="Product Type" options={['API', 'FDF']} {...props('product_type')} />
            <Field label="Dosage Form" {...props('dosage_form')} />
          </div>
        </fieldset>

        <fieldset className="fieldset">
          <legend className="section">3. Facility &amp; Material Impact</legend>
          <div className="grid">
            <Field
              label="Originating Site Block"
              options={reference.site_blocks}
              {...props('originating_site_block', 'Awaiting AI classification…')}
            />
            <Field
              label="Impacted Non-Product Materials (NPM)"
              options={reference.npm_options}
              {...props('impacted_npm', 'e.g., Primary packaging')}
            />
          </div>
        </fieldset>

        <fieldset className="fieldset">
          <legend className="section">4. Defect Analysis</legend>
          <div className="grid">
            <Field label="Complaint Category" options={reference.categories} {...props('complaint_category')} />
            <Field label="Severity" options={reference.severities} {...props('severity')} />
            <Field
              label="Structured Defect Summary"
              textarea
              span
              {...props('complaint_description', 'AI will synthesize the complaint into a formal QMS description…')}
            />
            <div className="checkline">
              <input
                id="sample_available"
                type="checkbox"
                checked={Boolean(draft.sample_available)}
                onChange={(event) => change('sample_available', event.target.checked)}
              />
              <label htmlFor="sample_available">Complaint sample available for return</label>
            </div>
            <div className="checkline">
              <input
                id="adverse_event"
                type="checkbox"
                checked={Boolean(draft.adverse_event)}
                onChange={(event) => change('adverse_event', event.target.checked)}
              />
              <label htmlFor="adverse_event">Adverse event reported</label>
            </div>
          </div>
        </fieldset>

        <RiskAssessmentSection />
        <AdditionalAnalysis />
      </div>

      <div className="actionbar">
        <span className="spacer">
          {savedComplaint ? (
            <>Committed as <span className="mono">{savedComplaint.complaint_no}</span></>
          ) : (
            'Every field is editable. Correct anything in the copilot and it updates here.'
          )}
        </span>
        <button className="btn btn--ghost btn--sm" onClick={() => dispatch(resetIntake())}>
          New complaint
        </button>
        <button
          className="btn"
          disabled={status === 'saving' || !assessment || Boolean(savedComplaint)}
          onClick={() => dispatch(saveComplaint())}
        >
          {status === 'saving' ? 'Committing…' : 'Commit complaint'}
        </button>
      </div>
    </section>
  )
}
