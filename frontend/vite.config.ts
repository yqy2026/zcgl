import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import compression from 'vite-plugin-compression'
import { createHtmlPlugin } from 'vite-plugin-html'

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isProduction = mode === 'production'
  const isDevelopment = mode === 'development'

  return {
    plugins: [
      react(),
      
      // HTML模板处理
      createHtmlPlugin({
        minify: isProduction,
        inject: {
          data: {
            title: 'Land Property Asset Management',
            description: '土地物业资产管理系统',
            keywords: 'asset management, property, land, real estate',
          },
        },
      }),
      
      // 生产环境压缩
      isProduction && compression({
        algorithm: 'gzip',
        ext: '.gz',
      }),
      
      isProduction && compression({
        algorithm: 'brotliCompress',
        ext: '.br',
      }),
      
      // 包分析报告
      process.env.ANALYZE && visualizer({
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
    },
  },
  
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false,
        ws: true,
        timeout: 30000,
        rewrite: (path) => path,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Sending Request to the Target:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        },
      },
    },
  },
  
    build: {
      // 生产环境优化
      target: ['es2015', 'chrome58', 'firefox57', 'safari11'],
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: isDevelopment || env.VITE_SOURCEMAP === 'true',
      
      // 代码分割优化
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            // 第三方库分割策略
            if (id.includes('node_modules')) {
              // React核心库（最高优先级，单独分包）
              if (id.includes('react/') || id.includes('react-dom/')) {
                return 'react-core'
              }
              
              // React路由（独立分包）
              if (id.includes('react-router')) {
                return 'react-router'
              }
              
              // Ant Design核心（独立分包）
              if (id.includes('antd/es/') || id.includes('@ant-design/icons')) {
                return 'antd-core'
              }
              
              // Ant Design图表组件（按需分包）
              if (id.includes('@ant-design/plots') || id.includes('@ant-design/charts')) {
                return 'antd-charts'
              }
              
              // 图表库（独立分包）
              if (id.includes('chart.js') || id.includes('react-chartjs-2')) {
                return 'chartjs'
              }
              
              if (id.includes('recharts')) {
                return 'recharts'
              }
              
              // 表单处理库（独立分包）
              if (id.includes('react-hook-form') || id.includes('@hookform')) {
                return 'form-libs'
              }
              
              if (id.includes('zod')) {
                return 'validation'
              }
              
              // 状态管理（独立分包）
              if (id.includes('zustand')) {
                return 'state-management'
              }
              
              // 数据获取（独立分包）
              if (id.includes('@tanstack/react-query')) {
                return 'data-fetching'
              }
              
              // HTTP客户端（独立分包）
              if (id.includes('axios')) {
                return 'http-client'
              }
              
              // 工具库（合并分包）
              if (id.includes('lodash') || id.includes('dayjs') || id.includes('uuid')) {
                return 'utils-vendor'
              }
              
              // Excel处理（独立分包）
              if (id.includes('xlsx') || id.includes('exceljs')) {
                return 'excel-vendor'
              }
              
              // 其他小型第三方库
              return 'vendor-misc'
            }
            
            // 应用代码分割策略
            
            // 页面组件（按功能模块分割）
            if (id.includes('/pages/Dashboard/')) {
              return 'page-dashboard'
            }
            
            if (id.includes('/pages/Assets/')) {
              return 'page-assets'
            }
            
            if (id.includes('/pages/') && !id.includes('/pages/Dashboard/') && !id.includes('/pages/Assets/')) {
              return 'page-others'
            }
            
            // 组件分割（按功能分组）
            if (id.includes('/components/Asset/')) {
              return 'components-asset'
            }
            
            if (id.includes('/components/Charts/')) {
              return 'components-charts'
            }
            
            if (id.includes('/components/Layout/')) {
              return 'components-layout'
            }
            
            if (id.includes('/components/ErrorHandling/') || id.includes('/components/Feedback/')) {
              return 'components-ux'
            }
            
            if (id.includes('/components/Loading/')) {
              return 'components-loading'
            }
            
            if (id.includes('/components/')) {
              return 'components-common'
            }
            
            // 服务层（按功能分割）
            if (id.includes('/services/')) {
              return 'services'
            }
            
            // 工具函数
            if (id.includes('/utils/')) {
              return 'utils'
            }
            
            // Hooks
            if (id.includes('/hooks/')) {
              return 'hooks'
            }
            
            // 状态管理
            if (id.includes('/store/')) {
              return 'store'
            }
            
            // 类型定义和配置
            if (id.includes('/types/') || id.includes('/schemas/') || id.includes('/config/')) {
              return 'types-config'
            }
          },
          
          // 资源文件命名策略
          chunkFileNames: (chunkInfo) => {
            const facadeModuleId = chunkInfo.facadeModuleId
            if (facadeModuleId && facadeModuleId.includes('pages/')) {
              return 'assets/js/pages/[name]-[hash].js'
            }
            return 'assets/js/[name]-[hash].js'
          },
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const info = assetInfo.name.split('.')
            const ext = info[info.length - 1]
            
            // 媒体文件
            if (/\.(mp4|webm|ogg|mp3|wav|flac|aac)(\?.*)?$/i.test(assetInfo.name)) {
              return `assets/media/[name]-[hash].${ext}`
            }
            
            // 图片文件
            if (/\.(png|jpe?g|gif|svg|webp|avif)(\?.*)?$/i.test(assetInfo.name)) {
              return `assets/images/[name]-[hash].${ext}`
            }
            
            // 字体文件
            if (/\.(woff2?|eot|ttf|otf)(\?.*)?$/i.test(assetInfo.name)) {
              return `assets/fonts/[name]-[hash].${ext}`
            }
            
            // CSS文件
            if (ext === 'css') {
              return `assets/css/[name]-[hash].${ext}`
            }
            
            return `assets/[ext]/[name]-[hash].${ext}`
          },
        },
        
        // 外部依赖（CDN）
        external: isProduction ? [] : [],
      },
      
      // 压缩配置
      minify: isProduction ? 'terser' : false,
      terserOptions: isProduction ? {
        compress: {
          drop_console: true,
          drop_debugger: true,
          pure_funcs: ['console.log', 'console.info'],
          passes: 2,
        },
        mangle: {
          safari10: true,
        },
        format: {
          comments: false,
        },
      } : {},
      
      // 资源内联阈值（4KB）
      assetsInlineLimit: 4096,
      
      // CSS代码分割
      cssCodeSplit: true,
      
      // 生成清单文件
      manifest: isProduction,
      
      // 报告压缩详情
      reportCompressedSize: isProduction,
      
      // Chunk大小警告限制
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
      exclude: [
        // 排除一些不需要预构建的包
      ],
    },
    
    // 环境变量
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version || '1.0.0'),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
      __DEV__: isDevelopment,
      __PROD__: isProduction,
    },
    
    // CSS预处理器配置
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
          modifyVars: {
            // Ant Design主题定制
            '@primary-color': '#1890ff',
            '@border-radius-base': '6px',
          },
        },
      },
      modules: {
        localsConvention: 'camelCase',
      },
      devSourcemap: isDevelopment,
    },
    
    // 实验性功能
    experimental: {
      renderBuiltUrl(filename, { hostType }) {
        if (hostType === 'js') {
          return { js: `/${filename}` }
        } else {
          return { relative: true }
        }
      },
    },
  }
})