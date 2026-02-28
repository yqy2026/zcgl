import type { User } from '@/types/auth';
import type { CapabilitiesResponse, CapabilityItem } from '@/types/capability';

export interface AuthData {
  user: User;
  permissions: Array<{
    resource: string;
    action: string;
    description?: string;
  }>;
  capabilities?: CapabilityItem[];
  capabilities_cached_at?: string;
  capabilities_version?: string;
  capabilities_generated_at?: string;
}

export type AuthDataPersistence = 'local' | 'session';

export interface AuthDataOptions {
  persistence?: AuthDataPersistence;
}

export class AuthStorageClass {
  private readonly AUTH_DATA_KEY = 'authData';
  private readonly AUTH_DATA_UPDATED_AT_KEY = 'authDataUpdatedAt';
  private readonly USER_KEY = 'user';
  private readonly PERMISSIONS_KEY = 'permissions';
  private readonly LEGACY_TOKEN_KEYS = ['token', 'refresh_token', 'auth_token', 'refreshToken'];

  /**
   * Store authentication metadata (tokens remain in httpOnly cookies).
   */
  setAuthData(data: AuthData, options?: AuthDataOptions): void {
    const persistence = options?.persistence ?? 'local';
    const targetStorage = this.getStorageByPersistence(persistence);
    const secondaryStorage = persistence === 'session' ? localStorage : sessionStorage;

    try {
      // Keep only one active metadata source to avoid stale cross-storage reads.
      this.clearAuthDataFromStorage(secondaryStorage);
      this.writeAuthDataToStorage(targetStorage, data);
      this.clearLegacyTokenKeys(localStorage);
      this.clearLegacyTokenKeys(sessionStorage);
    } catch (error) {
      console.error('Failed to store auth data:', error);
      throw error;
    }
  }

  /**
   * Retrieve authentication metadata, reconciling session/local conflicts by freshness.
   */
  getAuthData(): AuthData | null {
    const sessionAuthData = this.getAuthDataFromStorage(sessionStorage);
    const localAuthData = this.getAuthDataFromStorage(localStorage);
    const preferredPersistence = this.resolvePreferredPersistence(sessionAuthData, localAuthData);
    if (preferredPersistence === 'session') {
      return sessionAuthData;
    }
    if (preferredPersistence === 'local') {
      return localAuthData;
    }
    return null;
  }

  /**
   * Get where current auth metadata is persisted.
   */
  getAuthPersistence(): AuthDataPersistence | null {
    const sessionAuthData = this.getAuthDataFromStorage(sessionStorage);
    const localAuthData = this.getAuthDataFromStorage(localStorage);
    return this.resolvePreferredPersistence(sessionAuthData, localAuthData);
  }

  private getAuthDataFromStorage(storage: Storage): AuthData | null {
    try {
      const stored = storage.getItem(this.AUTH_DATA_KEY);
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

  getCapabilities(): CapabilityItem[] {
    const authData = this.getAuthData();
    return authData?.capabilities ?? [];
  }

  getCapabilitiesCachedAt(): string | null {
    const authData = this.getAuthData();
    return authData?.capabilities_cached_at ?? null;
  }

  setCapabilitiesSnapshot(snapshot: CapabilitiesResponse): void {
    const authData = this.getAuthData();
    if (authData == null) {
      return;
    }

    const persistence = this.getAuthPersistence() ?? 'session';
    this.setAuthData(
      {
        ...authData,
        capabilities: snapshot.capabilities,
        capabilities_cached_at: new Date().toISOString(),
        capabilities_version: snapshot.version,
        capabilities_generated_at: snapshot.generated_at,
      },
      { persistence }
    );
  }

  clearCapabilitiesSnapshot(): void {
    try {
      this.clearCapabilitiesFromStorage(localStorage);
      this.clearCapabilitiesFromStorage(sessionStorage);
    } catch (error) {
      console.error('Failed to clear capabilities snapshot:', error);
    }
  }

  /**
   * Clear all authentication metadata from session/local storage.
   */
  clearAuthData(): void {
    try {
      this.clearAuthDataFromStorage(localStorage);
      this.clearAuthDataFromStorage(sessionStorage);
      this.clearLegacyTokenKeys(localStorage);
      this.clearLegacyTokenKeys(sessionStorage);
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

  private getStorageByPersistence(persistence: AuthDataPersistence): Storage {
    return persistence === 'session' ? sessionStorage : localStorage;
  }

  private writeAuthDataToStorage(storage: Storage, data: AuthData): void {
    storage.setItem(this.AUTH_DATA_KEY, JSON.stringify(data));
    storage.setItem(this.AUTH_DATA_UPDATED_AT_KEY, String(Date.now()));
    storage.setItem(this.USER_KEY, JSON.stringify(data.user));
    storage.setItem(this.PERMISSIONS_KEY, JSON.stringify(data.permissions));
  }

  private resolvePreferredPersistence(
    sessionAuthData: AuthData | null,
    localAuthData: AuthData | null
  ): AuthDataPersistence | null {
    if (sessionAuthData != null && localAuthData != null) {
      const sessionUpdatedAt = this.getAuthDataUpdatedAt(sessionStorage);
      const localUpdatedAt = this.getAuthDataUpdatedAt(localStorage);

      if (sessionUpdatedAt != null && localUpdatedAt != null) {
        if (sessionUpdatedAt > localUpdatedAt) {
          return 'session';
        }
        if (localUpdatedAt > sessionUpdatedAt) {
          return 'local';
        }
      } else if (sessionUpdatedAt != null && localUpdatedAt == null) {
        return 'session';
      } else if (localUpdatedAt != null && sessionUpdatedAt == null) {
        return 'local';
      }

      // When two different users are present without reliable recency metadata,
      // prefer shared localStorage to follow cross-tab account switches.
      if (sessionAuthData.user.id !== localAuthData.user.id) {
        return 'local';
      }

      return 'session';
    }

    if (sessionAuthData != null) {
      return 'session';
    }
    if (localAuthData != null) {
      return 'local';
    }
    return null;
  }

  private getAuthDataUpdatedAt(storage: Storage): number | null {
    const value = storage.getItem(this.AUTH_DATA_UPDATED_AT_KEY);
    if (value == null) {
      return null;
    }
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return null;
    }
    return parsed;
  }

  private clearAuthDataFromStorage(storage: Storage): void {
    storage.removeItem(this.AUTH_DATA_KEY);
    storage.removeItem(this.AUTH_DATA_UPDATED_AT_KEY);
    storage.removeItem(this.USER_KEY);
    storage.removeItem(this.PERMISSIONS_KEY);
    storage.removeItem('currentUser');
  }

  private clearCapabilitiesFromStorage(storage: Storage): void {
    const authData = this.getAuthDataFromStorage(storage);
    if (authData == null) {
      return;
    }

    const nextAuthData: AuthData = { ...authData };
    delete nextAuthData.capabilities;
    delete nextAuthData.capabilities_cached_at;
    delete nextAuthData.capabilities_version;
    delete nextAuthData.capabilities_generated_at;

    this.writeAuthDataToStorage(storage, nextAuthData);
  }

  private clearLegacyTokenKeys(storage: Storage): void {
    for (const key of this.LEGACY_TOKEN_KEYS) {
      storage.removeItem(key);
    }
  }
}

// Export singleton instance
export const AuthStorage = new AuthStorageClass();
