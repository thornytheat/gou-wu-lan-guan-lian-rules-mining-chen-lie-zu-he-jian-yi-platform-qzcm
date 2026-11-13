import axios, { type AxiosInstance, type AxiosError } from 'axios'
import type { ApiError } from '../types/api'

export const TOKEN_KEY = 'basketrule_token'

export class RequestError extends Error {
  code: string
  status: number
  traceId: string | null

  constructor(message: string, code = 'NETWORK', status = 0, traceId: string | null = null) {
    super(message)
    this.name = 'RequestError'
    this.code = code
    this.status = status
    this.traceId = traceId
  }
}

function normalize(error: AxiosError<ApiError>): RequestError {
  const body = error.response?.data
  if (body?.message) {
    return new RequestError(body.message, body.code ?? 'ERROR', error.response?.status ?? 0, body.trace_id ?? null)
  }
  if (error.code === 'ECONNABORTED') {
    return new RequestError('请求超时，挖掘批次可能还在跑，稍后刷新看看。', 'TIMEOUT')
  }
  if (!error.response) {
    return new RequestError('接口暂时不可用，请确认容器状态后重试。', 'NETWORK')
  }
  return new RequestError(`请求失败（HTTP ${error.response.status}）`, 'ERROR', error.response.status)
}

export function createHttp(baseURL: string): AxiosInstance {
  const instance = axios.create({ baseURL, timeout: 40000 })
  instance.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ApiError>) => Promise.reject(normalize(error)),
  )
  return instance
}
