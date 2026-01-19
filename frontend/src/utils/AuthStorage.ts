export interface AuthData {
  token: string;
  refreshToken: string;
  user: {
    id: string;
    username: string;
    email?: string;
    full_name?: string;
    role?: string;
    organization_id?: string;
  };
  permissions: Array<{
    resource: string;
    action: string;
    description?: string;
  }>;
}

export class AuthStorageClass {
  private readonly AUTH_DATA_KEY = 'authData';
  private readonly TOKEN_KEY = 'token';
  private readonly REFRESH_TOKEN_KEY = 'refresh_token';

  /**
   * Store authentication data in localStorage
   */
  setAuthData(data: AuthData): void {
    try {
      localStorage.setItem(this.AUTH_DATA_KEY, JSON.stringify(data));
      // Also set individual keys for backward compatibility
      localStorage.setItem(this.TOKEN_KEY, data.token);
      localStorage.setItem(this.REFRESH_TOKEN_KEY, data.refreshToken);
    } catch (error) {
      console.error('Failed to store auth data:', error);
      throw error;
    }
  }

  /**
   * Retrieve authentication data from localStorage
   */
  getAuthData(): AuthData | null {
    try {
      const stored = localStorage.getItem(this.AUTH_DATA_KEY);
      if (stored == null) {
        return null;
      }
      return JSON.parse(stored) as AuthData;
    } catch (error) {
      console.error('Failed to retrieve auth data:', error);
      return null;
    }
  }

  /**
   * Get access token
   */
  getToken(): string | null {
    const authData = this.getAuthData();
    return authData?.token ?? null;
  }

  /**
   * Get refresh token
   */
  getRefreshToken(): string | null {
    const authData = this.getAuthData();
    return authData?.refreshToken ?? null;
  }

  /**
   * Get current user
   */
  getCurrentUser(): AuthData['user'] | null {
    const authData = this.getAuthData();
    return authData?.user ?? null;
  }

  /**
   * Get user permissions
   */
  getPermissions(): AuthData['permissions'] {
    const authData = this.getAuthData();
    return authData?.permissions ?? [];
  }

  /**
   * Clear all authentication data from localStorage
   */
  clearAuthData(): void {
    try {
      localStorage.removeItem(this.AUTH_DATA_KEY);
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(this.REFRESH_TOKEN_KEY);
      localStorage.removeItem('refreshToken'); // Remove old camelCase key
      localStorage.removeItem('user');
      localStorage.removeItem('permissions');
      localStorage.removeItem('currentUser');
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = this.getToken();
    return token != null && token.trim() !== '';
  }
}

// Export singleton instance
export const AuthStorage = new AuthStorageClass();
