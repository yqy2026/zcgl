import { expect, type Page } from '@playwright/test';

export interface Credentials {
  username: string;
  password: string;
}

const LOGIN_PATH = '/login';

const readNodeEnv = (name: string): string | undefined => {
  const rawValue = process.env[name];
  return typeof rawValue === 'string' && rawValue !== '' ? rawValue : undefined;
};

const dedupeCredentials = (credentials: Credentials[]): Credentials[] => {
  const seen = new Set<string>();
  const uniqueCredentials: Credentials[] = [];

  for (const credential of credentials) {
    const key = `${credential.username}:${credential.password}`;
    if (!seen.has(key)) {
      seen.add(key);
      uniqueCredentials.push(credential);
    }
  }

  return uniqueCredentials;
};

const toCredential = (username: string | undefined, password: string | undefined): Credentials | null => {
  if (username == null || username === '' || password == null || password === '') {
    return null;
  }
  return { username, password };
};

const readPasswordCandidates = (rolePrefix: string): string[] => {
  const directCandidate = readNodeEnv(`${rolePrefix}_PASSWORD`);
  const fallbackCandidate = readNodeEnv('E2E_PASSWORD');
  if (directCandidate != null) {
    return [directCandidate];
  }

  if (fallbackCandidate != null) {
    return [fallbackCandidate];
  }

  const defaults = ['admin123', 'Admin123!@#', 'password123'];

  const candidates = [
    ...defaults,
  ].filter((item): item is string => item != null && item !== '');

  return [...new Set(candidates)];
};

export const resolveAdminCredentialCandidates = (): Credentials[] => {
  const username =
    readNodeEnv('E2E_ADMIN_USERNAME') ??
    readNodeEnv('E2E_USERNAME') ??
    'admin';
  const passwordCandidates = readPasswordCandidates('E2E_ADMIN');

  return dedupeCredentials(
    passwordCandidates.map(password => ({
      username,
      password,
    }))
  );
};

export const resolveRoleCredentialCandidates = (
  role: 'ASSET_MANAGER' | 'ASSET_VIEWER',
  fallbackCredentials: Credentials[]
): Credentials[] => {
  const explicitCredential = toCredential(
    readNodeEnv(`E2E_${role}_USERNAME`),
    readNodeEnv(`E2E_${role}_PASSWORD`)
  );

  if (explicitCredential == null) {
    return fallbackCredentials;
  }

  return dedupeCredentials([explicitCredential, ...fallbackCredentials]);
};

export const resolveRegularCredential = (): Credentials | null =>
  toCredential(
    readNodeEnv('E2E_REGULAR_USERNAME') ?? readNodeEnv('E2E_USER_USERNAME'),
    readNodeEnv('E2E_REGULAR_PASSWORD') ?? readNodeEnv('E2E_USER_PASSWORD')
  );

export const resolveLogoutCredential = (): Credentials | null =>
  toCredential(
    readNodeEnv('E2E_LOGOUT_USERNAME'),
    readNodeEnv('E2E_LOGOUT_PASSWORD')
  );

const usernameSelector =
  'input#identifier, input[name="identifier"], input#login_username, input[name="username"]';
const passwordSelector = 'input#login_password, input[name="password"]';
const submitSelector = 'button[type="submit"]';

const navigateWithRetry = async (
  page: Page,
  path: string,
  attempts: number = 2
): Promise<void> => {
  let lastError: unknown = null;

  for (let index = 0; index < attempts; index += 1) {
    try {
      await page.goto(path, {
        waitUntil: 'domcontentloaded',
        timeout: 20_000,
      });
      return;
    } catch (error) {
      lastError = error;
      if (index + 1 >= attempts) {
        throw error;
      }
      await page.waitForTimeout(300);
    }
  }

  if (lastError instanceof Error) {
    throw lastError;
  }
};

export const loginWithCredential = async (page: Page, credential: Credentials): Promise<boolean> => {
  await navigateWithRetry(page, LOGIN_PATH);

  const usernameInput = page.locator(usernameSelector).first();
  const passwordInput = page.locator(passwordSelector).first();
  const submitButton = page.locator(submitSelector).first();

  await expect(usernameInput).toBeVisible();
  await expect(passwordInput).toBeVisible();
  await expect(submitButton).toBeVisible();

  await usernameInput.fill(credential.username);
  await passwordInput.fill(credential.password);
  await submitButton.click();

  const redirected = await page
    .waitForURL(url => !url.pathname.startsWith(LOGIN_PATH), { timeout: 8000 })
    .then(() => true)
    .catch(() => false);

  if (redirected) {
    return true;
  }

  const currentPath = new URL(page.url()).pathname;
  return !currentPath.startsWith(LOGIN_PATH);
};

export const loginWithCredentialRetry = async (
  page: Page,
  credential: Credentials,
  attempts: number = 2
): Promise<boolean> => {
  let lastError: unknown = null;

  for (let index = 0; index < attempts; index += 1) {
    try {
      return await loginWithCredential(page, credential);
    } catch (error) {
      lastError = error;
      if (index + 1 >= attempts) {
        throw error;
      }
      await page.waitForTimeout(300);
    }
  }

  if (lastError instanceof Error) {
    throw lastError;
  }
  return false;
};

export const resolveCsrfToken = async (page: Page): Promise<string | null> =>
  await page.evaluate(() => {
    const csrfCookie = document.cookie
      .split('; ')
      .find(item => item.startsWith('csrf_token='));
    if (csrfCookie == null || csrfCookie === '') {
      return null;
    }
    return decodeURIComponent(csrfCookie.split('=').slice(1).join('='));
  });

export const resolveCsrfHeaders = async (page: Page): Promise<Record<string, string>> => {
  const csrfToken = await resolveCsrfToken(page);
  if (csrfToken == null || csrfToken === '') {
    return {};
  }

  return { 'X-CSRF-Token': csrfToken };
};

export const loginAsAdmin = async (page: Page): Promise<Credentials> => {
  const credentialCandidates = resolveAdminCredentialCandidates();

  for (const credential of credentialCandidates) {
    const success = await loginWithCredentialRetry(page, credential, 2);
    if (success) {
      return credential;
    }
    await clearAuthState(page);
  }

  throw new Error(
    '无法使用 E2E 管理员凭证登录。请设置 E2E_ADMIN_USERNAME / E2E_ADMIN_PASSWORD。'
  );
};

export const ensureAuthenticated = async (page: Page): Promise<Credentials> => {
  await navigateWithRetry(page, '/dashboard');
  await page
    .waitForURL(
      url => url.pathname.startsWith('/dashboard') || url.pathname.startsWith(LOGIN_PATH),
      { timeout: 5_000 }
    )
    .catch(() => undefined);

  const currentPath = new URL(page.url()).pathname;
  if (currentPath.startsWith(LOGIN_PATH)) {
    return loginAsAdmin(page);
  }

  const authStatus = await page.evaluate(async () => {
    try {
      const response = await fetch('/api/v1/auth/me', { credentials: 'include' });
      return response.status;
    } catch {
      return 0;
    }
  });

  if (authStatus !== 200) {
    return loginAsAdmin(page);
  }

  return { username: 'authenticated-session', password: 'n/a' };
};

export const clearAuthState = async (page: Page): Promise<void> => {
  await page.context().clearCookies();
  await navigateWithRetry(page, LOGIN_PATH);
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
};
