// Typen fuer API-Responses — Felder entsprechen den Pydantic-Out-Schemas
// des Backends (admin/app/schemas.py). Datumswerte kommen als ISO-Strings an.

export interface AdminUser {
  id: number
  username: string
  is_admin: boolean
  created_at: string | null
  last_login: string | null
}

export interface SmtpUser {
  id: number
  username: string
  is_active: boolean
  company: string | null
  service: string | null
  mail_domain: string | null
  contact_email: string | null
  receive_reports: boolean
  package_id: number | null
  package_name: string | null
  origin: string
  portal_managed: boolean
  created_at: string | null
  created_by: number | null
  last_used_at: string | null
}

export interface IpBan {
  id: number
  ip_address: string
  reason: string
  ban_count: number
  fail_count: number
  banned_at: string | null
  expires_at: string | null
  is_active: boolean
}

export interface Network {
  id: number
  cidr: string
  owner: string
  is_protected: boolean
  created_at: string | null
}

export interface MailEvent {
  id: number
  timestamp: string
  queue_id: string | null
  sender: string | null
  recipient: string | null
  status: string
  relay: string | null
  delay: number | null
  dsn: string | null
  dsn_code: string | null
  remote_response: string | null
  size: number | null
  message: string | null
  client_ip: string | null
  sasl_username: string | null
}
