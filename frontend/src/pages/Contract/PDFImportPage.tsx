/**
 * PDF导入主页面 (重构版)
 *
 * 整合上传、状态查看、结果确认等所有功能
 * 重构后: 从860行缩减到~150行,通过组合子组件实现
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Tabs, Spin } from 'antd';
import styles from './PDFImportPage.module.css';

import ContractImportUpload from './ContractImportUpload';
import ContractImportStatus from './ContractImportStatus';
import ContractImportReview from './ContractImportReview';
import PDFImportHelp from './PDFImportHelp';

import { PDFImportHeader } from './components/PDFImportHeader';
import { SessionHistoryTab } from './components/SessionHistoryTab';
import { ImportStatusStates } from './components/ImportStatusStates';
import { usePDFImportSession } from '@/hooks/usePDFImportSession';

const PDFImportPage: React.FC = () => {
  // 使用自定义hook管理会话状态
  const session = usePDFImportSession();

  // UI状态(仅页面级UI状态)
  const [activeTab, setActiveTab] = useState<'upload' | 'history'>('upload');
  const [showHelp, setShowHelp] = useState(false);

  // 初始化:加载历史记录
  useEffect(() => {
    void session.loadSessionHistory();
  }, []);

  // 渲染当前会话(根据状态切换)
  const renderCurrentSession = useMemo(() => {
    if (session.currentSession == null) {
      return (
        <ContractImportUpload
          key="upload-main"
          onUploadSuccess={session.handleUploadSuccess}
          onUploadError={session.handleUploadError}
        />
      );
    }

    const keyPrefix = `${session.currentSession.status}-${session.currentSession.sessionId}`;

    switch (session.currentSession.status) {
      case 'processing':
        return (
          <ContractImportStatus
            key={keyPrefix}
            sessionId={session.currentSession.sessionId}
            fileInfo={{
              filename: session.currentSession.fileInfo.name,
              size: session.currentSession.fileInfo.size ?? 0,
              content_type: session.currentSession.fileInfo.type ?? 'application/pdf',
            }}
            onComplete={session.handleProcessingComplete}
            onError={session.handleProcessingError}
            onCancel={session.handleCancel}
          />
        );

      case 'ready':
        return session.currentSession.result != null ? (
          <ContractImportReview
            key={keyPrefix}
            sessionId={session.currentSession.sessionId}
            result={session.currentSession.result}
            onConfirm={session.handleConfirmImport}
            onCancel={session.handleBackToUpload}
            onBack={session.handleBackToUpload}
          />
        ) : null;

      case 'completed':
      case 'failed':
        return (
          <ImportStatusStates
            key={keyPrefix}
            status={session.currentSession.status}
            fileName={session.currentSession.fileInfo.name}
            error={session.currentSession.error}
            onUploadNew={session.handleBackToUpload}
            onViewHistory={() => setActiveTab('history')}
          />
        );

      default:
        return (
          <ContractImportUpload
            key="upload-initial"
            onUploadSuccess={session.handleUploadSuccess}
            onUploadError={session.handleUploadError}
          />
        );
    }
  }, [
    session.currentSession,
    session.handleUploadSuccess,
    session.handleUploadError,
    session.handleProcessingComplete,
    session.handleProcessingError,
    session.handleCancel,
    session.handleConfirmImport,
    session.handleBackToUpload,
    setActiveTab,
  ]);

  // 页面加载状态
  if (session.loading && session.currentSession == null) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <Spin size="large" />
        <span style={{ color: '#999' }}>正在初始化PDF导入系统...</span>
      </div>
    );
  }

  return (
    <div
      className={styles['pdf-import-page']}
      style={{
        animation: 'fadeIn 0.3s ease-in-out',
        minHeight: '100vh',
      }}
    >
      {/* 页面头部 */}
      <PDFImportHeader
        onShowHelp={() => setShowHelp(true)}
        onReload={session.handleReload}
        loading={session.loading}
      />

      {/* 主要内容区域 */}
      <Spin spinning={session.loading} tip="正在加载数据..." size="large" delay={300}>
        <Tabs
          activeKey={activeTab}
          onChange={key => setActiveTab(key as 'upload' | 'history')}
          items={[
            {
              key: 'upload',
              label: 'PDF导入',
              children: <div>{renderCurrentSession}</div>,
            },
            {
              key: 'history',
              label: '处理历史',
              children: (
                <SessionHistoryTab
                  sessionHistory={session.sessionHistory}
                  onSwitchToUpload={() => setActiveTab('upload')}
                />
              ),
            },
          ]}
        />

        {/* 使用帮助模态框 */}
        <PDFImportHelp visible={showHelp} onClose={() => setShowHelp(false)} />
      </Spin>
    </div>
  );
};

export default PDFImportPage;
