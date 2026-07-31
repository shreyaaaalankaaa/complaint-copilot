import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '../api/client'

export const fetchComplaints = createAsyncThunk('complaints/fetch', (filters = {}) =>
  api.listComplaints(filters),
)
export const fetchStats = createAsyncThunk('complaints/stats', () => api.stats())
export const fetchComplaint = createAsyncThunk('complaints/one', (id) => api.getComplaint(id))
export const changeStatus = createAsyncThunk('complaints/status', ({ id, status, reason }) =>
  api.updateStatus(id, status, reason),
)

const complaintsSlice = createSlice({
  name: 'complaints',
  initialState: { items: [], stats: null, selected: null, loading: false, filters: {}, error: null },
  reducers: {
    filterChanged(state, action) {
      state.filters = { ...state.filters, ...action.payload }
    },
    clearSelection(state) {
      state.selected = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchComplaints.pending, (state) => {
        state.loading = true
      })
      .addCase(fetchComplaints.fulfilled, (state, action) => {
        state.loading = false
        state.items = action.payload
      })
      .addCase(fetchStats.fulfilled, (state, action) => {
        state.stats = action.payload
      })
      .addCase(fetchComplaint.fulfilled, (state, action) => {
        state.selected = action.payload
      })
      .addCase(changeStatus.fulfilled, (state, action) => {
        state.items = state.items.map((item) =>
          item.id === action.payload.id ? action.payload : item,
        )
        if (state.selected?.complaint?.id === action.payload.id) {
          state.selected.complaint = action.payload
        }
      })
  },
})

export const { filterChanged, clearSelection } = complaintsSlice.actions
export default complaintsSlice.reducer
