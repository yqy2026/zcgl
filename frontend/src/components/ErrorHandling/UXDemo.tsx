import React, { useState } from 'react'
import { Card, Button, Space, Divider, Row, Col, Typography, Input, Form, Switch } from 'antd'
import {
  BugOutlined,
  ExperimentOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  DeleteOutlined,
} from '@ant-design/icons'

import { GlobalErrorBoundary, ErrorPage } from '@/components/ErrorHandling'
import { 
  LoadingSpinner, 
  SkeletonLoader 
} from '@/components/Loading'
import {
  SuccessNotification,
  EmptyState,
  ConfirmDialog,
  ProgressIndicator,
  ActionFeedback,
  showDeleteConfirm,
} from '@/components/Feedback'
import {
  useUXEnhancement,
  useLoadingState,
  useOperationState,
  useFormEnhancement,
  useNetworkStatus,
} from '@/hooks/useUXEnhancement'

const { Title, Paragraph, Text } = Typography

// 错误组件用于测试错误边界
const ErrorComponent: React.FC<{ shouldError: boolean }> = ({ shouldError }) => {
  if (shouldError) {
    throw new Error('这是一个测试错误，用于演示错误边界功能')
  }
  return <div>正常组件内容</div>
}

const UXDemo: React.FC = () => {
  const [showError, setShowError] = useState(false)
  const [errorPageType, setErrorPageType] = useState<'404' | '403' | '500' | 'network'>('404')
  const [loadingType, setLoadingType] = useState<'spinner' | 'skeleton'>('spinner')
  const [skeletonType, setSkeletonType] = useState<'list' | 'card' | 'form' | 'table'>('list')
  const [confirmVisible, setConfirmVisible] = useState(false)
  const [progressPercent, setProgressPercent] = useState(0)
  const [actionResult, setActionResult] = useState<any>(null)

  // 使用UX增强Hook
  const ux = useUXEnhancement({
    trackPageView: 'ux-demo',
    enableErrorHandling: true,
    enablePerformanceMonitoring: true,
    enableNetworkMonitoring: true,
  })

  const { loading, withLoading } = useLoadingState('demo')
  const operationState = useOperationState()
  const formEnhancement = useFormEnhancement()
  const networkStatus = useNetworkStatus()

  // 模拟异步操作
  const simulateAsyncOperation = async (shouldFail = false) => {
    await new Promise(resolve => setTimeout(resolve, 2000))
    if (shouldFail) {
      throw new Error('模拟操作失败')
    }
    return { message: '操作成功完成', data: { id: 1, name: '测试数据' } }
  }

  // 模拟进度更新
  const simulateProgress = () => {
    setProgressPercent(0)
    const interval = setInterval(() => {
      setProgressPercent(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + 10
      })
    }, 200)
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* 页面标题 */}
      <Card style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <ExperimentOutlined style={{ color: '#1890ff', marginRight: '8px' }} />
          用户体验组件演示
        </Title>
        <Paragraph>
          这个页面展示了所有的错误处理和用户体验增强组件，包括错误边界、加载状态、
          用户反馈、确认对话框、进度指示器等。
        </Paragraph>
        
        {/* 网络状态显示 */}
        <div style={{ marginTop: '16px' }}>
          <Text type="secondary">
            网络状态: {networkStatus.isOnline ? '在线' : '离线'} 
            {networkStatus.connectionType && ` (${networkStatus.connectionType})`}
          </Text>
        </div>
      </Card>

      <Row gutter={16}>
        {/* 错误处理演示 */}
        <Col xs={24} lg={12}>
          <Card title="错误处理演示" style={{ marginBottom: '16px' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>错误边界测试:</Text>
                <div style={{ marginTop: '8px' }}>
                  <Switch
                    checked={showError}
                    onChange={setShowError}
                    checkedChildren="触发错误"
                    unCheckedChildren="正常状态"
                  />
                </div>
                <div style={{ marginTop: '16px', padding: '16px', border: '1px dashed #d9d9d9' }}>
                  <GlobalErrorBoundary>
                    <ErrorComponent shouldError={showError} />
                  </GlobalErrorBoundary>
                </div>
              </div>

              <Divider />

              <div>
                <Text strong>错误页面演示:</Text>
                <div style={{ marginTop: '8px' }}>
                  <Space wrap>
                    <Button 
                      size="small" 
                      type={errorPageType === '404' ? 'primary' : 'default'}
                      onClick={() => setErrorPageType('404')}
                    >
                      404错误
                    </Button>
                    <Button 
                      size="small" 
                      type={errorPageType === '403' ? 'primary' : 'default'}
                      onClick={() => setErrorPageType('403')}
                    >
                      403错误
                    </Button>
                    <Button 
                      size="small" 
                      type={errorPageType === '500' ? 'primary' : 'default'}
                      onClick={() => setErrorPageType('500')}
                    >
                      500错误
                    </Button>
                    <Button 
                      size="small" 
                      type={errorPageType === 'network' ? 'primary' : 'default'}
                      onClick={() => setErrorPageType('network')}
                    >
                      网络错误
                    </Button>
                  </Space>
                </div>
                <div style={{ marginTop: '16px', border: '1px dashed #d9d9d9' }}>
                  <ErrorPage type={errorPageType} />
                </div>
              </div>
            </Space>
          </Card>
        </Col>

        {/* 加载状态演示 */}
        <Col xs={24} lg={12}>
          <Card title="加载状态演示" style={{ marginBottom: '16px' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>加载类型选择:</Text>
                <div style={{ marginTop: '8px' }}>
                  <Space>
                    <Button 
                      size="small" 
                      type={loadingType === 'spinner' ? 'primary' : 'default'}
                      onClick={() => setLoadingType('spinner')}
                    >
                      加载动画
                    </Button>
                    <Button 
                      size="small" 
                      type={loadingType === 'skeleton' ? 'primary' : 'default'}
                      onClick={() => setLoadingType('skeleton')}
                    >
                      骨架屏
                    </Button>
                  </Space>
                </div>
              </div>

              {loadingType === 'skeleton' && (
                <div>
                  <Text strong>骨架屏类型:</Text>
                  <div style={{ marginTop: '8px' }}>
                    <Space wrap>
                      {['list', 'card', 'form', 'table'].map(type => (
                        <Button
                          key={type}
                          size="small"
                          type={skeletonType === type ? 'primary' : 'default'}
                          onClick={() => setSkeletonType(type as any)}
                        >
                          {type}
                        </Button>
                      ))}
                    </Space>
                  </div>
                </div>
              )}

              <div style={{ marginTop: '16px', border: '1px dashed #d9d9d9', minHeight: '200px' }}>
                {loadingType === 'spinner' ? (
                  <LoadingSpinner 
                    loading={loading} 
                    tip="正在加载数据..." 
                    size="large"
                  >
                    <div style={{ padding: '20px', textAlign: 'center' }}>
                      <Text>这里是实际内容</Text>
                    </div>
                  </LoadingSpinner>
                ) : (
                  <SkeletonLoader 
                    type={skeletonType} 
                    loading={loading} 
                    rows={3}
                  >
                    <div style={{ padding: '20px', textAlign: 'center' }}>
                      <Text>这里是实际内容</Text>
                    </div>
                  </SkeletonLoader>
                )}
              </div>

              <Button 
                type="primary" 
                loading={loading}
                onClick={() => withLoading(() => simulateAsyncOperation())}
              >
                {loading ? '加载中...' : '开始加载'}
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* 用户反馈演示 */}
        <Col xs={24} lg={12}>
          <Card title="用户反馈演示" style={{ marginBottom: '16px' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>通知消息:</Text>
                <div style={{ marginTop: '8px' }}>
                  <Space wrap>
                    <Button 
                      size="small" 
                      icon={<CheckCircleOutlined />}
                      onClick={() => SuccessNotification.success.create('测试数据')}
                    >
                      成功
                    </Button>
                    <Button 
                      size="small" 
                      icon={<ExclamationCircleOutlined />}
                      onClick={() => SuccessNotification.warning.unsaved()}
                    >
                      警告
                    </Button>
                    <Button 
                      size="small" 
                      icon={<CloseCircleOutlined />}
                      onClick={() => SuccessNotification.error.operation('测试操作')}
                    >
                      错误
                    </Button>
                    <Button 
                      size="small" 
                      onClick={() => SuccessNotification.info.processing('数据处理')}
                    >
                      信息
                    </Button>
                  </Space>
                </div>
              </div>

              <Divider />

              <div>
                <Text strong>确认对话框:</Text>
                <div style={{ marginTop: '8px' }}>
                  <Space wrap>
                    <Button 
                      size="small" 
                      icon={<DeleteOutlined />}
                      onClick={() => setConfirmVisible(true)}
                    >
                      删除确认
                    </Button>
                    <Button 
                      size="small"
                      onClick={() => showDeleteConfirm({
                        itemName: '测试项目',
                        onConfirm: () => ux.showSuccess('删除成功'),
                      })}
                    >
                      快速确认
                    </Button>
                  </Space>
                </div>
              </div>

              <Divider />

              <div>
                <Text strong>空状态演示:</Text>
                <div style={{ marginTop: '16px', border: '1px dashed #d9d9d9', minHeight: '150px' }}>
                  <EmptyState
                    type="no-data"
                    showCreateButton
                    onCreateClick={() => ux.showInfo('点击了创建按钮')}
                  />
                </div>
              </div>
            </Space>
          </Card>
        </Col>

        {/* 进度和操作状态演示 */}
        <Col xs={24} lg={12}>
          <Card title="进度和操作状态演示" style={{ marginBottom: '16px' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>进度指示器:</Text>
                <div style={{ marginTop: '16px' }}>
                  <ProgressIndicator
                    type="line"
                    percent={progressPercent}
                    status={progressPercent === 100 ? 'success' : 'active'}
                    title="任务进度"
                    description={`当前进度: ${progressPercent}%`}
                  />
                </div>
                <div style={{ marginTop: '16px' }}>
                  <Button 
                    size="small" 
                    onClick={simulateProgress}
                    disabled={progressPercent > 0 && progressPercent < 100}
                  >
                    开始进度
                  </Button>
                </div>
              </div>

              <Divider />

              <div>
                <Text strong>操作状态管理:</Text>
                <div style={{ marginTop: '16px' }}>
                  <Space wrap>
                    <Button 
                      loading={operationState.loading}
                      onClick={() => operationState.execute(
                        () => simulateAsyncOperation(false),
                        {
                          successMessage: '操作成功完成',
                          errorMessage: '操作执行失败',
                          trackAction: 'demo_operation',
                        }
                      )}
                    >
                      成功操作
                    </Button>
                    <Button 
                      loading={operationState.loading}
                      onClick={() => operationState.execute(
                        () => simulateAsyncOperation(true),
                        {
                          successMessage: '操作成功完成',
                          errorMessage: '操作执行失败',
                          trackAction: 'demo_operation_fail',
                        }
                      )}
                    >
                      失败操作
                    </Button>
                    <Button 
                      size="small"
                      onClick={operationState.reset}
                    >
                      重置状态
                    </Button>
                  </Space>
                </div>

                {(operationState.success || operationState.error) && (
                  <div style={{ marginTop: '16px' }}>
                    <ActionFeedback
                      result={{
                        status: operationState.success ? 'success' : 'error',
                        message: operationState.success 
                          ? '操作成功完成' 
                          : operationState.error?.message || '操作失败',
                        data: operationState.data,
                        error: operationState.error,
                      }}
                      onRetry={() => operationState.execute(() => simulateAsyncOperation(false))}
                    />
                  </div>
                )}
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 表单增强演示 */}
      <Card title="表单增强演示" style={{ marginBottom: '16px' }}>
        <Form layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="测试输入">
                <Input 
                  placeholder="输入内容测试表单状态"
                  onChange={() => formEnhancement.markDirty()}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="操作">
                <Space>
                  <Button 
                    type="primary"
                    onClick={() => {
                      formEnhancement.markClean()
                      ux.showSuccess('表单已保存')
                    }}
                  >
                    保存
                  </Button>
                  <Button 
                    onClick={() => formEnhancement.confirmLeave(() => {
                      ux.showInfo('已离开表单')
                    })}
                  >
                    离开
                  </Button>
                  <Button 
                    size="small"
                    onClick={formEnhancement.warnUnsaved}
                  >
                    检查未保存
                  </Button>
                </Space>
              </Form.Item>
            </Col>
          </Row>
          
          <div style={{ marginTop: '16px' }}>
            <Text type="secondary">
              表单状态: {formEnhancement.isDirty ? '有未保存更改' : '已保存'}
              {formEnhancement.hasErrors && ' | 有验证错误'}
            </Text>
          </div>
        </Form>
      </Card>

      {/* 确认对话框 */}
      <ConfirmDialog
        type="delete"
        visible={confirmVisible}
        itemName="测试项目"
        onConfirm={() => {
          setConfirmVisible(false)
          ux.showSuccess('删除成功')
        }}
        onCancel={() => setConfirmVisible(false)}
      />
    </div>
  )
}

export default UXDemo