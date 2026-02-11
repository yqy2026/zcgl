import React from 'react';
import { Skeleton, Card, Row, Col } from 'antd';
import styles from './SkeletonLoader.module.css';

interface SkeletonLoaderProps {
  type?: 'list' | 'card' | 'form' | 'table' | 'chart' | 'detail';
  rows?: number;
  loading?: boolean;
  children?: React.ReactNode;
}

const INPUT_ROW_STYLE = { width: '100%', height: 32 } as const;
const CARD_SPACING_STYLE = { width: 200, height: 24 } as const;
const TABLE_HEADER_INPUT_STYLE = { width: '80%', height: 20 } as const;

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  type = 'list',
  rows = 3,
  loading = true,
  children,
}) => {
  if (loading === false && children !== null && children !== undefined) {
    return <>{children}</>;
  }

  const renderSkeleton = () => {
    switch (type) {
      case 'list':
        return (
          <div className={styles.sectionGroup}>
            {Array.from({ length: rows }).map((_, index) => (
              <Card key={`skeleton-list-${index}`} className={styles.sectionCard}>
                <Skeleton avatar paragraph={{ rows: 2 }} active />
              </Card>
            ))}
          </div>
        );

      case 'card':
        return (
          <Row gutter={16}>
            {Array.from({ length: rows }).map((_, index) => (
              <Col xs={24} sm={12} md={8} lg={6} key={`skeleton-card-${index}`}>
                <Card className={styles.sectionCard}>
                  <Skeleton paragraph={{ rows: 3 }} active />
                </Card>
              </Col>
            ))}
          </Row>
        );

      case 'form':
        return (
          <Card>
            <div className={styles.sectionBlockLg}>
              <Skeleton.Input style={{ width: 200, height: 32 }} active />
            </div>
            {Array.from({ length: rows }).map((_, index) => (
              <Row key={`skeleton-form-${index}`} gutter={16} className={styles.sectionBlockLg}>
                <Col span={6}>
                  <Skeleton.Input style={INPUT_ROW_STYLE} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={INPUT_ROW_STYLE} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={INPUT_ROW_STYLE} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={INPUT_ROW_STYLE} active />
                </Col>
              </Row>
            ))}
            <div className={styles.formActions}>
              <Skeleton.Button style={{ width: 100, height: 32 }} active />
              <Skeleton.Button style={{ width: 80, height: 32 }} className={styles.formActionSecondary} active />
            </div>
          </Card>
        );

      case 'table':
        return (
          <Card>
            <div className={styles.sectionBlockMd}>
              <Row gutter={16}>
                <Col span={6}>
                  <Skeleton.Input style={INPUT_ROW_STYLE} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={INPUT_ROW_STYLE} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Input style={INPUT_ROW_STYLE} active />
                </Col>
                <Col span={6}>
                  <Skeleton.Button style={{ width: 80, height: 32 }} active />
                </Col>
              </Row>
            </div>

            {/* 表头 */}
            <Row gutter={16} className={styles.tableHeaderRow}>
              {Array.from({ length: 6 }).map((_, index) => (
                <Col span={4} key={`skeleton-header-${index}`}>
                  <Skeleton.Input style={TABLE_HEADER_INPUT_STYLE} active />
                </Col>
              ))}
            </Row>

            {/* 表格行 */}
            {Array.from({ length: rows }).map((_, rowIndex) => (
              <Row key={`skeleton-row-${rowIndex}`} gutter={16} className={styles.tableDataRow}>
                {Array.from({ length: 6 }).map((_, colIndex) => (
                  <Col span={4} key={`skeleton-cell-${rowIndex}-${colIndex}`}>
                    <Skeleton.Input
                      style={{
                        width: colIndex === 0 ? '60%' : '80%',
                        height: 16,
                      }}
                      active
                    />
                  </Col>
                ))}
              </Row>
            ))}

            {/* 分页 */}
            <div className={styles.tablePagination}>
              <Skeleton.Button style={{ width: 200, height: 32 }} active />
            </div>
          </Card>
        );

      case 'chart':
        return (
          <Card>
            <div className={styles.sectionBlockMd}>
              <Skeleton.Input style={CARD_SPACING_STYLE} active />
            </div>

            {/* 统计卡片 */}
            <Row gutter={16} className={styles.sectionBlockLg}>
              {Array.from({ length: 4 }).map((_, index) => (
                <Col span={6} key={`skeleton-stat-${index}`}>
                  <Card size="small">
                    <Skeleton paragraph={{ rows: 1 }} title={{ width: '60%' }} active />
                  </Card>
                </Col>
              ))}
            </Row>

            {/* 图表区域 */}
            <div className={styles.chartArea}>
              <Skeleton.Node style={{ width: 200, height: 200 }} className={styles.chartNode} active>
                <div className={styles.chartCircle} />
              </Skeleton.Node>
            </div>
          </Card>
        );

      case 'detail':
        return (
          <div className={styles.sectionGroup}>
            {/* 头部信息 */}
            <Card className={styles.sectionCard}>
              <div className={styles.detailHeader}>
                <Skeleton.Avatar size={64} active />
                <div className={styles.detailHeaderMeta}>
                  <Skeleton.Input style={{ width: 300, height: 24, marginBottom: 8 }} active />
                  <Skeleton.Input style={{ width: 200, height: 16 }} active />
                </div>
                <div className={styles.detailHeaderActions}>
                  <Skeleton.Button style={{ width: 80, height: 32 }} active />
                  <Skeleton.Button style={{ width: 80, height: 32 }} active />
                </div>
              </div>
            </Card>

            {/* 详细信息 */}
            <Row gutter={16}>
              <Col span={16}>
                <Card title={<Skeleton.Input style={{ width: 120, height: 20 }} active />}>
                  {Array.from({ length: rows }).map((_, index) => (
                    <Row key={`skeleton-detail-${index}`} gutter={16} className={styles.sectionBlockMd}>
                      <Col span={8}>
                        <Skeleton.Input style={{ width: '100%', height: 16 }} active />
                      </Col>
                      <Col span={16}>
                        <Skeleton.Input style={{ width: '80%', height: 16 }} active />
                      </Col>
                    </Row>
                  ))}
                </Card>
              </Col>

              <Col span={8}>
                <Card title={<Skeleton.Input style={{ width: 100, height: 20 }} active />}>
                  {Array.from({ length: 3 }).map((_, index) => (
                    <div key={`skeleton-side-${index}`} className={styles.sectionBlockMd}>
                      <Skeleton paragraph={{ rows: 1 }} title={{ width: '70%' }} active />
                    </div>
                  ))}
                </Card>
              </Col>
            </Row>
          </div>
        );

      default:
        return <Skeleton paragraph={{ rows }} active />;
    }
  };

  return <div>{renderSkeleton()}</div>;
};

export default SkeletonLoader;
