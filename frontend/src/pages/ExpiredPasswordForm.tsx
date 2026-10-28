import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { AuthService } from '@/services/authService';
import styles from './LoginPage.module.css';

interface Values {
  username: string;
  current_password: string;
  new_password: string;
  confirmation: string;
}

export default function ExpiredPasswordForm({
  identifier,
  onComplete,
  onCancel,
}: {
  identifier: string;
  onComplete: () => void;
  onCancel: () => void;
}): React.ReactElement {
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    defaultValues: {
      username: identifier,
      current_password: '',
      new_password: '',
      confirmation: '',
    },
  });
  const [failure, setFailure] = useState<string | null>(null);
  const submit = handleSubmit(async values => {
    setFailure(null);
    try {
      await AuthService.changeExpiredPassword({
        username: values.username.trim(),
        current_password: values.current_password,
        new_password: values.new_password,
      });
      onComplete();
    } catch (error) {
      setFailure(error instanceof Error ? error.message : '修改失败，请重试');
    }
  });
  return (
    <form className={styles['login-form']} onSubmit={event => void submit(event)} noValidate>
      <h2 className={styles['login-title']}>修改过期密码</h2>
      <p>验证当前密码后设置新密码，再重新登录。新密码不能与当前或近期使用的密码相同。</p>
      {(
        [
          ['username', '用户名 / 手机号', 'text', 'username'],
          ['current_password', '当前密码', 'password', 'current-password'],
          ['new_password', '新密码', 'password', 'new-password'],
          ['confirmation', '确认新密码', 'password', 'new-password'],
        ] as const
      ).map(([name, label, type, autoComplete]) => (
        <div className={styles['field-group']} key={name}>
          <label className={styles['field-label']} htmlFor={`expired-${name}`}>
            {label}
          </label>
          <div className={styles['input-shell']}>
            <input
              id={`expired-${name}`}
              type={type}
              autoComplete={autoComplete}
              className={styles['input-control']}
              aria-invalid={errors[name] != null}
              aria-describedby={errors[name] != null ? `expired-error-${name}` : undefined}
              {...register(name, {
                required: '请填写此项',
                validate: value => {
                  if (
                    name === 'new_password' &&
                    (value.length < 8 ||
                      !/[A-Z]/.test(value) ||
                      !/[a-z]/.test(value) ||
                      !/[0-9]/.test(value) ||
                      !/[!@#$%^&*()_+=[\]{}|;:,.<>?-]/.test(value))
                  )
                    return '至少8个字符，包含大写字母、小写字母、数字和特殊字符';
                  if (name === 'confirmation' && value !== getValues('new_password'))
                    return '两次输入的新密码不一致';
                  if (name === 'username' && value.trim() === '') return '请输入用户名或手机号';
                  return true;
                },
              })}
            />
          </div>
          {errors[name] != null ? (
            <p id={`expired-error-${name}`} className={styles['field-error']}>
              {errors[name]?.message}
            </p>
          ) : null}
        </div>
      ))}
      {failure != null ? (
        <p role="alert" className={styles['field-error']}>
          {failure}
        </p>
      ) : null}
      <button className={styles['login-button']} type="submit" disabled={isSubmitting}>
        {isSubmitting ? '修改中…' : '修改密码并返回登录'}
      </button>
      <button type="button" onClick={onCancel} disabled={isSubmitting}>
        返回登录
      </button>
    </form>
  );
}
