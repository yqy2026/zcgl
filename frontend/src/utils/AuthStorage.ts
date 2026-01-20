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
      const sanitizedData: AuthData = {
        ...data,
        token: '',
        refreshToken: '',
      };
      localStorage.setItem(this.AUTH_DATA_KEY, JSON.stringify(sanitizedData));
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(this.REFRESH_TOKEN_KEY);
      localStorage.removeItem('refreshToken');
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
    const token = authData?.token?.trim();
    return token != null && token !== '' ? token : null;
  }

  /**
   * Get refresh token
   */
  getRefreshToken(): string | null {
    const authData = this.getAuthData();
    const refreshToken = authData?.refreshToken?.trim();
    return refreshToken != null && refreshToken !== '' ? refreshToken : null;
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
    const authData = this.getAuthData();
    return authData?.user?.id != null && authData.user.id.trim() !== '';
  }
}

// Export singleton instance
export const AuthStorage = new AuthStorageClass();
