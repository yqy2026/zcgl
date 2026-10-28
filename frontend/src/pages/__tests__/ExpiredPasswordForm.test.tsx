import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import ExpiredPasswordForm from '../ExpiredPasswordForm';
import { AuthService } from '@/services/authService';

vi.mock('@/services/authService', () => ({ AuthService: { changeExpiredPassword: vi.fn() } }));

it('requires matching strong passwords and returns to login only after success', async () => {
  vi.mocked(AuthService.changeExpiredPassword).mockResolvedValue(undefined);
  const done = vi.fn();
  render(<ExpiredPasswordForm identifier="test-user" onComplete={done} onCancel={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('当前密码'), { target: { value: 'old-password' } });
  fireEvent.change(screen.getByLabelText('新密码'), { target: { value: 'weak' } });
  fireEvent.click(screen.getByRole('button', { name: '修改密码并返回登录' }));
  expect(await screen.findByText(/至少8个字符/)).toBeVisible();
  expect(AuthService.changeExpiredPassword).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('新密码'), { target: { value: 'Example2026!' } });
  fireEvent.change(screen.getByLabelText('确认新密码'), { target: { value: 'Example2026!' } });
  fireEvent.click(screen.getByRole('button', { name: '修改密码并返回登录' }));
  await waitFor(() => expect(done).toHaveBeenCalledOnce());
  expect(AuthService.changeExpiredPassword).toHaveBeenCalledWith({
    username: 'test-user',
    current_password: 'old-password',
    new_password: 'Example2026!',
  });
});

it('keeps the form open when current-password verification fails', async () => {
  vi.mocked(AuthService.changeExpiredPassword).mockRejectedValue(new Error('账号或当前密码不正确'));
  const done = vi.fn();
  render(<ExpiredPasswordForm identifier="test-user" onComplete={done} onCancel={vi.fn()} />);
  for (const [label, value] of [
    ['当前密码', 'wrong-password'],
    ['新密码', 'Example2026!'],
    ['确认新密码', 'Example2026!'],
  ]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole('button', { name: '修改密码并返回登录' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('账号或当前密码不正确');
  expect(done).not.toHaveBeenCalled();
});
