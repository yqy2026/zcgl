import { useState, useEffect } from 'react';
import { MessageManager } from '@/utils/messageManager';
import { createLogger } from '@/utils/logger';

const logger = createLogger('useFullscreen');

export const useFullscreen = () => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        // 进入全屏
        await document.documentElement.requestFullscreen();
        setIsFullscreen(true);
        MessageManager.success('已进入全屏模式');
      } else {
        // 退出全屏
        await document.exitFullscreen();
        setIsFullscreen(false);
        MessageManager.success('已退出全屏模式');
      }
    } catch (error) {
      logger.error('全屏切换失败:', error as Error);
      MessageManager.error('全屏切换失败，请检查浏览器权限设置');
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  return { isFullscreen, toggleFullscreen };
};
