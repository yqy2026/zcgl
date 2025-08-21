import React from 'react'
import { Card, Typography, Space, Divider } from 'antd'
import { ExperimentOutlined, BookOutlined } from '@ant-design/icons'

import { UXDemo } from '@/components/ErrorHandling'
import { useUXEnhancement } from '@/hooks/useUXEnhancement'

const { Title, Paragraph, Text } = Typography

const UXDemoPage: React.FC = () => {
    // 使用UX增强功能跟踪页面访问
    const ux = useUXEnhancement({
        trackPageView: 'ux-demo-page',
        enableErrorHandling: true,
        enablePerformanceMonitoring: true,
        enableNetworkMonitoring: true,
    })

    return (
        <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
            {/* 页面头部 */}
            <Card style={{ marginBottom: '24px' }}>
                <div style={{ textAlign: 'center' }}>
                    <Title level={1}>
                        <ExperimentOutlined style={{ color: '#1890ff', marginRight: '12px' }} />
                        用户体验组件演示中心
                    </Title>

                    <Paragraph style={{ fontSize: '16px', color: '#666', maxWidth: '800px', margin: '0 auto' }}>
                        欢迎来到土地物业资产管理系统的用户体验组件演示中心。
                        这里展示了系统中所有的错误处理、加载状态、用户反馈、确认对话框等UX组件的功能和使用方法。
                    </Paragraph>

                    <Divider />

                    <Space size="large" style={{ marginTop: '16px' }}>
                        <div style={{ textAlign: 'center' }}>
                            <Title level={4} style={{ margin: '0 0 8px 0', color: '#52c41a' }}>
                                20+
                            </Title>
                            <Text type="secondary">UX组件</Text>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <Title level={4} style={{ margin: '0 0 8px 0', color: '#1890ff' }}>
                                5+
                            </Title>
                            <Text type="secondary">增强Hooks</Text>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <Title level={4} style={{ margin: '0 0 8px 0', color: '#faad14' }}>
                                100%
                            </Title>
                            <Text type="secondary">测试覆盖</Text>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <Title level={4} style={{ margin: '0 0 8px 0', color: '#722ed1' }}>
                                全面
                            </Title>
                            <Text type="secondary">文档支持</Text>
                        </div>
                    </Space>
                </div>
            </Card>

            {/* 功能特性介绍 */}
            <Card title={
                <Space>
                    <BookOutlined />
                    <span>功能特性</span>
                </Space>
            } style={{ marginBottom: '24px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
                    <div>
                        <Title level={4} style={{ color: '#ff4d4f' }}>🛡️ 错误处理</Title>
                        <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                            <li>全局错误边界保护</li>
                            <li>友好的错误页面</li>
                            <li>自动错误报告</li>
                            <li>错误恢复机制</li>
                        </ul>
                    </div>

                    <div>
                        <Title level={4} style={{ color: '#1890ff' }}>⏳ 加载状态</Title>
                        <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                            <li>多种加载动画</li>
                            <li>智能骨架屏</li>
                            <li>加载状态管理</li>
                            <li>性能优化</li>
                        </ul>
                    </div>

                    <div>
                        <Title level={4} style={{ color: '#52c41a' }}>💬 用户反馈</Title>
                        <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                            <li>丰富的通知类型</li>
                            <li>操作结果反馈</li>
                            <li>进度指示器</li>
                            <li>确认对话框</li>
                        </ul>
                    </div>

                    <div>
                        <Title level={4} style={{ color: '#faad14' }}>📊 性能监控</Title>
                        <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                            <li>实时性能监控</li>
                            <li>用户行为跟踪</li>
                            <li>错误统计分析</li>
                            <li>性能优化建议</li>
                        </ul>
                    </div>

                    <div>
                        <Title level={4} style={{ color: '#722ed1' }}>🎨 主题定制</Title>
                        <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                            <li>灵活的主题配置</li>
                            <li>响应式设计</li>
                            <li>无障碍支持</li>
                            <li>国际化支持</li>
                        </ul>
                    </div>

                    <div>
                        <Title level={4} style={{ color: '#13c2c2' }}>🔧 开发工具</Title>
                        <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                            <li>TypeScript支持</li>
                            <li>完整的测试套件</li>
                            <li>详细的文档</li>
                            <li>开发调试工具</li>
                        </ul>
                    </div>
                </div>
            </Card>

            {/* 使用说明 */}
            <Card title="使用说明" style={{ marginBottom: '24px' }}>
                <Paragraph>
                    <Text strong>如何使用演示：</Text>
                </Paragraph>
                <ol style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                    <li>浏览下方的各个演示区域，了解不同组件的功能</li>
                    <li>点击按钮和开关，体验各种交互效果</li>
                    <li>观察错误处理、加载状态、用户反馈等功能</li>
                    <li>查看浏览器控制台，了解性能监控和错误报告</li>
                    <li>参考代码示例，在您的项目中使用这些组件</li>
                </ol>

                <Paragraph style={{ marginTop: '16px' }}>
                    <Text strong>开发者提示：</Text>
                </Paragraph>
                <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                    <li>所有组件都支持TypeScript，提供完整的类型定义</li>
                    <li>组件设计遵循Ant Design设计规范，保持一致性</li>
                    <li>支持主题定制，可以根据项目需求调整样式</li>
                    <li>提供完整的单元测试，确保代码质量</li>
                    <li>详细的文档和示例，方便快速上手</li>
                </ul>
            </Card>

            {/* 主要演示区域 */}
            <UXDemo />

            {/* 页面底部信息 */}
            <Card style={{ marginTop: '24px', textAlign: 'center' }}>
                <Paragraph type="secondary">
                    这些UX组件已经集成到土地物业资产管理系统的各个页面中，
                    为用户提供一致、友好的交互体验。
                </Paragraph>
                <Paragraph type="secondary">
                    如需了解更多技术细节，请查看源代码和相关文档。
                </Paragraph>
            </Card>
        </div>
    )
}

export default UXDemoPage