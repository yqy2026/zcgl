/**
 * PDF导入主页面
 * 整合上传、状态查看、结果确认等所有功能
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import './PDFImportPage.css';

// API 错误接口
interface ApiError extends Error {
  response?: {
    data?: {
      message?: string
      detail?: string
    }
  }
  message?: string
}
import {
  Card,
  Tabs,
  Button,
  Space,
  Typography,
  Alert,
  message,
  notification,
  Spin,
  Row,
  Col,
  Statistic,
  Tag,
  Tooltip,
  Switch,
  Modal
} from 'antd';
import {
  UploadOutlined,
  FileTextOutlined,
  HistoryOutlined,
  SettingOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  EyeOutlined,
  ApiOutlined,
  StarOutlined,
  BulbOutlined
} from '@ant-design/icons';

import ContractImportUpload from './ContractImportUpload';
import ContractImportStatus from './ContractImportStatus';
import ContractImportReview from './ContractImportReview';
import PDFImportHelp from './PDFImportHelp';
import { pdfImportService } from '../../services/pdfImportService';
import type {
  FileUploadResponse,
  SessionProgress,
  CompleteResult,
  ConfirmedContractData,
  ConfirmImportResponse,
  ActiveSession
} from '../../services/pdfImportService';

const { Title, Text, Paragraph } = Typography;

interface UploadFile {
  uid: string;
  name: string;
  status: 'done' | 'error' | 'uploading';
  size?: number;
  type?: string;
  originFileObj?: File;
}

interface ProcessingSession {
  sessionId: string;
  fileInfo: UploadFile;
  status: 'uploading' | 'processing' | 'ready' | 'completed' | 'failed';
  progress: number;
  result?: CompleteResult;
  error?: string;
}

const PDFImportPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'upload' | 'history'>('upload');
  const [currentSession, setCurrentSession] = useState<ProcessingSession | null>(null);
  const [sessionHistory, setSessionHistory] = useState<ProcessingSession[]>([]);
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showSystemInfo, setShowSystemInfo] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [userPreferences, setUserPreferences] = useState({
    autoRefresh: true,
    showAdvancedOptions: false,
    preferMarkitdown: true,
    enableNotifications: true,
    compactView: false
  });

  // 使用 ref 避免闭包问题
  const currentSessionRef = useRef(currentSession);
  currentSessionRef.current = currentSession;

  // 加载系统信息和键盘快捷键
  useEffect(() => {
    loadSystemInfo();
    loadSessionHistory();
    loadUserPreferences();

    // 设置键盘快捷键
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl/Cmd + H: 显示帮助
      if ((event.ctrlKey || event.metaKey) && event.key === 'h') {
        event.preventDefault();
        setShowHelp(true);
      }
      // Ctrl/Cmd + K: 显示键盘快捷键
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        setShowKeyboardShortcuts(true);
      }
      // Ctrl/Cmd + R: 刷新数据
      if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        handleReload();
      }
      // Alt + 1: 切换到PDF导入标签
      if (event.altKey && event.key === '1') {
        event.preventDefault();
        setActiveTab('upload');
      }
      // Alt + 2: 切换到处理历史标签
      if (event.altKey && event.key === '2') {
        event.preventDefault();
        setActiveTab('history');
      }
      // Esc: 关闭所有模态框
      if (event.key === 'Escape') {
        setShowHelp(false);
        setShowKeyboardShortcuts(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 加载用户偏好设置
  const loadUserPreferences = useCallback(() => {
    try {
      const saved = localStorage.getItem('pdf-import-preferences');
      if (saved) {
        setUserPreferences(JSON.parse(saved));
      }
    } catch (error) {
      console.warn('加载用户偏好设置失败:', error);
    }
  }, []);

  // 保存用户偏好设置
  const saveUserPreferences = useCallback((prefs: typeof userPreferences) => {
    try {
      localStorage.setItem('pdf-import-preferences', JSON.stringify(prefs));
      setUserPreferences(prefs);
    } catch (error) {
      console.warn('保存用户偏好设置失败:', error);
    }
  }, []);

  const loadSystemInfo = async () => {
    try {
      const info = await pdfImportService.getSystemInfo();
      setSystemInfo(info);
    } catch (error) {
      console.error('加载系统信息失败:', error);
    }
  };

  const loadSessionHistory = async () => {
    try {
      const response = await pdfImportService.getActiveSessions();
      if (response.success) {
        // 转换为历史记录格式
        const history = response.active_sessions
          .filter(session => ['ready_for_review', 'failed', 'cancelled', 'completed'].includes(session.status))
          .map(session => ({
            sessionId: session.session_id,
            fileInfo: {
              uid: session.session_id,
              name: session.file_name,
              status: 'done',
              size: 0,
              type: 'application/pdf'
            },
            status: session.status === 'ready_for_review' ? 'ready' : session.status as any,
            progress: session.progress
          }));
        setSessionHistory(history);
      }
    } catch (error) {
      console.error('加载会话历史失败:', error);
    }
  };

  // 文件上传成功处理
  const handleUploadSuccess = (sessionId: string, fileInfo: UploadFile) => {
    // Upload success

    const newSession: ProcessingSession = {
      sessionId,
      fileInfo,
      status: 'processing',
      progress: 0
    };

    setCurrentSession(newSession);
    setActiveTab('upload');

    // 强制重新渲染
    setTimeout(() => {
      setCurrentSession(prev => prev ? {...prev} : null);
    }, 100);
  };

  // 文件上传失败处理
  const handleUploadError = (error: string) => {
    message.error(error);
    setCurrentSession(null);
  };

  // 处理完成处理
  const handleProcessingComplete = (result: CompleteResult) => {
    // Processing complete

    if (currentSession) {
      setCurrentSession({
        ...currentSession,
        status: 'ready',
        progress: 100,
        result
      });
    }
  };

  // 处理错误处理
  const handleProcessingError = (error: string) => {
    if (currentSession) {
      setCurrentSession({
        ...currentSession,
        status: 'failed',
        error
      });
    }
    message.error(error);
  };

  // 确认导入处理
  const handleConfirmImport = async (data: ConfirmedContractData): Promise<ConfirmImportResponse> => {
    try {
      const response = await pdfImportService.confirmImport(
        currentSession!.sessionId,
        data
      );

      if (response.success) {
        // 更新会话状态
        setCurrentSession({
          ...currentSession!,
          status: 'completed'
        });

        // 添加到历史记录
        if (currentSession) {
          setSessionHistory(prev => [currentSession, ...prev]);
        }

        // 显示成功通知
        if (userPreferences.enableNotifications) {
          notification.success({
            message: '合同导入成功！',
            description: `已成功导入合同 ${currentSession.fileInfo.name}`,
            duration: 4.5,
            placement: 'topRight'
          });
        } else {
          message.success('合同导入成功！');
        }
      }

      return response;
    } catch (error: unknown) {
      const apiError = error as ApiError
      if (userPreferences.enableNotifications) {
        notification.error({
          message: '导入失败',
          description: error.message || '合同导入过程中发生错误',
          duration: 6,
          placement: 'topRight'
        });
      } else {
        message.error(error.message || '导入失败');
      }
      throw error;
    }
  };

  // 取消处理
  const handleCancel = async () => {
    if (currentSession) {
      try {
        const response = await pdfImportService.cancelSession(currentSession.sessionId);
        if (response.success) {
          message.info('已取消导入');
          setCurrentSession(null);
        }
      } catch (error: unknown) {
      const apiError = error as ApiError
        message.error(error.message || '取消失败');
      }
    }
  };

  // 返回上传页面
  const handleBackToUpload = () => {
    setCurrentSession(null);
    setActiveTab('upload');
  };

  // 重新加载
  const handleReload = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadSystemInfo(),
        loadSessionHistory()
      ]);
      message.success('数据已刷新');
    } catch (error) {
      message.error('刷新失败');
    } finally {
      setLoading(false);
    }
  };

  // 测试系统功能
  const handleTestSystem = async () => {
    try {
      setLoading(true);
      const response = await pdfImportService.testConversion();
      if (response.system_ready) {
        message.success('系统功能正常');
      } else {
        message.warning('系统可能存在问题');
      }
    } catch (error: unknown) {
      const apiError = error as ApiError
      message.error('测试失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取系统状态统计 - 使用 useMemo 优化
  const systemStats = useMemo(() => {
    if (!systemInfo) return null;

    const { capabilities } = systemInfo;
    const availableCount = [
      capabilities.pdfplumber_available,
      capabilities.pymupdf_available,
      capabilities.spacy_available,
      capabilities.ocr_available
    ].filter(Boolean).length;

    return {
      total: 4,
      available: availableCount,
      percentage: Math.round((availableCount / 4) * 100)
    };
  }, [systemInfo]);

  // 渲染当前会话内容 - 使用 useMemo 优化复杂条件渲染
  const renderCurrentSession = useMemo(() => {
    if (!currentSession) {
      return (
        <ContractImportUpload
          key="upload-main"
          onUploadSuccess={handleUploadSuccess}
          onUploadError={handleUploadError}
        />
      );
    }

    const keyPrefix = `${currentSession.status}-${currentSession.sessionId}`;

    switch (currentSession.status) {
      case 'processing':
        return (
          <ContractImportStatus
            key={keyPrefix}
            sessionId={currentSession.sessionId}
            fileInfo={{
              filename: currentSession.fileInfo.name,
              size: currentSession.fileInfo.size || 0,
              content_type: currentSession.fileInfo.type || 'application/pdf'
            }}
            onComplete={handleProcessingComplete}
            onError={handleProcessingError}
            onCancel={handleCancel}
          />
        );
      case 'ready':
        return currentSession.result ? (
          <ContractImportReview
            key={keyPrefix}
            sessionId={currentSession.sessionId}
            result={currentSession.result}
            onConfirm={handleConfirmImport}
            onCancel={handleBackToUpload}
            onBack={handleBackToUpload}
          />
        ) : null;
      case 'completed':
        return (
          <div key={keyPrefix} style={{ textAlign: 'center', padding: '40px' }}>
            <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a', marginBottom: 16 }} />
            <Title level={4} style={{ color: '#52c41a' }}>
              导入成功！
            </Title>
            <Paragraph>
              合同已成功导入到系统中。
            </Paragraph>
            <Space>
              <Button type="primary" onClick={() => setCurrentSession(null)}>
                导入新合同
              </Button>
              <Button onClick={() => setActiveTab('history')}>
                查看历史记录
              </Button>
            </Space>
          </div>
        );
      case 'failed':
        return (
          <div key={keyPrefix} style={{ textAlign: 'center', padding: '40px' }}>
            <CloseCircleOutlined style={{ fontSize: 64, color: '#ff4d4f', marginBottom: 16 }} />
            <Title level={4} style={{ color: '#ff4d4f' }}>
              处理失败
            </Title>
            <Paragraph>
              {currentSession.error || '处理过程中发生错误'}
            </Paragraph>
            <Space>
              <Button onClick={() => setCurrentSession(null)}>
                重新上传
              </Button>
              <Button onClick={() => setActiveTab('history')}>
                查看历史记录
              </Button>
            </Space>
          </div>
        );
      default:
        return (
          <ContractImportUpload
            key="upload-initial"
            onUploadSuccess={handleUploadSuccess}
            onUploadError={handleUploadError}
          />
        );
    }
  }, [currentSession, handleUploadSuccess, handleUploadError, handleProcessingComplete,
      handleProcessingError, handleCancel, handleConfirmImport, handleBackToUpload, setActiveTab]);

  // 页面加载状态
  if (loading && !systemInfo && !currentSession) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        flexDirection: 'column',
        gap: 16
      }}>
        <Spin size="large" />
        <Text type="secondary">正在初始化PDF导入系统...</Text>
      </div>
    );
  }

  return (
    <div className="pdf-import-page" style={{
      animation: 'fadeIn 0.3s ease-in-out',
      minHeight: '100vh'
    }}>
      {/* 页面头部 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space size="large">
              <div className="status-icon">
                <UploadOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              </div>
              <div>
                <Title level={3} style={{ margin: 0 }}>
                  PDF合同智能导入
                </Title>
                <Text type="secondary">
                  上传PDF文件，自动提取合同信息并导入系统
                </Text>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ApiOutlined />}
                onClick={() => setShowKeyboardShortcuts(true)}
                title="快捷键: Ctrl/Cmd + K"
              >
                快捷键
              </Button>
              <Button
                icon={<QuestionCircleOutlined />}
                onClick={() => setShowHelp(true)}
                title="快捷键: Ctrl/Cmd + H"
              >
                使用帮助
              </Button>
              <Button
                icon={<SettingOutlined />}
                onClick={() => setShowSystemInfo(!showSystemInfo)}
              >
                {showSystemInfo ? '隐藏状态' : '系统状态'}
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleReload}
                loading={loading}
                title="快捷键: Ctrl/Cmd + R"
              >
                刷新
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 系统状态信息 */}
        {showSystemInfo && systemInfo && (
          <Alert
            message="系统状态"
            description={
              <div>
                <Row gutter={16}>
                  <Col span={6}>
                    <Tag color={systemInfo.capabilities.pdfplumber_available ? 'green' : 'orange'}>
                      PDFPlumber: {systemInfo.capabilities.pdfplumber_available ? '可用' : '不可用'}
                    </Tag>
                  </Col>
                  <Col span={6}>
                    <Tag color={systemInfo.capabilities.pymupdf_available ? 'green' : 'orange'}>
                      PyMuPDF: {systemInfo.capabilities.pymupdf_available ? '可用' : '不可用'}
                    </Tag>
                  </Col>
                  <Col span={6}>
                    <Tag color={systemInfo.capabilities.ocr_available ? 'green' : 'default'}>
                      OCR: {systemInfo.capabilities.ocr_available ? '可用' : '不可用'}
                    </Tag>
                  </Col>
                  <Col span={6}>
                    <Text type="secondary">
                      最大文件: {systemInfo.capabilities.max_file_size_mb}MB
                    </Text>
                  </Col>
                </Row>
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">
                    处理时间: {systemInfo.capabilities.estimated_processing_time} |
                    支持格式: {systemInfo.capabilities.supported_formats.join(', ')}
                  </Text>
                </div>
              </div>
            }
            type="info"
            showIcon
            action={
              <Button size="small" onClick={handleTestSystem}>
                测试功能
              </Button>
            }
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 统计信息 */}
        <Row gutter={16}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="活跃会话"
                value={sessionHistory.length + (currentSession ? 1 : 0)}
                prefix={<HistoryOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="系统状态"
                value={systemStats?.percentage || 0}
                suffix="%"
                prefix={<SettingOutlined />}
                valueStyle={{
                  color: systemStats?.percentage === 100 ? '#3f8600' : '#faad14'
                }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="文件大小限制"
                value={systemInfo?.capabilities.max_file_size_mb || 50}
                suffix="MB"
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="预估处理时间"
                value={systemInfo?.capabilities.estimated_processing_time || '30-60秒'}
                prefix={<SettingOutlined />}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 主要内容区域 */}
      <Spin
        spinning={loading}
        tip="正在加载数据..."
        size="large"
        delay={300}
      >
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as 'upload' | 'history')}
          items={[
            {
              key: 'upload',
              label: 'PDF导入',
              children: (
                <div>
                  {renderCurrentSession}
                </div>
              )
            },
            {
              key: 'history',
              label: '处理历史',
              children: (
                <Card title="导入历史记录">
                  {sessionHistory.length > 0 ? (
                    <div>
                      {sessionHistory.map((session, index) => (
                        <Card
                          key={session.sessionId}
                          size="small"
                          style={{ marginBottom: 8 }}
                          title={
                            <Space>
                              <Text>{session.fileInfo.name}</Text>
                              <Tag color={
                                session.status === 'completed' ? 'green' :
                                session.status === 'ready' ? 'blue' :
                                session.status === 'failed' ? 'red' : 'orange'
                              }>
                                {session.status === 'completed' ? '已完成' :
                                 session.status === 'ready' ? '待确认' :
                                 session.status === 'failed' ? '失败' : '其他'}
                              </Tag>
                            </Space>
                          }
                          extra={
                            <Space>
                              <Text type="secondary">
                                进度: {session.progress}%
                              </Text>
                              <Button size="small" type="text">
                                查看详情
                              </Button>
                            </Space>
                          }
                        >
                          <Text type="secondary">
                            会话ID: {session.sessionId}
                          </Text>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                      <HistoryOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
                      <Title level={4} style={{ color: '#d9d9d9' }}>
                        暂无导入记录
                      </Title>
                      <Paragraph>
                        开始上传PDF文件以创建导入记录。
                      </Paragraph>
                      <Button type="primary" onClick={() => setActiveTab('upload')}>
                        开始导入
                      </Button>
                    </div>
                  )}
                </Card>
              )
            }
          ]}
        />

        {/* 使用帮助模态框 */}
        <PDFImportHelp
          visible={showHelp}
          onClose={() => setShowHelp(false)}
        />

        {/* 键盘快捷键和设置模态框 */}
        <Modal
          title={
            <Space>
              <ApiOutlined />
              快捷键与设置
            </Space>
          }
          open={showKeyboardShortcuts}
          onCancel={() => setShowKeyboardShortcuts(false)}
          footer={[
            <Button key="close" onClick={() => setShowKeyboardShortcuts(false)}>
              保存并关闭
            </Button>
          ]}
          width={800}
        >
          <div>
            <Tabs
              defaultActiveKey="shortcuts"
              items={[
                {
                  key: 'shortcuts',
                  label: '快捷键',
                  children: (
                    <div>
                      <Alert
                        message="快捷键提示"
                        description="使用以下快捷键可以提高操作效率。所有快捷键都支持 Ctrl (Windows) 和 Cmd (Mac)。"
                        type="info"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />

                      <Row gutter={[16, 16]}>
                        <Col span={12}>
                          <Card size="small" title="功能快捷键">
                            <Space direction="vertical" size="small" style={{ width: '100%' }}>
                              <div>
                                <Tag color="blue">Ctrl/Cmd + H</Tag>
                                <Text>打开使用帮助</Text>
                              </div>
                              <div>
                                <Tag color="blue">Ctrl/Cmd + K</Tag>
                                <Text>显示快捷键</Text>
                              </div>
                              <div>
                                <Tag color="blue">Ctrl/Cmd + R</Tag>
                                <Text>刷新数据</Text>
                              </div>
                              <div>
                                <Tag color="blue">Esc</Tag>
                                <Text>关闭所有弹窗</Text>
                              </div>
                            </Space>
                          </Card>
                        </Col>
                        <Col span={12}>
                          <Card size="small" title="页面导航">
                            <Space direction="vertical" size="small" style={{ width: '100%' }}>
                              <div>
                                <Tag color="green">Alt + 1</Tag>
                                <Text>切换到PDF导入</Text>
                              </div>
                              <div>
                                <Tag color="green">Alt + 2</Tag>
                                <Text>切换到处理历史</Text>
                              </div>
                              <div>
                                <Tag color="orange">Tab</Tag>
                                <Text>切换焦点</Text>
                              </div>
                              <div>
                                <Tag color="orange">Enter</Tag>
                                <Text>确认操作</Text>
                              </div>
                            </Space>
                          </Card>
                        </Col>
                      </Row>

                      <Alert
                        message="提示"
                        description="快捷键功能在页面加载完成后生效。如果快捷键与其他软件冲突，请使用鼠标点击操作。"
                        type="info"
                        showIcon
                        icon={<BulbOutlined />}
                        style={{ marginTop: 16 }}
                      />
                    </div>
                  )
                },
                {
                  key: 'preferences',
                  label: '用户偏好',
                  children: (
                    <div>
                      <Alert
                        message="个性化设置"
                        description="根据您的使用习惯调整界面和功能设置。设置会自动保存到本地浏览器。"
                        type="info"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />

                      <Row gutter={[16, 16]}>
                        <Col span={12}>
                          <Card size="small" title="界面设置">
                            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                              <div>
                                <Space>
                                  <Text>启用桌面通知：</Text>
                                  <Switch
                                    checked={userPreferences.enableNotifications}
                                    onChange={(checked) => saveUserPreferences({
                                      ...userPreferences,
                                      enableNotifications: checked
                                    })}
                                  />
                                  <Tooltip title="在导入完成或失败时显示系统通知">
                                    <QuestionCircleOutlined style={{ color: '#999' }} />
                                  </Tooltip>
                                </Space>
                              </div>
                              <div>
                                <Space>
                                  <Text>紧凑视图：</Text>
                                  <Switch
                                    checked={userPreferences.compactView}
                                    onChange={(checked) => saveUserPreferences({
                                      ...userPreferences,
                                      compactView: checked
                                    })}
                                  />
                                  <Tooltip title="减少界面元素间距，显示更多内容">
                                    <QuestionCircleOutlined style={{ color: '#999' }} />
                                  </Tooltip>
                                </Space>
                              </div>
                              <div>
                                <Space>
                                  <Text>显示高级选项：</Text>
                                  <Switch
                                    checked={userPreferences.showAdvancedOptions}
                                    onChange={(checked) => saveUserPreferences({
                                      ...userPreferences,
                                      showAdvancedOptions: checked
                                    })}
                                  />
                                  <Tooltip title="显示更多技术性选项和详细信息">
                                    <QuestionCircleOutlined style={{ color: '#999' }} />
                                  </Tooltip>
                                </Space>
                              </div>
                            </Space>
                          </Card>
                        </Col>
                        <Col span={12}>
                          <Card size="small" title="处理设置">
                            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                              <div>
                                <Space>
                                  <Text>自动刷新进度：</Text>
                                  <Switch
                                    checked={userPreferences.autoRefresh}
                                    onChange={(checked) => saveUserPreferences({
                                      ...userPreferences,
                                      autoRefresh: checked
                                    })}
                                  />
                                  <Tooltip title="自动刷新处理进度，无需手动操作">
                                    <QuestionCircleOutlined style={{ color: '#999' }} />
                                  </Tooltip>
                                </Space>
                              </div>
                              <div>
                                <Space>
                                  <Text>优先使用MarkItDown：</Text>
                                  <Switch
                                    checked={userPreferences.preferMarkitdown}
                                    onChange={(checked) => saveUserPreferences({
                                      ...userPreferences,
                                      preferMarkitdown: checked
                                    })}
                                  />
                                  <Tooltip title="PDF转换时优先使用MarkItDown引擎">
                                    <QuestionCircleOutlined style={{ color: '#999' }} />
                                  </Tooltip>
                                </Space>
                              </div>
                            </Space>
                          </Card>
                        </Col>
                      </Row>

                      <Card size="small" title="当前设置" style={{ marginTop: 16 }}>
                        <Row gutter={16}>
                          <Col span={8}>
                            <Tag color={userPreferences.enableNotifications ? 'green' : 'default'}>
                              通知: {userPreferences.enableNotifications ? '启用' : '禁用'}
                            </Tag>
                          </Col>
                          <Col span={8}>
                            <Tag color={userPreferences.compactView ? 'green' : 'default'}>
                              视图: {userPreferences.compactView ? '紧凑' : '标准'}
                            </Tag>
                          </Col>
                          <Col span={8}>
                            <Tag color={userPreferences.autoRefresh ? 'green' : 'default'}>
                              刷新: {userPreferences.autoRefresh ? '自动' : '手动'}
                            </Tag>
                          </Col>
                        </Row>
                      </Card>
                    </div>
                  )
                }
              ]}
            />
          </div>
        </Modal>
      </Spin>
    </div>
  );
};

export default PDFImportPage;