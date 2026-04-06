import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import QuickActions from '../QuickActions';

const navigateMock = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

describe('QuickActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('routes the export shortcut to the canonical assets list', () => {
    render(<QuickActions />);

    fireEvent.click(screen.getByText('数据导出'));

    expect(navigateMock).toHaveBeenCalledWith('/assets/list');
  });
});
