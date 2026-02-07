/**
 * Accessibility Utilities
 * Helper functions and components for improving accessibility
 */

/**
 * Generate ARIA labels for icon-only buttons
 * @param action - The action being performed (e.g., 'edit', 'delete', 'save')
 * @param target - Optional target object (e.g., 'asset', 'contract')
 * @returns Complete ARIA label string
 */
export function generateAriaLabel(action: string, target?: string): string {
  const actionMap: Record<string, string> = {
    edit: '编辑',
    delete: '删除',
    save: '保存',
    cancel: '取消',
    confirm: '确认',
    close: '关闭',
    view: '查看',
    add: '添加',
    remove: '移除',
    download: '下载',
    upload: '上传',
    search: '搜索',
    filter: '筛选',
    sort: '排序',
    refresh: '刷新',
    export: '导出',
    import: '导入',
    copy: '复制',
    paste: '粘贴',
    print: '打印',
    share: '分享',
    settings: '设置',
    info: '信息',
    warning: '警告',
    error: '错误',
    success: '成功',
  };

  const actionText = actionMap[action] || action;

  if (target) {
    return `${actionText}${target}`;
  }

  return actionText;
}

/**
 * Generate unique IDs for ARIA attributes
 * @param prefix - Prefix for the ID
 * @returns Unique ID string
 */
export function generateId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Announce a message to screen readers
 * @param message - The message to announce
 * @param priority - 'polite' or 'assertive'
 */
export function announceToScreenReader(
  message: string,
  priority: 'polite' | 'assertive' = 'polite'
): void {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;

  document.body.appendChild(announcement);

  // Remove after announcement
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}

/**
 * Generate accessible props for an icon-only button
 * @param action - The action being performed
 * @param target - Optional target object
 * @returns Object with aria-label and title props
 */
export function getIconButtonProps(
  action: string,
  target?: string
): {
  'aria-label': string;
  title: string;
} {
  const label = generateAriaLabel(action, target);
  return {
    'aria-label': label,
    title: label,
  };
}

/**
 * Generate form field IDs for accessibility
 * @param fieldName - Name of the form field
 * @returns Object with label and description IDs
 */
export function generateFormFieldIds(fieldName: string): {
  labelId: string;
  inputId: string;
  descriptionId: string;
  errorId: string;
} {
  const base = generateId(fieldName);
  return {
    labelId: `${base}-label`,
    inputId: `${base}-input`,
    descriptionId: `${base}-description`,
    errorId: `${base}-error`,
  };
}

/**
 * Check if user prefers reduced motion
 * @returns True if user prefers reduced motion
 */
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Get the appropriate animation duration based on user preferences
 * @param duration - Default duration in ms
 * @returns Adjusted duration (0 if reduced motion is preferred)
 */
export function getAccessibleDuration(duration: number): number {
  return prefersReducedMotion() ? 0 : duration;
}

/**
 * Format a number for screen readers with proper grouping
 * @param num - Number to format
 * @param locale - Locale string (default: zh-CN)
 * @returns Formatted number string
 */
export function formatNumberForScreenReader(num: number, locale: string = 'zh-CN'): string {
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Format a date for screen readers
 * @param date - Date to format
 * @param locale - Locale string (default: zh-CN)
 * @returns Formatted date string
 */
export function formatDateForScreenReader(date: Date, locale: string = 'zh-CN'): string {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date);
}
