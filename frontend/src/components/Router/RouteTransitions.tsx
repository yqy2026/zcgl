/**
 * 路由动画和转场组件
 * 提供流畅的页面切换动画和过渡效果
 */

import React, { useState, useEffect, ReactNode } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ConfigProvider, theme } from 'antd';

// 动画类型
type AnimationType = 'fade' | 'slide' | 'scale' | 'flip' | 'none';

// 网络连接接口
interface NetworkConnection {
  effectiveType: 'slow-2g' | '2g' | '3g' | '4g';
  downlink: number;
  rtt: number;
  saveData: boolean;
}

// 扩展Navigator接口
declare global {
  interface Navigator {
    connection?: NetworkConnection;
    mozConnection?: NetworkConnection;
    webkitConnection?: NetworkConnection;
  }
}

interface RouteTransitionProps {
  children: ReactNode;
  animationType?: 'fade' | 'slide' | 'scale' | 'flip' | 'none';
  duration?: number;
  easing?: string;
  custom?: unknown;
}

interface PageTransitionConfig {
  enter: any;
  exit: any;
  initial: any;
}

class RouteTransitionManager {
  private animationTypes: Map<string, PageTransitionConfig>;
  private defaultDuration: number;
  private reducedMotion: boolean;

  constructor() {
    this.animationTypes = new Map();
    this.defaultDuration = 300;
    this.reducedMotion = this.detectReducedMotion();
    this.initializeAnimations();
  }

  private detectReducedMotion(): boolean {
    // 检测用户是否偏好减少动画
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  }

  private initializeAnimations() {
    this.animationTypes = new Map();

    // 淡入淡出动画
    this.animationTypes.set('fade', {
      initial: {
        opacity: 0,
        scale: 0.98,
      },
      enter: {
        opacity: 1,
        scale: 1,
        transition: {
          duration: this.defaultDuration,
          ease: [0.4, 0, 0.2, 1],
        },
      },
      exit: {
        opacity: 0,
        scale: 1.02,
        transition: {
          duration: this.defaultDuration * 0.5,
          ease: [0.4, 0, 1, 1],
        },
      },
    });

    // 滑动动画
    this.animationTypes.set('slide', {
      initial: {
        x: 300,
        opacity: 0,
      },
      enter: {
        x: 0,
        opacity: 1,
        transition: {
          duration: this.defaultDuration,
          ease: [0.25, 1, 0.5, 1],
          delay: 0.1,
        },
      },
      exit: {
        x: -300,
        opacity: 0,
        transition: {
          duration: this.defaultDuration * 0.75,
          ease: [0.4, 0, 1, 1],
        },
      },
    });

    // 缩放动画
    this.animationTypes.set('scale', {
      initial: {
        scale: 0.8,
        opacity: 0,
      },
      enter: {
        scale: 1,
        opacity: 1,
        transition: {
          duration: this.defaultDuration,
          ease: [0.34, 1.56, 0.64, 1],
          delay: 0.05,
        },
      },
      exit: {
        scale: 0.9,
        opacity: 0,
        transition: {
          duration: this.defaultDuration * 0.6,
          ease: [0.4, 0, 1, 1],
        },
      },
    });

    // 翻转动画
    this.animationTypes.set('flip', {
      initial: {
        rotateY: -90,
        opacity: 0,
      },
      enter: {
        rotateY: 0,
        opacity: 1,
        transition: {
          duration: this.defaultDuration,
          ease: [0.25, 1, 0.5, 1],
        },
      },
      exit: {
        rotateY: 90,
        opacity: 0,
        transition: {
          duration: this.defaultDuration * 0.8,
          ease: [0.4, 0, 1, 1],
        },
      },
    });

    // 无动画
    this.animationTypes.set('none', {
      initial: {},
      enter: {},
      exit: {},
    });
  }

  public getAnimationConfig(type: string): PageTransitionConfig {
    if (this.reducedMotion) {
      return this.animationTypes.get('fade') ?? this.animationTypes.get('none')!;
    }

    return this.animationTypes.get(type) ?? this.animationTypes.get('fade')!;
  }

  public setReducedMotion(reduced: boolean) {
    this.reducedMotion = reduced;
  }

  public setDefaultDuration(duration: number) {
    this.defaultDuration = duration;
  }
}

// 全局转场管理器
const globalTransitionManager = new RouteTransitionManager();

// 路由转场组件
export const RouteTransition: React.FC<RouteTransitionProps> = ({
  children,
  animationType = 'fade',
  duration,
  easing: _easing,
  custom,
}) => {
  const location = useLocation();
  const navigationType = useNavigationType();
  const [_prevLocation, setPrevLocation] = useState(location);

  useEffect(() => {
    setPrevLocation(location);
  }, [location]);

  // 根据导航类型选择动画
  const getAnimationType = () => {
    if (custom != null) return 'fade';

    switch (navigationType) {
      case 'POP':
        return 'slide'; // 返回时使用滑动
      case 'PUSH':
        return animationType; // 前进时使用指定动画
      case 'REPLACE':
        return 'fade'; // 替换时使用淡入淡出
      default:
        return animationType;
    }
  };

  const animationConfig = globalTransitionManager.getAnimationConfig(getAnimationType());

  // 应用自定义持续时间
  if (duration != null) {
    animationConfig.enter.transition = {
      ...animationConfig.enter.transition,
      duration,
    };
    animationConfig.exit.transition = {
      ...animationConfig.exit.transition,
      duration,
    };
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={animationConfig.initial}
        animate={animationConfig.enter}
        exit={animationConfig.exit}
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          top: 0,
          left: 0,
        }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
};

// 页面转场容器
export const PageTransitionContainer: React.FC<{
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}> = ({ children, className, style }) => {
  return (
    <div
      className={className}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        ...style,
      }}
    >
      {children}
    </div>
  );
};

// 布局转场组件
export const LayoutTransition: React.FC<{
  children: ReactNode;
  animation?: 'fade' | 'slide' | 'scale';
  duration?: number;
}> = ({ children, animation = 'fade', duration = 200 }) => {
  const config = globalTransitionManager.getAnimationConfig(animation);

  return (
    <motion.div
      initial={config.initial}
      animate={config.enter}
      transition={{
        duration,
        ease: 'easeInOut',
      }}
    >
      {children}
    </motion.div>
  );
};

// 元素级转场Hook
export const useElementTransition = (isVisible: boolean) => {
  const [shouldRender, setShouldRender] = useState(isVisible);

  useEffect(() => {
    if (isVisible !== undefined && isVisible !== null) {
      setShouldRender(true);
    } else {
      // 延迟卸载以允许退出动画完成
      const timer = setTimeout(() => {
        setShouldRender(false);
      }, 300);

      return () => clearTimeout(timer);
    }
  }, [isVisible]);

  const variants = {
    hidden: {
      opacity: 0,
      y: 20,
    },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 200,
        ease: 'easeOut',
      },
    },
  };

  return {
    shouldRender,
    variants,
    initial: 'hidden',
    animate: shouldRender ? 'visible' : 'hidden',
    exit: 'hidden',
  };
};

// 路由特定动画Hook
export const useRouteAnimation = (route: string) => {
  const [animationType, setAnimationType] = useState<'fade' | 'slide' | 'scale' | 'flip'>('fade');

  useEffect(() => {
    // 根据路由类型选择合适的动画
    const routeAnimations: Record<string, typeof animationType> = {
      '/dashboard': 'scale',
      '/assets': 'slide',
      '/rental': 'fade',
      '/system': 'flip',
    };

    const defaultAnimation = Object.keys(routeAnimations).find(r => route.startsWith(r));
    setAnimationType(defaultAnimation != null ? routeAnimations[defaultAnimation] : 'fade');
  }, [route]);

  return { animationType };
};

// 智能转场Hook
export const useSmartTransition = () => {
  const location = useLocation();
  const navigationType = useNavigationType();
  const [preferredAnimation, setPreferredAnimation] = useState<
    'fade' | 'slide' | 'scale' | 'flip' | 'none'
  >('fade');

  useEffect(() => {
    // 根据用户行为学习偏好
    const userPreferences = localStorage.getItem('preferred_route_animation');
    if (
      userPreferences != null &&
      ['fade', 'slide', 'scale', 'flip', 'none'].includes(userPreferences)
    ) {
      setPreferredAnimation(userPreferences as AnimationType);
    }
  }, []);

  const getOptimalAnimation = () => {
    // 根据导航类型和路径深度选择最优动画
    const pathDepth = location.pathname.split('/').length;

    if (navigationType === 'POP') {
      return 'slide'; // 返回导航适合滑动动画
    }

    if (pathDepth > 3) {
      return 'fade'; // 深层路径适合简单动画
    }

    return preferredAnimation;
  };

  const setAnimationPreference = (animation: typeof preferredAnimation) => {
    setPreferredAnimation(animation);
    localStorage.setItem('preferred_route_animation', animation);
  };

  return {
    animationType: getOptimalAnimation(),
    setAnimationPreference,
  };
};

// 性能优化的转场组件
export const OptimizedTransition: React.FC<{
  children: ReactNode;
  animationType?: string;
  disabled?: boolean;
}> = ({ children, animationType = 'fade', disabled = false }) => {
  const [isReduced, setIsReduced] = useState(false);

  useEffect(() => {
    // 监听性能变化
    const handlePerformanceChange = () => {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      setIsReduced(mediaQuery.matches);
    };

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    mediaQuery.addEventListener('change', handlePerformanceChange);
    handlePerformanceChange();

    return () => {
      mediaQuery.removeEventListener('change', handlePerformanceChange);
    };
  }, []);

  if (disabled || isReduced) {
    return <>{children}</>;
  }

  const config = globalTransitionManager.getAnimationConfig(animationType);

  return (
    <motion.div
      initial={config.initial}
      animate={config.enter}
      exit={config.exit}
      style={{
        willChange: 'opacity, transform', // 提示浏览器优化
      }}
    >
      {children}
    </motion.div>
  );
};

// 转场配置提供者
interface TransitionConfigContextType {
  animationsEnabled: boolean;
  reducedMotion: boolean;
  defaultDuration: number;
  setAnimationsEnabled: (enabled: boolean) => void;
  setReducedMotion: (reduced: boolean) => void;
  setDefaultDuration: (duration: number) => void;
}

const TransitionConfigContext = React.createContext<TransitionConfigContextType | null>(null);

export const TransitionConfigProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [animationsEnabled, setAnimationsEnabled] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [defaultDuration, setDefaultDuration] = useState(300);

  useEffect(() => {
    // 检测系统偏好
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setReducedMotion(prefersReducedMotion);

    // 检测设备性能
    const checkPerformance = () => {
      const connection =
        navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (connection !== undefined && connection !== null && connection.effectiveType) {
        // 在慢速网络上禁用动画
        const isSlowNetwork = ['slow-2g', '2g', '3g'].includes(connection.effectiveType);
        setAnimationsEnabled(!isSlowNetwork);
      }
    };

    checkPerformance();
  }, []);

  const contextValue: TransitionConfigContextType = {
    animationsEnabled,
    reducedMotion,
    defaultDuration,
    setAnimationsEnabled,
    setReducedMotion,
    setDefaultDuration,
  };

  return (
    <TransitionConfigContext.Provider value={contextValue}>
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            motionDurationFast: `${defaultDuration * 0.5}ms`,
            motionDurationMid: `${defaultDuration}ms`,
            motionDurationSlow: `${defaultDuration * 1.5}ms`,
          },
        }}
      >
        {children}
      </ConfigProvider>
    </TransitionConfigContext.Provider>
  );
};

// 转场配置Hook
export const useTransitionConfig = () => {
  const context = React.useContext(TransitionConfigContext);
  if (!context) {
    throw new Error('useTransitionConfig must be used within TransitionConfigProvider');
  }
  return context;
};

// 预设转场动画
export const presetAnimations = {
  // 淡入淡出
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
    transition: { duration: 0.3 },
  },

  // 从右滑入
  slideInRight: {
    initial: { x: 100, opacity: 0 },
    animate: { x: 0, opacity: 1 },
    exit: { x: -100, opacity: 0 },
    transition: { duration: 0.3, ease: 'easeInOut' },
  },

  // 缩放进入
  scaleIn: {
    initial: { scale: 0.8, opacity: 0 },
    animate: { scale: 1, opacity: 1 },
    exit: { scale: 1.1, opacity: 0 },
    transition: { duration: 0.25, ease: 'easeOut' },
  },

  // 弹跳进入
  bounceIn: {
    initial: { scale: 0.3, opacity: 0 },
    animate: {
      scale: 1,
      opacity: 1,
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 20,
      },
    },
    exit: { scale: 0.3, opacity: 0 },
  },
};

export default RouteTransitionManager;
