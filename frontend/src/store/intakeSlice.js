import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

/**
 * Owns the whole intake screen: the conversation, the form the agent fills, the
 * reviewer's edits on top of it, and the copilot assessment.
 *
 * Two things are worth calling out.
 *
 * `provenance` tags every field 'ai' or 'human' so the form can show who put each
 * value there. In a GxP system that is not decoration -- a record has to be
 * attributable.
 *
 * `threadId` is what makes the conversation work. The first turn sends a document;
 * every turn after that sends only a message, and the backend's LangGraph
 * checkpointer restores the form state for that thread.
 */

const EMPTY_DRAFT = {
  complaint_source: '', customer_name: '', received_date: '', reported_by: '',
  customer_site: '', country: '', contact_email: '',
  product_name: '', generic_name: '', product_type: '', dosage_form: '', strength: '',
  batch_no: '', mfg_date: '', expiry_date: '', quantity_supplied: '', quantity_affected: '',
  originating_site_block: '', impacted_npm: '',
  complaint_category: '', complaint_description: '',
  sample_available: null, adverse_event: null, severity: '',
}

const GREETING = {
  role: 'copilot',
  text:
    'Ready to process new complaints. You can paste the raw email from the customer, or upload a ' +
    'PDF of the complaint report. I will extract the data and run the initial risk assessment.',
}

const normalise = (draft) => {
  const merged = { ...EMPTY_DRAFT }
  Object.entries(draft || {}).forEach(([key, value]) => {
    if (key in merged && value !== null && value !== undefined) merged[key] = value
  })
  return merged
}

export const analyzeText = createAsyncThunk('intake/analyzeText', (text) => api.analyzeText(text))
export const analyzeFile = createAsyncThunk('intake/analyzeFile', (file) => api.analyzeFile(file))

/** Follow-up turn: "sorry, the batch number is BMX240602". */
export const correctForm = createAsyncThunk(
  'intake/correct',
  ({ message }, { getState }) => api.correct(getState().intake.threadId, message),
)

export const saveComplaint = createAsyncThunk(
  'intake/save',
  async (_, { getState, rejectWithValue }) => {
    const { intake } = getState()
    const draft = Object.fromEntries(
      Object.entries(intake.draft).filter(([, value]) => value !== '' && value !== null),
    )
    try {
      return await api.saveComplaint({
        draft,
        source_type: intake.sourceType,
        raw_text: intake.rawText,
        assessment: intake.assessment,
      })
    } catch (error) {
      return rejectWithValue(error.message)
    }
  },
)

const initialState = {
  status: 'idle', // idle | analyzing | correcting | ready | saving | saved | error
  error: null,
  threadId: null,
  sourceType: 'text',
  rawText: '',
  sourceName: '',
  messages: [GREETING],
  draft: { ...EMPTY_DRAFT },
  confidence: {},
  provenance: {},
  assessment: null,
  isValidComplaint: true,
  rejectionReason: null,
  savedComplaint: null,
  lastApplied: [],
}

/** Form-level state machine, mirroring the badge in the top right of the form. */
export const selectFormStage = (state) => {
  const { assessment, draft, savedComplaint } = state.intake
  if (savedComplaint) return { label: 'Committed', tone: 'ok' }
  if (!assessment) return { label: 'Pending Triage', tone: 'wait' }
  const blocking = ['customer_name', 'product_name', 'batch_no', 'complaint_description'].filter(
    (field) => !draft[field],
  )
  return blocking.length
    ? { label: 'Awaiting Details', tone: 'wait' }
    : { label: 'Ready to Commit', tone: 'ok' }
}

const applyResult = (state, payload, { sourceName, isCorrection } = {}) => {
  state.status = 'ready'
  state.threadId = payload.thread_id
  state.sourceType = payload.source_type || state.sourceType
  state.rawText = payload.raw_text || state.rawText
  if (sourceName) state.sourceName = sourceName
  state.draft = normalise(payload.draft)
  state.confidence = payload.field_confidence || {}
  state.assessment = payload.assessment
  state.isValidComplaint = payload.is_valid_complaint
  state.rejectionReason = payload.rejection_reason
  state.savedComplaint = null
  state.lastApplied = payload.applied_fields || []

  const previous = state.provenance
  state.provenance = Object.fromEntries(
    Object.entries(state.draft)
      .filter(([, value]) => value !== '' && value !== null)
      .map(([key]) => [
        key,
        // A field the reviewer corrected in chat stays theirs, not the agent's.
        isCorrection && state.lastApplied.includes(key) ? 'human' : previous[key] || 'ai',
      ]),
  )

  state.messages.push({
    role: 'copilot',
    text: isCorrection
      ? payload.patch_confirmation || 'I could not tell which field to change.'
      : payload.is_valid_complaint
        ? "Complaint parsed successfully. I've extracted the product details, mapped the batch " +
          'information, and generated an initial risk assessment. Form populated on the left.'
        : `I did not log this as a complaint. ${payload.rejection_reason}`,
    appliedFields: isCorrection ? state.lastApplied : undefined,
  })
}

const intakeSlice = createSlice({
  name: 'intake',
  initialState,
  reducers: {
    fieldChanged(state, action) {
      const { field, value } = action.payload
      state.draft[field] = value
      state.provenance[field] = 'human'
      state.savedComplaint = null
    },
    resetIntake: () => ({ ...initialState, draft: { ...EMPTY_DRAFT }, messages: [GREETING] }),
    dismissError(state) {
      state.error = null
      if (state.status === 'error') state.status = state.assessment ? 'ready' : 'idle'
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(analyzeText.pending, (state, action) => {
        state.status = 'analyzing'
        state.error = null
        state.messages.push({ role: 'user', text: action.meta.arg })
      })
      .addCase(analyzeText.fulfilled, (state, action) =>
        applyResult(state, action.payload, { sourceName: 'Pasted text' }),
      )
      .addCase(analyzeFile.pending, (state, action) => {
        state.status = 'analyzing'
        state.error = null
        state.sourceName = action.meta.arg.name
        state.messages.push({ role: 'user', attachment: action.meta.arg.name })
      })
      .addCase(analyzeFile.fulfilled, (state, action) =>
        applyResult(state, action.payload, { sourceName: action.meta.arg.name }),
      )
      .addCase(correctForm.pending, (state, action) => {
        state.status = 'correcting'
        state.messages.push({ role: 'user', text: action.meta.arg.message })
      })
      .addCase(correctForm.fulfilled, (state, action) =>
        applyResult(state, action.payload, { isCorrection: true }),
      )
      .addCase(saveComplaint.pending, (state) => {
        state.status = 'saving'
      })
      .addCase(saveComplaint.fulfilled, (state, action) => {
        state.status = 'saved'
        state.savedComplaint = action.payload
        state.messages.push({
          role: 'copilot',
          text: `Complaint committed to the register as ${action.payload.complaint_no}.`,
        })
      })
      .addMatcher(
        (action) => action.type.startsWith('intake/') && action.type.endsWith('/rejected'),
        (state, action) => {
          state.status = 'error'
          state.error = action.payload || action.error?.message || 'Something went wrong.'
          state.messages.push({ role: 'copilot', error: true, text: state.error })
        },
      )
  },
})

export const { fieldChanged, resetIntake, dismissError } = intakeSlice.actions
export default intakeSlice.reducer
