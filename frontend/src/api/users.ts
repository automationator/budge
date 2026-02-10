import apiClient from './client'
import type { User, UserUpdate } from '@/types'

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/users/me')
  return response.data
}

export async function updateCurrentUser(data: UserUpdate): Promise<User> {
  const response = await apiClient.patch<User>('/users/me', data)
  return response.data
}

export async function deleteCurrentUser(): Promise<void> {
  await apiClient.delete('/users/me')
}
