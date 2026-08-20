import http from './http'

export interface Notification {
  id: number
  title: string
  content: string
  type?: string
  is_read: boolean
  created_at?: string
}

export interface NotificationList {
  items: Notification[]
  total?: number
  unread?: number
  page?: number
  page_size?: number
}

export interface Announcement {
  id: number
  title: string
  content?: string
  published_at?: string
}

export function getNotifications(params: {
  page?: number
  page_size?: number
}): Promise<NotificationList> {
  return http.get<NotificationList>('/notifications', { params })
}

export function readNotification(id: number): Promise<unknown> {
  return http.post(`/notifications/${id}/read`)
}

export function readAllNotifications(): Promise<{ count?: number }> {
  return http.post<{ count?: number }>('/notifications/read-all')
}

export async function getAnnouncements(): Promise<Announcement[]> {
  const res = await http.get<{ items?: Announcement[] } | Announcement[]>('/announcements')
  return Array.isArray(res) ? res : (res.items ?? [])
}

export interface Banner {
  id: number
  title: string
  subtitle?: string
  image_url?: string
  link_type?: string
  link_value?: string
}

export async function getBanners(): Promise<Banner[]> {
  const res = await http.get<{ items?: Banner[] } | Banner[]>('/banners')
  return Array.isArray(res) ? res : (res.items ?? [])
}