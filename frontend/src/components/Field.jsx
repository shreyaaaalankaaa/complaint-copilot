/**
 * One form control plus its provenance strip.
 *
 * The coloured edge and the tag answer a question an auditor will ask: who put
 * this value in the record? Indigo = the agent extracted it, teal = a reviewer
 * typed or corrected it. Editing an AI-filled field flips it to human and the
 * confidence meter disappears, because the machine's confidence in a value it
 * no longer owns is meaningless.
 */
export default function Field({
  label,
  name,
  value,
  onChange,
  provenance,
  confidence,
  required = false,
  missing = false,
  type = 'text',
  options,
  textarea = false,
  span = false,
  placeholder,
  justChanged = false,
}) {
  const id = `field-${name}`
  const className = [
    'field',
    provenance === 'ai' ? 'field--ai' : provenance === 'human' ? 'field--human' : '',
    missing ? 'field--missing' : '',
    justChanged ? 'field--flash' : '',
    span ? 'grid--full' : '',
  ]
    .filter(Boolean)
    .join(' ')

  const handle = (event) => onChange(name, event.target.value)

  return (
    <div className={className}>
      <label className="field__label" htmlFor={id}>
        {label}
        {required && <span className="req" aria-label="required">*</span>}
      </label>

      {options ? (
        <select id={id} value={value ?? ''} onChange={handle}>
          <option value=""></option>
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      ) : textarea ? (
        <textarea id={id} value={value ?? ''} onChange={handle} placeholder={placeholder} />
      ) : (
        <input id={id} type={type} value={value ?? ''} onChange={handle} placeholder={placeholder} />
      )}

      <div className="field__meta">
        {provenance === 'ai' && (
          <>
            <span className="tag tag--ai">AI</span>
            {confidence != null && (
              <>
                <span className="meter" aria-hidden="true">
                  <i style={{ width: `${Math.round(confidence * 100)}%` }} />
                </span>
                <span className="field__conf">{Math.round(confidence * 100)}% confidence</span>
              </>
            )}
          </>
        )}
        {provenance === 'human' && <span className="tag tag--human">Edited</span>}
      </div>
    </div>
  )
}
