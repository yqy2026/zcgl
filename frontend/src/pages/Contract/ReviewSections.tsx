import React from 'react';
import { Alert, Col, DatePicker, Form, Input, InputNumber, Row, Select, Space, Switch, Tabs, Tag, Typography } from 'antd';
import type { FormInstance } from 'antd/es/form';

import type {
  AssetMatch,
  CompleteResult,
  ConfirmedContractData,
  OwnershipMatch,
} from '@/services/pdfImportService';
import { ContractStatus, ContractStatusLabels } from '@/types/rentContract';
import type { FormValues, ReviewFieldLabelRenderer } from './useReviewData';
import styles from './ContractImportReview.module.css';

const { TextArea } = Input;
const { Title } = Typography;

type AgencyFeeCalculationBase = NonNullable<
  ConfirmedContractData['agency_detail']
>['fee_calculation_base'];

interface ReviewSectionsProps {
  form: FormInstance<FormValues>;
  result: CompleteResult;
  activeTab: string;
  onTabChange: (key: string) => void;
  currentRevenueMode: ConfirmedContractData['revenue_mode'] | undefined;
  showAdvancedFields: boolean;
  onShowAdvancedFieldsChange: (checked: boolean) => void;
  onValuesChange: (changedValues: Record<string, unknown>) => void;
  renderFieldLabel: ReviewFieldLabelRenderer;
  parseJsonObjectField: (value: string) => ConfirmedContractData['settlement_rule'];
  normalizeAgencyFeeCalculationBase: (
    value: string | undefined
  ) => AgencyFeeCalculationBase | undefined;
}

const ReviewSections: React.FC<ReviewSectionsProps> = ({
  form,
  result,
  activeTab,
  onTabChange,
  currentRevenueMode,
  showAdvancedFields,
  onShowAdvancedFieldsChange,
  onValuesChange,
  renderFieldLabel,
  parseJsonObjectField,
  normalizeAgencyFeeCalculationBase,
}) => {
  const BasicInfoForm = () => (
    <Form form={form} layout="vertical" onValuesChange={onValuesChange}>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label={renderFieldLabel('合同编号', 'contract_number')}
            name="contract_number"
            rules={[{ required: true, message: '请输入合同编号' }]}
          >
            <Input placeholder="请输入合同编号" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label={renderFieldLabel('承租方名称', 'tenant_name')}
            name="tenant_name"
            rules={[{ required: true, message: '请输入承租方名称' }]}
          >
            <Input placeholder="请输入承租方名称" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label={renderFieldLabel('承租方联系方式', 'tenant_contact')}
            name="tenant_contact"
          >
            <Input placeholder="请输入承租方联系方式" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label={renderFieldLabel('合同状态', 'contract_status')} name="contract_status">
            <Select placeholder="请选择合同状态">
              {Object.values(ContractStatus).map(status => (
                <Select.Option key={status} value={status}>
                  {ContractStatusLabels[status]}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );

  const DateAmountForm = () => (
    <Form form={form} layout="vertical" onValuesChange={onValuesChange}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label={renderFieldLabel('签订日期', 'sign_date')} name="sign_date">
            <DatePicker className={styles.fullWidthControl} placeholder="请选择签订日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('开始日期', 'start_date')}
            name="start_date"
            rules={[{ required: true, message: '请选择开始日期' }]}
          >
            <DatePicker className={styles.fullWidthControl} placeholder="请选择开始日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('结束日期', 'end_date')}
            name="end_date"
            rules={[{ required: true, message: '请选择结束日期' }]}
          >
            <DatePicker className={styles.fullWidthControl} placeholder="请选择结束日期" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label={renderFieldLabel('租赁面积(㎡)', 'rentable_area')} name="rentable_area">
            <InputNumber
              className={styles.fullWidthControl}
              placeholder="请输入租赁面积"
              min={0}
              precision={2}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label={renderFieldLabel('月租金(元)', 'monthly_rent')}
            name="monthly_rent"
            rules={[{ required: true, message: '请输入月租金' }]}
          >
            <InputNumber
              className={styles.fullWidthControl}
              placeholder="请输入月租金"
              min={0}
              precision={2}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label={renderFieldLabel('押金(元)', 'total_deposit')} name="total_deposit">
            <InputNumber
              className={styles.fullWidthControl}
              placeholder="请输入押金金额"
              min={0}
              precision={2}
              defaultValue={0}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );

  const MatchingForm = () => (
    <div>
      <div className={styles.matchingSection}>
        <Title level={5}>
          资产匹配
          {result.matching_result.matched_assets.length > 0 && (
            <Tag color="green" className={styles.matchCountTag}>
              找到 {result.matching_result.matched_assets.length} 个匹配项
            </Tag>
          )}
        </Title>

        {result.matching_result.matched_assets.length > 0 ? (
          <Form.Item label="选择资产" name="asset_id">
            <Select
              placeholder="请选择匹配的资产"
              showSearch
              filterOption={(input, option) =>
                String(option?.children || '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {result.matching_result.matched_assets.map((asset: AssetMatch) => (
                <Select.Option key={asset.id} value={asset.id}>
                  <div>
                    <Space>
                      <span>{asset.asset_name}</span>
                      <Tag
                        color={
                          asset.similarity >= 80
                            ? 'green'
                            : asset.similarity >= 60
                              ? 'orange'
                              : 'red'
                        }
                      >
                        相似度: {asset.similarity}%
                      </Tag>
                    </Space>
                    <div className={styles.matchAddressText}>{asset.address}</div>
                  </div>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <>
            <Alert
              title="未找到匹配的资产"
              description="资产关联保持可选；如需要，请手动填写资产 ID。"
              type="warning"
              showIcon
            />
            <Form.Item label="资产 ID（可选）" name="asset_id">
              <Input placeholder="请输入资产 ID" />
            </Form.Item>
          </>
        )}
      </div>

      <div>
        <Title level={5}>
          产权方主体匹配
          {result.matching_result.matched_ownerships.length > 0 && (
            <Tag color="green" className={styles.matchCountTag}>
              找到 {result.matching_result.matched_ownerships.length} 个匹配项
            </Tag>
          )}
        </Title>

        {result.matching_result.matched_ownerships.length > 0 ? (
          <Form.Item
            label="选择产权方主体"
            name="owner_party_id"
            rules={[{ required: true, message: '请选择关联的产权方主体' }]}
          >
            <Select
              placeholder="请选择匹配的产权方主体"
              showSearch
              filterOption={(input, option) =>
                String(option?.children || '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {result.matching_result.matched_ownerships.map((ownership: OwnershipMatch) => (
                <Select.Option key={ownership.id} value={ownership.id}>
                  <Space>
                    <span>{ownership.ownership_name}</span>
                    <Tag
                      color={
                        ownership.similarity >= 80
                          ? 'green'
                          : ownership.similarity >= 60
                            ? 'orange'
                            : 'red'
                      }
                    >
                      相似度: {ownership.similarity}%
                    </Tag>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        ) : (
          <>
            <Alert
              title="未找到匹配的产权方主体"
              description="新合同导入仍要求显式 owner_party_id，请手动填写。"
              type="warning"
              showIcon
            />
            <Form.Item
              label="产权方主体 ID"
              name="owner_party_id"
              rules={[{ required: true, message: '请输入产权方主体 ID' }]}
            >
              <Input placeholder="请输入产权方主体 ID" />
            </Form.Item>
          </>
        )}
      </div>
    </div>
  );

  const AdvancedForm = () => (
    <Form form={form} layout="vertical" onValuesChange={onValuesChange}>
      <Form.Item label={renderFieldLabel('支付条款', 'payment_terms')} name="payment_terms">
        <TextArea rows={3} placeholder="请输入支付条款" />
      </Form.Item>

      <Form.Item label={renderFieldLabel('合同备注', 'contract_notes')} name="contract_notes">
        <TextArea rows={3} placeholder="请输入合同备注" />
      </Form.Item>
    </Form>
  );

  const ContractContextForm = () => (
    <Form form={form} layout="vertical" onValuesChange={onValuesChange}>
      <Alert
        type="info"
        showIcon
        className={styles.messageAlert}
        title="新合同导入采用 fail-closed 模式，必须显式提供合同组与主体上下文。"
      />

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="经营模式"
            name="revenue_mode"
            rules={[{ required: true, message: '请选择经营模式' }]}
            extra="请输入 LEASE 或 AGENCY"
          >
            <Input placeholder="LEASE / AGENCY" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="合同方向"
            name="contract_direction"
            rules={[{ required: true, message: '请选择合同方向' }]}
            extra="请输入 LESSOR 或 LESSEE"
          >
            <Input placeholder="LESSOR / LESSEE" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="合同角色"
            name="group_relation_type"
            rules={[{ required: true, message: '请选择合同角色' }]}
            extra="请输入 UPSTREAM / DOWNSTREAM / ENTRUSTED / DIRECT_LEASE"
          >
            <Input placeholder="UPSTREAM / DOWNSTREAM / ENTRUSTED / DIRECT_LEASE" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="运营方主体 ID"
            name="operator_party_id"
            rules={[{ required: true, message: '请输入运营方主体 ID' }]}
          >
            <Input placeholder="请输入运营方主体 ID" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="出租方/委托方主体 ID"
            name="lessor_party_id"
            rules={[{ required: true, message: '请输入出租方/委托方主体 ID' }]}
          >
            <Input placeholder="请输入出租方/委托方主体 ID" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="承租方/受托方主体 ID"
            name="lessee_party_id"
            rules={[{ required: true, message: '请输入承租方/受托方主体 ID' }]}
          >
            <Input placeholder="请输入承租方/受托方主体 ID" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="结算规则 JSON"
        name="settlement_rule_json"
        rules={[
          { required: true, message: '请输入结算规则 JSON' },
          {
            validator: async (_, value: string | undefined) => {
              try {
                parseJsonObjectField(value ?? '');
              } catch (error) {
                throw new Error(error instanceof Error ? error.message : '结算规则必须是合法 JSON');
              }
            },
          },
        ]}
      >
        <TextArea
          rows={6}
          placeholder='{"version":"v1","cycle":"月付","settlement_mode":"manual","amount_rule":{},"payment_rule":{}}'
        />
      </Form.Item>

      {currentRevenueMode === 'AGENCY' && (
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              label="服务费比例"
              name="service_fee_ratio"
              rules={[
                { required: true, message: '请输入服务费比例' },
                {
                  validator: async (_, value: string | undefined) => {
                    const normalized = value?.trim() ?? '';
                    const numericValue = Number(normalized);
                    if (
                      normalized === '' ||
                      Number.isNaN(numericValue) ||
                      numericValue < 0 ||
                      numericValue > 1
                    ) {
                      throw new Error('服务费比例必须是 0 到 1 之间的小数');
                    }
                  },
                },
              ]}
            >
              <Input placeholder="例如 0.08" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              label="计费基数"
              name="fee_calculation_base"
              rules={[
                { required: true, message: '请输入计费基数' },
                {
                  validator: async (_, value: string | undefined) => {
                    if (normalizeAgencyFeeCalculationBase(value) == null) {
                      throw new Error('计费基数必须是 actual_received 或 due_amount');
                    }
                  },
                },
              ]}
              extra="请输入 actual_received 或 due_amount"
            >
              <Input placeholder="actual_received / due_amount" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="代理范围说明" name="agency_scope">
              <Input placeholder="请输入代理范围说明" />
            </Form.Item>
          </Col>
        </Row>
      )}
    </Form>
  );

  const tabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: <BasicInfoForm />,
    },
    {
      key: 'dates',
      label: '日期和金额',
      children: <DateAmountForm />,
    },
    {
      key: 'matching',
      label: '数据匹配',
      children: <MatchingForm />,
    },
    {
      key: 'contract-context',
      label: '新体系上下文',
      children: <ContractContextForm />,
    },
    {
      key: 'advanced',
      label: `高级字段${showAdvancedFields ? '' : ' (展开)'}`,
      children: (
        <>
          <div className={styles.advancedSwitchRow}>
            <Switch
              checked={showAdvancedFields}
              onChange={onShowAdvancedFieldsChange}
              checkedChildren="显示高级字段"
              unCheckedChildren="隐藏高级字段"
            />
          </div>
          {showAdvancedFields && <AdvancedForm />}
        </>
      ),
    },
  ];

  return <Tabs activeKey={activeTab} onChange={onTabChange} items={tabItems} />;
};

export default ReviewSections;
