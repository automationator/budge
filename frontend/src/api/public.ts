import axios from 'axios'
import type { RegistrationStatus } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Use plain axios (no auth interceptor) for public endpoints
export async function getRegistrationStatus(): Promise<RegistrationStatus> {
  const response = await axios.get<RegistrationStatus>(`${API_BASE_URL}/public/registration-status`)
  return response.data
}
