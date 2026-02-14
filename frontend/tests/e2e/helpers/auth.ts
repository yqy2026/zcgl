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

const usernameSelector = 'input#login_username, input[name="username"]';
const passwordSelector = 'input#login_password, input[name="password"]';
const submitSelector = 'button[type="submit"]';

export const loginWithCredential = async (page: Page, credential: Credentials): Promise<boolean> => {
  await page.goto(LOGIN_PATH);

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

export const loginAsAdmin = async (page: Page): Promise<Credentials> => {
  const credentialCandidates = resolveAdminCredentialCandidates();

  for (const credential of credentialCandidates) {
    const success = await loginWithCredential(page, credential);
    if (success) {
      return credential;
    }
  }

  throw new Error(
    '无法使用 E2E 管理员凭证登录。请设置 E2E_ADMIN_USERNAME / E2E_ADMIN_PASSWORD。'
  );
};

export const ensureAuthenticated = async (page: Page): Promise<Credentials> => {
  await page.goto('/dashboard');
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
  await page.goto(LOGIN_PATH);
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
};
