import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

export const askCopilot = createAsyncThunk('copilot/ask', ({ question, complaintId }) =>
  api.ask(question, complaintId),
)

const copilotSlice = createSlice({
  name: 'copilot',
  initialState: { messages: [], pending: false },
  reducers: {
    clearChat(state) {
      state.messages = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(askCopilot.pending, (state, action) => {
        state.pending = true
        state.messages.push({ role: 'user', text: action.meta.arg.question })
      })
      .addCase(askCopilot.fulfilled, (state, action) => {
        state.pending = false
        state.messages.push({
          role: 'copilot',
          text: action.payload.answer,
          model: action.payload.model,
          confidence: action.payload.confidence,
        })
      })
      .addCase(askCopilot.rejected, (state, action) => {
        state.pending = false
        state.messages.push({
          role: 'copilot',
          text: action.error?.message || 'The copilot could not answer that.',
          error: true,
        })
      })
  },
})

export const { clearChat } = copilotSlice.actions
export default copilotSlice.reducer
