import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import type { LoginFormData } from '@/types/auth';
import styles from './LoginPage.module.css';

type FieldErrors = {
  identifier: string | null;
  password: string | null;
};

const BRAND_FEATURES = [
  {
    icon: 'domain',
    title: '资产全景视图',
    description: '实时掌握资产分布与状态',
  },
  {
    icon: 'analytics',
    title: '智能决策分析',
    description: '多维数据驱动运营优化',
  },
  {
    icon: 'verified_user',
    title: '安全合规管控',
    description: '全流程风控体系保障',
  },
];

type MaterialSymbolProps = {
  name: string;
  className?: string;
};

const MaterialSymbol: React.FC<MaterialSymbolProps> = ({ name, className }) => {
  const combinedClassName = [styles['material-symbol'], className ?? ''].join(' ').trim();
  return (
    <span className={combinedClassName} aria-hidden="true">
      {name}
    </span>
  );
};

const validateForm = (values: LoginFormData): FieldErrors => {
  const identifier = values.identifier.trim();
  const password = values.password;

  let identifierError: string | null = null;
  let passwordError: string | null = null;

  if (identifier === '') {
    identifierError = '请输入用户名或手机号';
  } else if (identifier.length > 50) {
    identifierError = '用户名或手机号最多50个字符';
  }

  if (password.trim() === '') {
    passwordError = '请输入密码';
  } else if (password.length < 6) {
    passwordError = '密码至少6个字符';
  }

  return {
    identifier: identifierError,
    password: passwordError,
  };
};

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading, error } = useAuth();
  const [formData, setFormData] = useState<LoginFormData>({
    identifier: '',
    password: '',
    remember: false,
  });
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [isQrMode, setIsQrMode] = useState<boolean>(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({
    identifier: null,
    password: null,
  });

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = validateForm(formData);
    setFieldErrors(nextErrors);

    const hasIdentifierError = nextErrors.identifier != null && nextErrors.identifier !== '';
    const hasPasswordError = nextErrors.password != null && nextErrors.password !== '';
    if (hasIdentifierError || hasPasswordError) {
      return;
    }

    try {
      await login({
        identifier: formData.identifier,
        password: formData.password,
        remember: formData.remember,
      });

      // 登录成功，跳转到目标页面或默认工作台
      const state = location.state as { from?: { pathname?: string } } | null;
      const from = state?.from?.pathname ?? '/dashboard';
      navigate(from, { replace: true });
    } catch {
      // 错误处理已在useAuth中完成，这里不需要额外处理
    }
  };

  const handleIdentifierChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, identifier: e.target.value }));
    setFieldErrors(prev => ({ ...prev, identifier: null }));
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, password: e.target.value }));
    setFieldErrors(prev => ({ ...prev, password: null }));
  };

  const handleRememberChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, remember: event.target.checked }));
  };

  const togglePasswordVisibility = () => {
    setShowPassword(prev => !prev);
  };

  const toggleMode = () => {
    setIsQrMode(prev => !prev);
  };

  const hasError = error != null && error !== '';
  const hasIdentifierFieldError = fieldErrors.identifier != null && fieldErrors.identifier !== '';
  const hasPasswordFieldError = fieldErrors.password != null && fieldErrors.password !== '';
  const currentModeIcon = isQrMode ? 'desktop_windows' : 'qr_code_2';

  return (
    <div className={styles['login-page']}>
      <div className={styles['page-overlay']} />
      <div className={styles['page-accent']} />

      <main className={styles['login-main']}>
        <section className={styles['brand-panel']} aria-label="系统介绍">
          <div className={styles['brand-heading']}>
            <p className={styles['brand-kicker']}>
              Real Estate Asset Management & Operations System
            </p>
            <h1 className={styles['brand-title']}>
              土地物业
              <br />
              资产运营管理系统
            </h1>
          </div>

          <p className={styles['brand-description']}>
            构建数智化资产管理新生态，实现全生命周期价值最大化。
          </p>

          <ul className={styles['feature-list']}>
            {BRAND_FEATURES.map(itemData => (
              <li key={itemData.title} className={styles['brand-list-item']}>
                <div className={styles['feature-icon']}>
                  <MaterialSymbol name={itemData.icon} />
                </div>
                <div className={styles['feature-content']}>
                  <span className={styles['feature-title']}>{itemData.title}</span>
                  <span className={styles['feature-desc']}>{itemData.description}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className={styles['card-shell']}>
          <div className={styles['login-card']}>
            <button
              type="button"
              className={styles['mode-toggle-btn']}
              onClick={toggleMode}
              aria-label={isQrMode ? '切换到账号登录' : '切换到二维码登录'}
            >
              <span className={styles['mode-corner']} />
              <span className={styles['mode-icon']}>
                <MaterialSymbol name={currentModeIcon} />
              </span>
            </button>

            <div className={styles['view-stack']}>
              <div
                className={[
                  styles['login-view'],
                  isQrMode ? styles['view-hidden-left'] : styles['view-visible'],
                ].join(' ')}
              >
                <header className={styles['login-header']}>
                  <h2 className={styles['login-title']}>欢迎回来</h2>
                  <p className={styles['login-subtitle']}>请输入您的账号密码以继续</p>
                </header>

                <form className={styles['login-form']} onSubmit={handleSubmit} noValidate>
                  <div className={styles['field-list']}>
                    <div className={styles['field-group']}>
                      <label className={styles['field-label']} htmlFor="identifier">
                        用户名 / 手机号
                      </label>
                      <div
                        className={[
                          styles['input-shell'],
                          hasIdentifierFieldError ? styles['input-shell-error'] : '',
                        ].join(' ')}
                      >
                        <span className={styles['input-icon']}>
                          <MaterialSymbol name="person" />
                        </span>
                        <input
                          id="identifier"
                          name="identifier"
                          type="text"
                          className={styles['input-control']}
                          placeholder="请输入用户名或手机号"
                          value={formData.identifier}
                          onChange={handleIdentifierChange}
                          autoComplete="username"
                        />
                      </div>
                      {hasIdentifierFieldError && (
                        <p className={styles['field-error']}>{fieldErrors.identifier}</p>
                      )}
                    </div>

                    <div className={styles['field-group']}>
                      <label className={styles['field-label']} htmlFor="password">
                        密码
                      </label>
                      <div
                        className={[
                          styles['input-shell'],
                          hasPasswordFieldError ? styles['input-shell-error'] : '',
                        ].join(' ')}
                      >
                        <span className={styles['input-icon']}>
                          <MaterialSymbol name="lock" />
                        </span>
                        <input
                          id="password"
                          name="password"
                          type={showPassword ? 'text' : 'password'}
                          className={styles['input-control']}
                          placeholder="••••••••"
                          value={formData.password}
                          onChange={handlePasswordChange}
                          autoComplete="current-password"
                        />
                        <button
                          type="button"
                          className={styles['password-visibility']}
                          onClick={togglePasswordVisibility}
                          aria-label={showPassword ? '隐藏密码' : '显示密码'}
                        >
                          <MaterialSymbol name={showPassword ? 'visibility' : 'visibility_off'} />
                        </button>
                      </div>
                      {hasPasswordFieldError && (
                        <p className={styles['field-error']}>{fieldErrors.password}</p>
                      )}
                    </div>
                  </div>

                  <div className={styles['login-meta']}>
                    <label className={styles['remember-label']} htmlFor="remember-me">
                      <input
                        id="remember-me"
                        name="remember-me"
                        type="checkbox"
                        checked={formData.remember}
                        onChange={handleRememberChange}
                        className={styles['remember-checkbox']}
                      />
                      <span>记住登录状态</span>
                    </label>
                    <a
                      href="#"
                      className={styles['forgot-link']}
                      onClick={event => {
                        event.preventDefault();
                      }}
                    >
                      忘记密码?
                    </a>
                  </div>

                  {hasError && (
                    <div className={styles['login-error']} role="alert">
                      <p className={styles['login-error-title']}>登录失败</p>
                      <p className={styles['login-error-message']}>{error}</p>
                    </div>
                  )}

                  <button
                    type="submit"
                    className={styles['login-button']}
                    disabled={loading === true}
                  >
                    {loading === true ? '登录中...' : '立即登录'}
                  </button>
                </form>

                <footer className={styles['login-footer']}>
                  <a
                    href="#"
                    className={styles['support-link']}
                    onClick={event => {
                      event.preventDefault();
                    }}
                  >
                    <MaterialSymbol name="support_agent" />
                    <span>遇到问题？联系 IT 管理员</span>
                  </a>
                </footer>
              </div>

              <div
                className={[
                  styles['qr-view'],
                  isQrMode ? styles['view-visible'] : styles['view-hidden-right'],
                ].join(' ')}
              >
                <div className={styles['qr-header']}>
                  <h2 className={styles['qr-title']}>企业微信登录</h2>
                  <p className={styles['qr-subtitle']}>请打开企业微信扫一扫登录</p>
                </div>

                <div className={styles['qr-code-shell']}>
                  <div className={styles['qr-code-box']}>
                    <svg
                      className={styles['qr-code-svg']}
                      fill="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path d="M3 3h6v6H3V3zm2 2v2h2V5H5zm8-2h6v6h-6V3zm2 2v2h2V5h-2zM3 13h6v6H3v-6zm2 2v2h2v-2H5zm13-2h3v2h-3v-2zm-3 0h2v3h-2v-3zm-3 3h3v5h-3v-5zm3 3h3v2h-3v-2zm-3-3h-2v5h3v-2h-1v-3zm-2-3h2v2h-2v-2zm-3 3h2v2h-2v-2zm0 3h-2v2h2v-2z" />
                      <rect x="15" y="15" width="2" height="2" />
                      <rect x="18" y="13" width="2" height="2" />
                    </svg>
                    <div className={styles['scan-line']} />
                  </div>
                </div>

                <div className={styles['qr-footer']}>
                  <p className={styles['qr-tip']}>
                    请使用 <span>企业微信 APP</span> 扫码
                  </p>
                  <button type="button" className={styles['back-login-btn']} onClick={toggleMode}>
                    <MaterialSymbol name="arrow_back" />
                    <span>返回账号登录</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default LoginPage;
