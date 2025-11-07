import { useEffect, useRef, useCallback } from "react";
import { useLocation } from "react-router-dom";

// 预加载模块类型定义
interface PreloadModule {
  default: React.ComponentType<any>;
}

// 预加载函数类型
type PreloadFunction = () => Promise<PreloadModule>;

// 调试接口
interface PreloadDebugInterface {
  getStats: () => any;
  clearCache: () => void;
  manager: SmartPreloadManager | null;
}

// 扩展Window接口
declare global {
  interface Window {
    __PRELOAD_DEBUG__?: PreloadDebugInterface;
  }
}

// 预加载配置
interface PreloadConfig {
  threshold: number; // 预加载阈值（毫秒）
  maxConcurrent: number; // 最大并发预加载数
  enabledRoutes: string[]; // 启用预加载的路由
  priorityRoutes: string[]; // 高优先级路由
}

const DEFAULT_CONFIG: PreloadConfig = {
  threshold: 200,
  maxConcurrent: 3,
  enabledRoutes: ["/assets/list", "/rental/contracts", "/system/users", "/dashboard"],
  priorityRoutes: ["/dashboard", "/assets/list"],
};

// 用户行为跟踪
interface UserBehavior {
  lastActiveTime: number;
  hoveredRoutes: Set<string>;
  visitedRoutes: Set<string>;
  currentRoute: string;
  interactionCount: number;
}

class SmartPreloadManager {
  private config: PreloadConfig;
  private behavior: UserBehavior;
  private preloadQueue: PreloadFunction[];
  private activePreloads: Set<string>;
  private preloadCache: Map<string, Promise<PreloadModule>>;
  private observers: Set<() => void>;

  constructor(config: Partial<PreloadConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.behavior = {
      lastActiveTime: Date.now(),
      hoveredRoutes: new Set(),
      visitedRoutes: new Set(),
      currentRoute: "",
      interactionCount: 0,
    };
    this.preloadQueue = [];
    this.activePreloads = new Set();
    this.preloadCache = new Map();
    this.observers = new Set();

    this.initializeObservers();
  }

  private initializeObservers() {
    // 监听用户交互
    if (typeof window !== "undefined") {
      document.addEventListener("mousemove", this.handleMouseMove.bind(this));
      document.addEventListener("click", this.handleClick.bind(this));
      document.addEventListener("keydown", this.handleKeyDown.bind(this));

      // 监听页面可见性变化
      document.addEventListener("visibilitychange", this.handleVisibilityChange.bind(this));
    }
  }

  private handleMouseMove = (event: MouseEvent) => {
    this.behavior.lastActiveTime = Date.now();
    this.behavior.interactionCount++;

    // 检查鼠标是否悬停在可预加载的元素上
    const target = event.target as HTMLElement;
    const routeElement = target.closest("[data-route]");
    if (routeElement) {
      const route = routeElement.getAttribute("data-route");
      if (route && this.config.enabledRoutes.includes(route)) {
        this.schedulePreload(route, "hover");
      }
    }
  };

  private handleClick = (event: MouseEvent) => {
    this.behavior.lastActiveTime = Date.now();

    const target = event.target as HTMLElement;
    const linkElement = target.closest("a[href]");
    if (linkElement) {
      const href = linkElement.getAttribute("href");
      if (href && this.config.enabledRoutes.includes(href)) {
        this.schedulePreload(href, "click");
      }
    }
  };

  private handleKeyDown = () => {
    this.behavior.lastActiveTime = Date.now();
    this.behavior.interactionCount++;
  };

  private handleVisibilityChange = () => {
    if (document.hidden) {
      // 页面隐藏时暂停预加载
      this.pausePreloading();
    } else {
      // 页面可见时恢复预加载
      this.resumePreloading();
    }
  };

  private schedulePreload(route: string, trigger: "hover" | "click" | "predictive") {
    if (this.activePreloads.has(route) || this.preloadCache.has(route)) {
      return;
    }

    // 根据触发方式设置不同的延迟
    let delay = this.config.threshold;
    if (trigger === "hover") {
      delay = 100; // 悬停时较快预加载
    } else if (trigger === "click") {
      delay = 0; // 点击时立即预加载
    }

    setTimeout(() => {
      this.executePreload(route);
    }, delay);
  }

  private async executePreload(route: string) {
    if (this.activePreloads.has(route) || this.preloadCache.has(route)) {
      return;
    }

    this.activePreloads.add(route);

    try {
      // 获取预加载函数
      const preloadFn = this.getPreloadFunction(route);
      if (preloadFn) {
        const promise = preloadFn();
        this.preloadCache.set(route, promise);
        await promise;

        // Preload completed
      }
    } catch (error) {
      console.warn(`预加载失败: ${route}`, error);
    } finally {
      this.activePreloads.delete(route);
    }
  }

  private getPreloadFunction(route: string): PreloadFunction | null {
    // 预加载函数映射
    const preloadFunctions: Record<string, PreloadFunction> = {
      "/dashboard": () => import("../pages/Dashboard/DashboardPage"),
      "/assets/list": () => import("../pages/Assets/AssetListPage"),
      "/assets/new": () => import("../pages/Assets/AssetCreatePage"),
      "/rental/contracts": () => import("../pages/Rental/ContractListPage"),
      "/system/users": () => import("../pages/System/UserManagementPage"),
      "/system/roles": () => import("../pages/System/RoleManagementPage"),
    };

    return preloadFunctions[route] || null;
  }

  private pausePreloading() {
    // 暂停预加载逻辑
    // Pause preloading
  }

  private resumePreloading() {
    // 恢复预加载逻辑
    // Resume preloading
  }

  // 预测性预加载
  private predictivePreload(currentRoute: string) {
    const predictions = this.getPredictedRoutes(currentRoute);
    predictions.forEach((route) => {
      this.schedulePreload(route, "predictive");
    });
  }

  private getPredictedRoutes(currentRoute: string): string[] {
    // 基于历史行为预测下一个可能访问的路由
    const predictions: string[] = [];

    // 根据当前路由预测
    if (currentRoute === "/dashboard") {
      predictions.push("/assets/list", "/rental/contracts");
    } else if (currentRoute === "/assets/list") {
      predictions.push("/assets/new", "/assets/analytics");
    } else if (currentRoute === "/rental/contracts") {
      predictions.push("/rental/contracts/new");
    }

    // 优先返回高优先级路由
    return predictions.filter((route) => this.config.priorityRoutes.includes(route));
  }

  // 公共API
  public updateCurrentRoute(route: string) {
    this.behavior.visitedRoutes.add(route);
    this.behavior.currentRoute = route;

    // 触发预测性预加载
    this.predictivePreload(route);
  }

  public clearCache() {
    this.preloadCache.clear();
    // Preload cache cleared
  }

  public getCacheStats() {
    return {
      cachedRoutes: this.preloadCache.size,
      activePreloads: this.activePreloads.size,
      visitedRoutes: this.behavior.visitedRoutes.size,
      interactionCount: this.behavior.interactionCount,
    };
  }

  public destroy() {
    // 清理事件监听器
    if (typeof window !== "undefined") {
      document.removeEventListener("mousemove", this.handleMouseMove);
      document.removeEventListener("click", this.handleClick);
      document.removeEventListener("keydown", this.handleKeyDown);
      document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    }

    this.clearCache();
  }
}

// 全局预加载管理器实例
let globalPreloadManager: SmartPreloadManager | null = null;

export const useSmartPreload = (config?: Partial<PreloadConfig>) => {
  const location = useLocation();
  const managerRef = useRef<SmartPreloadManager>();

  // 初始化管理器
  if (!managerRef.current) {
    managerRef.current = new SmartPreloadManager(config);
    globalPreloadManager = managerRef.current;
  }

  // 更新当前路由
  useEffect(() => {
    if (managerRef.current) {
      managerRef.current.updateCurrentRoute(location.pathname);
    }
  }, [location.pathname]);

  // 清理
  useEffect(() => {
    return () => {
      if (managerRef.current) {
        managerRef.current.destroy();
      }
    };
  }, []);

  // 提供预加载函数
  const preloadRoute = useCallback((route: string) => {
    if (managerRef.current) {
      managerRef.current.schedulePreload(route, "predictive");
    }
  }, []);

  const getStats = useCallback(() => {
    return managerRef.current?.getCacheStats() || null;
  }, []);

  const clearCache = useCallback(() => {
    managerRef.current?.clearCache();
  }, []);

  return {
    preloadRoute,
    getStats,
    clearCache,
    config: managerRef.current ? { ...DEFAULT_CONFIG, ...config } : DEFAULT_CONFIG,
  };
};

// 预加载高阶组件
export const withPreload = <T extends Record<string, unknown> = Record<string, unknown>>(
  Component: React.ComponentType<T>,
  route: string,
) => {
  return (props: T) => {
    const { preloadRoute } = useSmartPreload();

    useEffect(() => {
      preloadRoute(route);
    }, [preloadRoute, route]);

    return <Component {...props} />;
  };
};

// 预加载指令 - 用于组件中
export const usePreloadDirective = (routes: string[]) => {
  const { preloadRoute } = useSmartPreload();

  useEffect(() => {
    routes.forEach((route) => {
      preloadRoute(route);
    });
  }, [preloadRoute, routes]);
};

// 开发模式下的调试工具
export const usePreloadDebug = () => {
  const { getStats, clearCache } = useSmartPreload();

  if (process.env.NODE_ENV === "development") {
    // 暴露到全局对象用于调试
    if (typeof window !== "undefined") {
      window.__PRELOAD_DEBUG__ = {
        getStats,
        clearCache,
        manager: globalPreloadManager,
      };
    }
  }

  return { getStats, clearCache };
};

export default SmartPreloadManager;
