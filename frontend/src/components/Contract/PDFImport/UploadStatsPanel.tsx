/**
 * 上传统计面板组件
 */

import React from 'react';
import { Row, Col, Statistic } from 'antd';
import { usePDFImportContext } from './PDFImportContext';

const UploadStatsPanel: React.FC = () => {
  const { uploadStats } = usePDFImportContext();

  if (!uploadStats) {
    return null;
  }

  return (
    <Row gutter={16} style={{ marginTop: 16 }}>
      <Col span={8}>
        <Statistic title="上传速度" value={uploadStats.uploadSpeed} suffix="KB/s" precision={1} />
      </Col>
      <Col span={8}>
        <Statistic title="预估时间" value={uploadStats.estimatedTime} suffix="秒" />
      </Col>
      <Col span={8}>
        <Statistic
          title="推荐方法"
          value={uploadStats.fileAnalysis.recommendedMethod}
          styles={{ content: { fontSize: 14 } }}
        />
      </Col>
    </Row>
  );
};

export default UploadStatsPanel;
