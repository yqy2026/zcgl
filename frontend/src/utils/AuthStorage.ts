import type { User } from '@/types/auth';

export interface AuthData {
  user: User;
  permissions: Array<{
    resource: string;
    action: string;
    description?: string;
  }>;
}

export class AuthStorageClass {
  private readonly AUTH_DATA_KEY = 'authData';
  private readonly USER_KEY = 'user';
  private readonly PERMISSIONS_KEY = 'permissions';
  private readonly LEGACY_TOKEN_KEYS = ['token', 'refresh_token', 'auth_token', 'refreshToken'];

  /**
   * Store authentication data in localStorage (no tokens)
   */
  setAuthData(data: AuthData): void {
    try {
      localStorage.setItem(this.AUTH_DATA_KEY, JSON.stringify(data));
      // Store user and permissions for legacy consumers
      localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
      localStorage.setItem(this.PERMISSIONS_KEY, JSON.stringify(data.permissions));
      this.clearLegacyTokenKeys();
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
      localStorage.removeItem(this.USER_KEY);
      localStorage.removeItem(this.PERMISSIONS_KEY);
      localStorage.removeItem('currentUser');
      this.clearLegacyTokenKeys();
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const user = this.getCurrentUser();
    return user != null;
  }

  private clearLegacyTokenKeys(): void {
    for (const key of this.LEGACY_TOKEN_KEYS) {
      localStorage.removeItem(key);
    }
  }
}

// Export singleton instance
export const AuthStorage = new AuthStorageClass();
