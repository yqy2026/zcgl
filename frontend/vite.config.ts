import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { visualizer } from 'rollup-plugin-visualizer';
import compression from 'vite-plugin-compression';

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const isProduction = mode === 'production';
  const isDevelopment = mode === 'development';

  return {
    plugins: [
      react({
        // React 19 JSX runtime configuration
        // Explicitly set to 'react' for compatibility
        // See: https://react.dev/blog/2024/12/05/react-19
        jsxImportSource: 'react',
      }),

      // 生产环境压缩
      isProduction &&
      compression({
        algorithm: 'gzip',
        ext: '.gz',
      }),

      isProduction &&
      compression({
        algorithm: 'brotliCompress',
        ext: '.br',
      }),

      // 包分析报告（可选）
      process.env.ANALYZE &&
      visualizer({
        filename: 'dist/stats.html',
        open: true,
        gzipSize: true,
        brotliSize: true,
        template: 'treemap',
      }),
    ].filter(Boolean),

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@/components': path.resolve(__dirname, './src/components'),
        '@/pages': path.resolve(__dirname, './src/pages'),
        '@/services': path.resolve(__dirname, './src/services'),
        '@/types': path.resolve(__dirname, './src/types'),
        '@/utils': path.resolve(__dirname, './src/utils'),
        '@/hooks': path.resolve(__dirname, './src/hooks'),
        '@/store': path.resolve(__dirname, './src/store'),
        // Mock @sentry/react for builds (optional dependency)
        '@sentry/react': path.resolve(__dirname, './src/mocks/sentry.ts'),
      },
    },

    server: {
      port: 5173,
      host: true,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8002', // 修改为8002端口
          changeOrigin: true,
          secure: false,
          ws: true,
          timeout: 120000,
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log('proxy error', err);
            });
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              console.log('Sending Request to the Target:', req.method, req.url);
              proxyReq.setHeader('Connection', 'keep-alive');
            });
            proxy.on('proxyRes', (proxyRes, req, _res) => {
              console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
            });
          },
        },
      },
    },

    build: {
      target: ['es2022', 'chrome90', 'firefox98', 'safari14'],
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: isDevelopment || env.VITE_SOURCEMAP === 'true',

      rollupOptions: {
        output: {
          // 详细的代码分割策略
          manualChunks: id => {
            if (id.includes('node_modules')) {
              // React核心库（最高优先级，单独分包）
              if (id.includes('react/') || id.includes('react-dom/')) {
                return 'react-core';
              }

              // React路由（独立分包）
              if (id.includes('react-router')) {
                return 'react-router';
              }

              // Ant Design核心（独立分包）
              if (id.includes('antd/es/') || id.includes('@ant-design/icons')) {
                return 'antd-core';
              }

              // Ant Design图表组件（按需分包）
              if (id.includes('@ant-design/plots') || id.includes('@ant-design/charts')) {
                return 'antd-charts';
              }

              // 表单处理库（独立分包）
              if (id.includes('react-hook-form') || id.includes('@hookform')) {
                return 'form-libs';
              }

              if (id.includes('zod')) {
                return 'validation';
              }

              // 状态管理（独立分包）
              if (id.includes('zustand')) {
                return 'state-management';
              }

              // 数据获取（独立分包）
              if (id.includes('@tanstack/react-query')) {
                return 'data-fetching';
              }

              // HTTP客户端（独立分包）
              if (id.includes('axios')) {
                return 'http-client';
              }

              // 工具库（合并分包）
              if (id.includes('lodash') || id.includes('dayjs') || id.includes('uuid')) {
                return 'utils-vendor';
              }

              // Excel处理（独立分包）
              if (id.includes('xlsx') || id.includes('exceljs')) {
                return 'excel-vendor';
              }

              // 其他小型第三方库
              return 'vendor-misc';
            }

            // 应用代码分割策略
            if (id.includes('/pages/Dashboard/')) {
              return 'page-dashboard';
            }

            if (id.includes('/pages/Assets/')) {
              return 'page-assets';
            }

            if (
              id.includes('/pages/') &&
              !id.includes('/pages/Dashboard/') &&
              !id.includes('/pages/Assets/')
            ) {
              return 'page-others';
            }

            // 组件分割（按功能分组）
            if (id.includes('/components/Asset/')) {
              return 'components-asset';
            }

            if (id.includes('/components/Charts/')) {
              return 'components-charts';
            }

            if (id.includes('/components/Layout/')) {
              return 'components-layout';
            }

            if (id.includes('/components/')) {
              return 'components-common';
            }

            // 服务层、工具函数等
            if (id.includes('/services/')) {
              return 'services';
            }

            if (id.includes('/utils/')) {
              return 'utils';
            }

            if (id.includes('/hooks/')) {
              return 'hooks';
            }
          },

          // 资源文件命名策略
          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: assetInfo => {
            const info = assetInfo.name.split('.');
            const ext = info[info.length - 1];

            // 图片文件
            if (/\.(png|jpe?g|gif|svg|webp|avif)(\?.*)?$/i.test(assetInfo.name)) {
              return `assets/images/[name]-[hash].${ext}`;
            }

            // CSS文件
            if (ext === 'css') {
              return `assets/css/[name]-[hash].${ext}`;
            }

            return `assets/[ext]/[name]-[hash].${ext}`;
          },
        },
      },

      // 压缩配置
      minify: isProduction ? 'terser' : false,
      terserOptions: isProduction
        ? {
          compress: {
            drop_console: true,
            drop_debugger: true,
            pure_funcs: ['console.log', 'console.info'],
          },
          mangle: {},
          format: {
            comments: false,
          },
        }
        : {},

      // 资源内联阈值
      assetsInlineLimit: 4096,
      cssCodeSplit: true,
      manifest: isProduction,
      reportCompressedSize: isProduction,
      chunkSizeWarningLimit: 1000,
    },

    // 预构建优化
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        'antd',
        '@ant-design/icons',
        'axios',
        'dayjs',
        'lodash',
        'zustand',
        '@tanstack/react-query',
        'react-hook-form',
        'zod',
      ],
      // Force dependency pre-bundling (useful for debugging dependency issues)
      // Enable via: FORCE_OPTIMIZE=true pnpm dev
      force: env.FORCE_OPTIMIZE === 'true',
    },

    // 环境变量
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version || '1.0.0'),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
      __DEV__: isDevelopment,
      __PROD__: isProduction,
      'process.env.NODE_ENV': JSON.stringify(mode),
    },

    // CSS预处理器配置
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
          modifyVars: {
            // Ant Design 6 new default primary color
            // Updated from #1890ff (Ant Design 5)
            '@primary-color': '#1677ff',
            '@border-radius-base': '6px',
          },
        },
      },
      devSourcemap: isDevelopment,
    },
  };
});
