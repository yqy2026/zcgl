/**
 * 处理步骤显示组件
 */

import React from 'react';
import { Steps, Progress, Typography } from 'antd';
import { usePDFImportContext } from './PDFImportContext';
import styles from './ProcessingStepsDisplay.module.css';

const ProcessingStepsDisplay: React.FC = () => {
  const { uploading, uploadProgress, processingProgress, processingSteps, getStepIcon } =
    usePDFImportContext();

  if (processingSteps.length === 0 || (!uploading && !processingProgress)) {
    return null;
  }

  return (
    <div className={styles.stepsContainer}>
      <Steps
        size="small"
        current={processingSteps.findIndex(s => s.status === 'process')}
        items={processingSteps.map(step => ({
          title: step.title,
          description: step.description,
          status: ((): 'wait' | 'process' | 'finish' | 'error' => {
            switch (step.status) {
              case 'wait':
                return 'wait';
              case 'process':
              case 'uploading':
                return 'process';
              case 'finish':
              case 'completed':
                return 'finish';
              case 'error':
              case 'failed':
                return 'error';
              default:
                return 'process';
            }
          })(),
          icon: getStepIcon(step),
        }))}
      />

      {(uploading || processingProgress) && (
        <div className={styles.progressSection}>
          <Progress
            percent={uploading ? uploadProgress : (processingProgress?.progress ?? 0)}
            status={processingProgress?.status === 'failed' ? 'exception' : undefined}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />

          {processingProgress && (
            <div className={styles.progressMetaRow}>
              <Typography.Text type="secondary">
                {processingProgress.current_step || '准备中...'}
              </Typography.Text>
              <Typography.Text type="secondary">
                {processingProgress.progress ?? 0}%
              </Typography.Text>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ProcessingStepsDisplay;
