import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import ErrorPage from '../ErrorPage';

const navigateMock = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigateMock,
}));

describe('ErrorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders default 404 content and suggestions', () => {
    render(<ErrorPage />);

    expect(screen.getByText('页面不存在')).toBeInTheDocument();
    expect(screen.getByText('可能的原因：')).toBeInTheDocument();
    expect(screen.getByText('网址输入错误')).toBeInTheDocument();
  });

  it('hides back/home buttons when disabled', () => {
    render(<ErrorPage showBackButton={false} showHomeButton={false} />);

    expect(screen.queryByRole('button', { name: /返回上页/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /返回首页/ })).not.toBeInTheDocument();
  });

  it('shows reload action for network error', () => {
    render(<ErrorPage type="network" />);

    expect(screen.getByRole('button', { name: /重新加载/ })).toBeInTheDocument();
  });

  it('triggers navigate for back/home actions by default', () => {
    render(<ErrorPage />);

    fireEvent.click(screen.getByRole('button', { name: /返回上页/ }));
    fireEvent.click(screen.getByRole('button', { name: /返回首页/ }));

    expect(navigateMock).toHaveBeenCalledWith(-1);
    expect(navigateMock).toHaveBeenCalledWith('/');
  });

  it('uses callbacks when provided', () => {
    const onBack = vi.fn();
    const onHome = vi.fn();
    const onReload = vi.fn();

    render(
      <ErrorPage
        type="500"
        onBack={onBack}
        onHome={onHome}
        onReload={onReload}
        showReloadButton={true}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /返回上页/ }));
    fireEvent.click(screen.getByRole('button', { name: /返回首页/ }));
    fireEvent.click(screen.getByRole('button', { name: /重新加载/ }));

    expect(onBack).toHaveBeenCalledTimes(1);
    expect(onHome).toHaveBeenCalledTimes(1);
    expect(onReload).toHaveBeenCalledTimes(1);
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
