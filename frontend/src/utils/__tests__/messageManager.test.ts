import type { MessageInstance } from 'antd/es/message/interface';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const runtimeEnvState = vi.hoisted(() => ({
  isDevelopment: true,
}));

const antdMessageMock = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
  loading: vi.fn(),
  destroy: vi.fn(),
}));

vi.mock('antd', () => ({
  message: antdMessageMock,
}));

vi.mock('@/utils/runtimeEnv', () => ({
  isDevelopmentMode: () => runtimeEnvState.isDevelopment,
}));

const createMessageApi = (): MessageInstance => {
  return {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    loading: vi.fn(),
    destroy: vi.fn(),
    open: vi.fn(),
    config: vi.fn(),
  } as unknown as MessageInstance;
};

const importMessageManager = async () => {
  vi.resetModules();
  const module = await import('../messageManager');
  return module.MessageManager;
};

describe('MessageManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runtimeEnvState.isDevelopment = true;
  });

  it('uses static fallback and logs error in development when uninitialized', async () => {
    const MessageManager = await importMessageManager();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    MessageManager.success('保存成功');
    MessageManager.error('保存失败');
    MessageManager.warning('请检查输入');
    MessageManager.info('系统提示');
    MessageManager.loading('处理中');

    expect(antdMessageMock.success).toHaveBeenCalledWith('保存成功', 3);
    expect(antdMessageMock.error).toHaveBeenCalledWith('保存失败', 4);
    expect(antdMessageMock.warning).toHaveBeenCalledWith('请检查输入', 3);
    expect(antdMessageMock.info).toHaveBeenCalledWith('系统提示', 3);
    expect(antdMessageMock.loading).toHaveBeenCalledWith('处理中', 0);
    expect(consoleSpy).toHaveBeenCalledTimes(5);
  });

  it('does not log initialization error in non-development mode', async () => {
    const MessageManager = await importMessageManager();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    runtimeEnvState.isDevelopment = false;

    MessageManager.error('生产环境错误');

    expect(antdMessageMock.error).toHaveBeenCalledWith('生产环境错误', 4);
    expect(consoleSpy).not.toHaveBeenCalled();
  });

  it('uses injected message instance after init', async () => {
    const MessageManager = await importMessageManager();
    const messageApi = createMessageApi();

    MessageManager.init(messageApi);

    MessageManager.success('操作成功', 6);
    MessageManager.error('操作失败');
    MessageManager.warning('警告');
    MessageManager.info('提示');
    MessageManager.loading('加载中');

    expect(messageApi.success).toHaveBeenCalledWith(
      expect.objectContaining({
        content: '操作成功',
        duration: 6,
        key: expect.stringMatching(/^success-/),
      })
    );
    expect(messageApi.error).toHaveBeenCalledWith(
      expect.objectContaining({
        content: '操作失败',
        duration: 4,
        key: expect.stringMatching(/^error-/),
      })
    );
    expect(messageApi.warning).toHaveBeenCalledWith(
      expect.objectContaining({
        content: '警告',
        duration: 3,
        key: expect.stringMatching(/^warning-/),
      })
    );
    expect(messageApi.info).toHaveBeenCalledWith(
      expect.objectContaining({
        content: '提示',
        duration: 3,
        key: expect.stringMatching(/^info-/),
      })
    );
    expect(messageApi.loading).toHaveBeenCalledWith(
      expect.objectContaining({
        content: '加载中',
        duration: 0,
        key: expect.stringMatching(/^loading-/),
      })
    );

    expect(antdMessageMock.success).not.toHaveBeenCalled();
    expect(antdMessageMock.error).not.toHaveBeenCalled();
    expect(antdMessageMock.warning).not.toHaveBeenCalled();
    expect(antdMessageMock.info).not.toHaveBeenCalled();
    expect(antdMessageMock.loading).not.toHaveBeenCalled();
  });

  it('supports destroy with and without key for both fallback and initialized mode', async () => {
    const fallbackManager = await importMessageManager();
    fallbackManager.destroy('task-key');
    fallbackManager.destroy();
    expect(antdMessageMock.destroy).toHaveBeenNthCalledWith(1, 'task-key');
    expect(antdMessageMock.destroy).toHaveBeenNthCalledWith(2);

    const initializedManager = await importMessageManager();
    const messageApi = createMessageApi();
    initializedManager.init(messageApi);

    initializedManager.destroy('notice-key');
    initializedManager.destroy();

    expect(messageApi.destroy).toHaveBeenNthCalledWith(1, 'notice-key');
    expect(messageApi.destroy).toHaveBeenNthCalledWith(2);
  });
});
