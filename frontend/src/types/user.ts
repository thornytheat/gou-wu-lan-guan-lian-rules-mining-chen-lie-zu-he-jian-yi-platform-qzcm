export type UserRole = 'admin' | 'analyst' | 'viewer'

export interface User {
  id: string
  email: string
  display_name: string
  role: UserRole
  permissions: string[]
  is_active: boolean
}

export interface LoginResult {
  access_token: string
  token: string
  token_type: string
  user: User
}
