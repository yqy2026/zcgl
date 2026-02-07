declare module '@playwright/test' {
  export interface Locator {
    fill(...args: any[]): Promise<void>;
    click(...args: any[]): Promise<void>;
    count(...args: any[]): Promise<number>;
    first(...args: any[]): Locator;
    locator(...args: any[]): Locator;
    isVisible(...args: any[]): Promise<boolean>;
    [key: string]: any;
  }

  export interface Page {
    goto(...args: any[]): Promise<void>;
    fill(...args: any[]): Promise<void>;
    click(...args: any[]): Promise<void>;
    waitForURL(...args: any[]): Promise<void>;
    waitForLoadState(...args: any[]): Promise<void>;
    reload(...args: any[]): Promise<void>;
    url(...args: any[]): string;
    close(...args: any[]): Promise<void>;
    evaluate(...args: any[]): Promise<any>;
    locator(...args: any[]): Locator;
    getByRole(...args: any[]): Locator;
    waitForResponse(
      predicate: (response: { url: () => string; status: () => number }) => boolean | Promise<boolean>
    ): Promise<any>;
    [key: string]: any;
  }

  export interface BrowserContext {
    newPage(...args: any[]): Promise<Page>;
    [key: string]: any;
  }

  export interface PlaywrightTestArgs {
    page: Page;
    context: BrowserContext;
    [key: string]: unknown;
  }

  export type TestBody = (args: PlaywrightTestArgs) => void | Promise<void>;
  export type HookBody = (args: PlaywrightTestArgs) => void | Promise<void>;

  export interface TestType {
    (title: string, body: TestBody): void;
    describe(title: string, body: () => void): void;
    beforeEach(body: HookBody): void;
    afterEach(body: HookBody): void;
    beforeAll(body: HookBody): void;
    afterAll(body: HookBody): void;
  }

  export const test: TestType;
  export const expect: any;
  export const devices: Record<string, Record<string, any>>;
  export function defineConfig<TConfig = unknown>(config: TConfig): TConfig;
}
