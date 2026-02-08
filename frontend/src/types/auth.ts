export interface LoginFormData {
  username: string;
  password: string;
  remember: boolean;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface User {
  id: string;
  username: string;
  email?: string;
  full_name: string;
  phone: string;
  role_id?: string;
  role_name?: string;
  roles?: string[];
  role_ids?: string[];
  is_admin?: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  // 个人资料相关字段
  last_login_at?: string;
  password_last_changed?: string;
  failed_login_attempts?: number;
  is_locked?: boolean;
  locked_until?: string;
  default_organization_id?: string;
  // 关联数据
  organization?: Organization;
  permissions?: Permission[];
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: string;
  name: string;
  parent_id?: string;
  level: number;
  path: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  permissions: Permission[];
  loading: boolean;
  error: string | null;
}

/** @deprecated Cookie 认证不再在响应体返回 Token。 */
export interface CookieAuthResponse {
  user: User;
  permissions: Permission[];
  message: string;
  auth_mode: 'cookie';
}

export interface AuthResponse {
  user: User;
  permissions: Permission[];
  message?: string;
  auth_mode?: 'cookie';
}

export interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details: unknown;
    timestamp: string;
  };
}

export interface UserActivity {
  id: string;
  user_id: string;
  action: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
  details?: Record<string, unknown>;
}
