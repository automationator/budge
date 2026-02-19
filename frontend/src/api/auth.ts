import apiClient from './client'
import type { User, UserUpdate, LoginRequest, RegisterRequest } from '@/types'

export async function login(data: LoginRequest): Promise<void> {
  await apiClient.post('/auth/login', data)
}

export async function register(data: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>('/users', data)
  return response.data
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}

export async function refreshTokens(): Promise<void> {
  await apiClient.post('/auth/refresh')
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/users/me')
  return response.data
}

export async function updateCurrentUser(data: UserUpdate): Promise<User> {
  const response = await apiClient.patch<User>('/users/me', data)
  return response.data
}
