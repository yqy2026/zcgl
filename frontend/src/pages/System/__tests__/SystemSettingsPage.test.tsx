import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import SystemSettingsPage from '../SystemSettingsPage';
import { systemService } from '@/services/systemService';

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

    warnSpy.mockRestore();
    errorSpy.mockRestore();
  });
});
