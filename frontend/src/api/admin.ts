import apiClient from './client'
import type { SystemSettings } from '@/types'

export async function getSystemSettings(): Promise<SystemSettings> {
  const response = await apiClient.get<SystemSettings>('/admin/settings')
  return response.data
}

export async function updateSystemSettings(data: Partial<SystemSettings>): Promise<SystemSettings> {
  const response = await apiClient.patch<SystemSettings>('/admin/settings', data)
  return response.data
}
