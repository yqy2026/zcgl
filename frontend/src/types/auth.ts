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
  role: string;
  organization_id?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  // 个人资料相关字段
  phone?: string;
  last_login_at?: string;
  password_last_changed?: string;
  failed_login_attempts?: number;
  is_locked?: boolean;
  locked_until?: string;
  employee_id?: string;
  default_organization_id?: string;
  // 关联数据
  roles?: Role[];
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

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse {
  user: User;
  tokens: TokenResponse;
  message: string;
}

export interface AuthResponse {
  success: boolean;
  data: {
    user: User;
    token: string;
    refreshToken: string;
    permissions: Permission[];
  };
  message?: string;
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
