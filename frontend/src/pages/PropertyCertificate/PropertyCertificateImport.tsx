/**
 * Property Certificate Import Page
 * 产权证导入页面
 */

import { useState } from 'react';
import { Row, Col, Steps, message, Card } from 'antd';
import { PropertyCertificateUpload } from '@/components/PropertyCertificate/PropertyCertificateUpload';
import { PropertyCertificateReview } from '@/components/PropertyCertificate/PropertyCertificateReview';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import type { CertificateExtractionResult } from '@/types/propertyCertificate';

export const PropertyCertificateImport: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [extractionResult, setExtractionResult] = useState<CertificateExtractionResult | null>(
    null
  );
  const [loading, setLoading] = useState(false);

  const handleUploadSuccess = (result: CertificateExtractionResult) => {
    setExtractionResult(result);
    setCurrentStep(1);
  };

  const handleConfirm = async (data: any) => {
    setLoading(true);
    try {
      const response = await propertyCertificateService.confirmImport(data);
      message.success(`产权证创建成功！ID: ${response.certificate_id}`);
      // Navigate to list page
      window.location.href = '/property-certificates';
    } catch {
      message.error('创建失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <Card>
            <Steps
              current={currentStep}
              items={[
                { title: '上传文件', description: '上传产权证扫描件' },
                { title: '审核确认', description: '确认提取的信息' },
                { title: '完成', description: '产权证已创建' },
              ]}
            />
          </Card>
        </Col>

        <Col span={24}>
          {currentStep === 0 && (
            <PropertyCertificateUpload onSuccess={handleUploadSuccess} loading={loading} />
          )}

          {currentStep === 1 && extractionResult && (
            <PropertyCertificateReview
              extractionResult={extractionResult}
              onConfirm={handleConfirm}
              loading={loading}
            />
          )}
        </Col>
      </Row>
    </div>
  );
};

export default PropertyCertificateImport;
