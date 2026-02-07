import { useAuth as useAuthContext } from '@/contexts/AuthContext';

/**
 * 认证Hook（兼容层）
 *
 * 说明：
 * - 统一复用 AuthContext，避免出现第二套本地认证状态源。
 * - 历史调用方仍可从 '@/hooks/useAuth' 导入，不影响现有代码。
 */
export const useAuth = () => {
  return useAuthContext();
};
