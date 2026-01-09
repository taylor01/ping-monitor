import axios from 'axios'
import { setTokens, clearTokens } from './client'

// In dev mode, use relative path (proxied by Vite). In production, use env var.
const API_URL = import.meta.env.DEV ? '/api/v1' : (import.meta.env.VITE_API_URL || '/api/v1')

interface LoginCredentials {
  email: string
  password: string
}

export async function login(credentials: LoginCredentials): Promise<boolean> {
  try {
    const response = await axios.post(`${API_URL}/auth/token`, {
      authenticatable_type: 'user',
      identifier: credentials.email,
      secret: credentials.password,
    })

    const { access_token, refresh_token, expires_in } = response.data.data
    setTokens(access_token, refresh_token, expires_in)
    return true
  } catch {
    return false
  }
}

export function logout(): void {
  clearTokens()
}

export function isAuthenticated(): boolean {
  const token = localStorage.getItem('access_token')
  return !!token
}
