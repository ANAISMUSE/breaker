import http from '@/api/http'

export interface UserProfile {
  username: string
  role: 'admin' | 'user'
  nickname: string | null
  email: string | null
  phone: string | null
  avatar: string | null
  created_at: string
  updated_at: string
}

export interface UserProfilePatch {
  nickname: string | null
  email: string | null
  phone: string | null
  avatar: string | null
}

export async function getMyProfile() {
  const { data } = await http.get<UserProfile>('/api/users/me')
  return data
}

export async function updateMyProfile(payload: UserProfilePatch) {
  const { data } = await http.patch<UserProfile>('/api/users/me', payload)
  return data
}

export async function listUsers() {
  const { data } = await http.get<UserProfile[]>('/api/users')
  return data
}

export async function updateUserRole(username: string, role: 'admin' | 'user') {
  const { data } = await http.patch<UserProfile>(`/api/users/${encodeURIComponent(username)}/role`, { role })
  return data
}
