/**
 * Property Certificate Import Page
 * 产权证导入页面
 */

import { useState } from 'react';
import { Row, Col, Steps, message, Card } from 'antd';
import { useNavigate } from 'react-router-dom';
import { PropertyCertificateUpload } from '@/components/PropertyCertificate/PropertyCertificateUpload';
import { PropertyCertificateReview } from '@/components/PropertyCertificate/PropertyCertificateReview';
import { PROPERTY_CERTIFICATE_ROUTES } from '@/constants/routes';
import { propertyCertificateService } from '@/services/propertyCertificateService';
import PageContainer from '@/components/Common/PageContainer';
import type {
  CertificateExtractionResult,
  CertificateImportConfirm,
} from '@/types/propertyCertificate';
import styles from './PropertyCertificateImport.module.css';

export const PropertyCertificateImport: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [extractionResult, setExtractionResult] = useState<CertificateExtractionResult | null>(
    null
  );
  const [loading, setLoading] = useState(false);

  const handleUploadSuccess = (result: CertificateExtractionResult) => {
    setExtractionResult(result);
    setCurrentStep(1);
  };

  const handleConfirm = async (data: CertificateImportConfirm) => {
    setLoading(true);
    try {
      const response = await propertyCertificateService.confirmImport(data);
      message.success(`产权证创建成功！ID: ${response.certificate_id}`);
      setCurrentStep(2);
      window.setTimeout(() => {
        navigate(PROPERTY_CERTIFICATE_ROUTES.LIST);
      }, 800);
    } catch {
      message.error('创建失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer
      title="产权证导入"
      subTitle="上传扫描件并审核抽取结果后创建产权证"
      className={styles.importPage}
    >
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <Card className={styles.stepsCard}>
            <Steps
              current={currentStep}
              className={styles.importSteps}
              items={[
                { title: '上传文件', content: '上传产权证扫描件' },
                { title: '审核确认', content: '确认提取的信息' },
                { title: '完成', content: '产权证已创建' },
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
    </PageContainer>
  );
};

export default PropertyCertificateImport;
