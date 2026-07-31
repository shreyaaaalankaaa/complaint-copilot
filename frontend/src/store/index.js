import { configureStore } from '@reduxjs/toolkit'
import intake from './intakeSlice'
import complaints from './complaintsSlice'
import copilot from './copilotSlice'

export const store = configureStore({
  reducer: { intake, complaints, copilot },
})
