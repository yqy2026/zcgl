/**
 * 处理步骤显示组件
 */

import React from 'react';
import { Steps, Progress, Typography } from 'antd';
import { usePDFImportContext } from './PDFImportContext';

const ProcessingStepsDisplay: React.FC = () => {
    const {
        uploading,
        uploadProgress,
        processingProgress,
        processingSteps,
        getStepIcon
    } = usePDFImportContext();

    if (processingSteps.length === 0 || (!uploading && !processingProgress)) {
        return null;
    }

    return (
        <div style={{ marginBottom: 24 }}>
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
                    icon: getStepIcon(step)
                }))}
            />

            {(uploading || processingProgress) && (
                <div style={{ marginTop: 16 }}>
                    <Progress
                        percent={uploading ? uploadProgress : (processingProgress?.progress !== null && processingProgress?.progress !== undefined) ? processingProgress.progress : 0}
                        status={processingProgress?.status === 'failed' ? 'exception' : undefined}
                        strokeColor={{
                            '0%': '#108ee9',
                            '100%': '#87d068',
                        }}
                    />

                    {processingProgress && (
                        <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                            <Typography.Text type="secondary">
                                {processingProgress.current_step || '准备中...'}
                            </Typography.Text>
                            <Typography.Text type="secondary">
                                {processingProgress.progress || 0}%
                            </Typography.Text>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ProcessingStepsDisplay;
