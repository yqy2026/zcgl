/**
 * 高级选项面板组件
 */

import React from 'react';
import { Card, Row, Col, Space, Switch, Typography } from 'antd';
import { usePDFImportContext } from './PDFImportContext';

const AdvancedOptionsPanel: React.FC = () => {
    const { showAdvancedOptions, processingOptions, setProcessingOptions } = usePDFImportContext();

    if (!showAdvancedOptions) {
        return null;
    }

    return (
        <Card
            size="small"
            title="处理选项"
            style={{ marginTop: 16 }}
            extra={
                <Space>
                    <Switch
                        checked={processingOptions.prefer_ocr}
                        onChange={(checked) => setProcessingOptions(prev => ({ ...prev, prefer_ocr: checked }))}
                        checkedChildren="OCR"
                        unCheckedChildren="文本"
                    />
                    <Switch
                        checked={processingOptions.enable_chinese_optimization}
                        onChange={(checked) => setProcessingOptions(prev => ({ ...prev, enable_chinese_optimization: checked }))}
                        checkedChildren="中文优化"
                    />
                </Space>
            }
        >
            <Row gutter={16}>
                <Col span={12}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <div>
                            <Typography.Text strong>置信度阈值</Typography.Text>
                            <input
                                type="range"
                                min="0.1"
                                max="1.0"
                                step="0.1"
                                value={processingOptions.confidence_threshold}
                                onChange={(e) => setProcessingOptions(prev => ({ ...prev, confidence_threshold: parseFloat(e.target.value) }))}
                                style={{ width: '100%' }}
                            />
                            <Typography.Text type="secondary">{processingOptions.confidence_threshold}</Typography.Text>
                        </div>
                    </Space>
                </Col>
                <Col span={12}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <Switch
                            checked={processingOptions.enable_multi_engine_fusion}
                            onChange={(checked) => setProcessingOptions(prev => ({ ...prev, enable_multi_engine_fusion: checked }))}
                            checkedChildren="多引擎融合"
                        />
                        <Switch
                            checked={processingOptions.enable_semantic_validation}
                            onChange={(checked) => setProcessingOptions(prev => ({ ...prev, enable_semantic_validation: checked }))}
                            checkedChildren="语义验证"
                        />
                    </Space>
                </Col>
            </Row>
        </Card>
    );
};

export default AdvancedOptionsPanel;
