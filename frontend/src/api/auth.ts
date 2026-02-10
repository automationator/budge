import apiClient from './client'
import type { User, UserUpdate, LoginRequest, LoginResponse, RegisterRequest } from '@/types'

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', data)
  return response.data
}

export async function register(data: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>('/users', data)
  return response.data
}

export async function logout(refreshToken: string): Promise<void> {
  await apiClient.post('/auth/logout', { refresh_token: refreshToken })
}

export async function refreshTokens(refreshToken: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return response.data
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/users/me')
  return response.data
}

export async function updateCurrentUser(data: UserUpdate): Promise<User> {
  const response = await apiClient.patch<User>('/users/me', data)
  return response.data
}
