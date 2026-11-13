export interface ApiError {
  code: string
  message: string
  detail?: string
  trace_id?: string | null
}
