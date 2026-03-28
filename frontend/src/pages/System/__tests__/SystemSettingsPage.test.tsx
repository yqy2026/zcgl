import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import SystemSettingsPage from '../SystemSettingsPage';
import { systemService } from '@/services/systemService';

const formatStderrWrites = (calls: unknown[][]) => calls.map(call => String(call[0] ?? '')).join(' ');

vi.mock('@/services/systemService', () => ({
  systemService: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
    getSystemInfo: vi.fn(),
    backupSystem: vi.fn(),
    restoreSystem: vi.fn(),
  },
}));

vi.mock('@/utils/messageManager', () => ({
  MessageManager: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  }),
}));

vi.mock('../SystemSettingsPage.module.css', () => ({
  default: new Proxy(
    {},
    {
      get: (_target, property) => String(property),
    }
  ),
}));

vi.mock('@/components/Common/PageContainer', () => ({
  default: ({
    title,
    children,
  }: {
    title?: React.ReactNode;
    children?: React.ReactNode;
  }) => (
    <div data-testid="page-container">
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');

  const Card = ({
    title,
    children,
  }: {
    title?: React.ReactNode;
    children?: React.ReactNode;
  }) => (
    <div data-testid="card">
      {title != null && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  );

  const Alert = ({
    title,
    description,
  }: {
    title?: React.ReactNode;
    description?: React.ReactNode;
  }) => (
    <div data-testid="alert">
      {title}
      {description}
    </div>
  );

  const Space = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  const Tabs = ({ items }: { items?: Array<{ label?: React.ReactNode; children?: React.ReactNode }> }) => (
    <div data-testid="tabs">
      {(items ?? []).map((item, index) => (
        <div key={index}>
          <div>{item.label}</div>
          <div>{item.children}</div>
        </div>
      ))}
    </div>
  );
  const Form = ({ children }: { children?: React.ReactNode }) => <form>{children}</form>;
  Form.Item = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  Form.useForm = () => [{ setFieldsValue: vi.fn() }];
  const Input = ({ placeholder }: { placeholder?: string }) => <input placeholder={placeholder} readOnly />;
  Input.TextArea = ({ placeholder }: { placeholder?: string }) => (
    <textarea placeholder={placeholder} readOnly />
  );
  const InputNumber = ({ placeholder }: { placeholder?: string }) => (
    <input placeholder={placeholder} readOnly />
  );
  const Switch = () => <input type="checkbox" readOnly />;
  const Button = ({
    children,
    disabled,
  }: {
    children?: React.ReactNode;
    disabled?: boolean;
  }) => <button disabled={disabled}>{children}</button>;
  const Divider = () => <hr />;
  const Tag = ({ children }: { children?: React.ReactNode }) => <span>{children}</span>;
  const Typography = {
    Title: ({ children }: { children?: React.ReactNode }) => <span>{children}</span>,
    Text: ({ children }: { children?: React.ReactNode }) => <span>{children}</span>,
  };
  const ConfigProvider = ({ children }: { children?: React.ReactNode }) => <>{children}</>;
  const theme = { defaultAlgorithm: {} };

  return {
    ...actual,
    Card,
    Alert,
    Space,
    Tabs,
    Form,
    Input,
    InputNumber,
    Switch,
    Button,
    Divider,
    Tag,
    Typography,
    ConfigProvider,
    theme,
  };
});

const mockSettings = {
  site_name: '测试站点',
  site_description: '测试描述',
  logo_url: '',
  allow_registration: true,
  default_role: 'user',
  session_timeout: 30,
  password_policy: {
    min_length: 8,
    require_uppercase: true,
    require_lowercase: true,
    require_numbers: true,
    require_special_chars: false,
  },
};

const mockSystemInfo = {
  version: '1.0.0',
  build_time: '2026-02-04T00:00:00Z',
  database_status: 'connected',
  api_version: 'v1',
  environment: 'test',
};

describe('SystemSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(systemService.getSettings).mockResolvedValue(mockSettings);
    vi.mocked(systemService.getSystemInfo).mockResolvedValue(mockSystemInfo);
  });

  it('renders without Tabs/Form warnings', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const stderrWriteSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);

    try {
      renderWithProviders(<SystemSettingsPage />);

      await waitFor(() => {
        expect(systemService.getSettings).toHaveBeenCalled();
      });

      expect(screen.getByText('系统设置')).toBeInTheDocument();

      const warnOutput = warnSpy.mock.calls.flat().join(' ');
      const errorOutput = errorSpy.mock.calls.flat().join(' ');

      expect(warnOutput).not.toContain('Tabs.TabPane');
      expect(errorOutput).not.toContain('Tabs.TabPane');
      expect(warnOutput).not.toContain('Form.Item');
      expect(errorOutput).not.toContain('Form.Item');
      expect(formatStderrWrites(stderrWriteSpy.mock.calls)).not.toContain(
        'Could not parse CSS stylesheet'
      );
    } finally {
      stderrWriteSpy.mockRestore();
      warnSpy.mockRestore();
      errorSpy.mockRestore();
    }
  });
});
