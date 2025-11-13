/**
 * 租户合同创建/编辑表单组件
 */

import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  InputNumber,
  DatePicker,
  Button,
  Space,
  Card,
  Row,
  Col,
  Divider,
  Typography,
  message,
  Modal,
  Table,
  Tooltip,
  Tag,
  Popconfirm
} from 'antd';
import {
  SaveOutlined,
  PlusOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
  CalendarOutlined,
  DollarOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import type { ColumnsType } from 'antd/es/table';

import { RentContractCreate, RentTermCreate } from '../../types/rentContract';
import { Asset } from '../../types/asset';
import { Ownership } from '../../types/ownership';
import { assetService } from '../../services/assetService';
import { ownershipService } from '../../services/ownershipService';

// 租金条款接口（用于编辑时）
interface RentTermData {
  start_date: string;
  end_date: string;
  monthly_rent: number;
  rent_description?: string;
  management_fee?: number;
  other_fees?: number;
}

// 租赁合同表单初始数据接口
interface RentContractInitialData {
  contract_number?: string;
  asset_id: string;
  ownership_id: string;
  tenant_name: string;
  tenant_contact?: string;
  tenant_phone?: string;
  tenant_address?: string;
  sign_date?: string;
  start_date: string;
  end_date: string;
  total_deposit?: number;
  monthly_rent_base?: number;
  contract_status?: string;
  payment_terms?: string;
  contract_notes?: string;
  rent_terms?: RentTermData[];
}

const { Option } = Select;
const { TextArea } = Input;
const { Title, Text } = Typography;

interface RentContractFormProps {
  initialData?: RentContractInitialData;
  onSubmit: (data: RentContractCreate) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  mode?: 'create' | 'edit';
}

interface RentTermFormData {
  key: string;
  start_date: Dayjs;
  end_date: Dayjs;
  monthly_rent: number;
  rent_description?: string;
  management_fee?: number;
  other_fees?: number;
}

const RentContractForm: React.FC<RentContractFormProps> = ({
  initialData,
  onSubmit,
  onCancel,
  loading = false,
  mode = 'create'
}) => {
  const [form] = Form.useForm();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [ownerships, setOwnerships] = useState<Ownership[]>([]);
  const [rentTerms, setRentTerms] = useState<RentTermFormData[]>([]);
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [loadingOwnerships, setLoadingOwnerships] = useState(false);
  const [showRentTermModal, setShowRentTermModal] = useState(false);
  const [editingTerm, setEditingTerm] = useState<RentTermFormData | null>(null);
  const [termForm] = Form.useForm();

  // 加载资产和权属方数据
  useEffect(() => {
    loadAssets();
    loadOwnerships();
  }, []);

  // 初始化表单数据
  useEffect(() => {
    if (initialData && mode === 'edit') {
      const formData = {
        ...initialData,
        sign_date: initialData.sign_date ? dayjs(initialData.sign_date) : undefined,
        start_date: initialData.start_date ? dayjs(initialData.start_date) : undefined,
        end_date: initialData.end_date ? dayjs(initialData.end_date) : undefined,
      };
      form.setFieldsValue(formData);
      
      if (initialData.rent_terms) {
        const terms = initialData.rent_terms.map((term: RentTermData, index: number) => ({
          key: `term-${index}`,
          start_date: dayjs(term.start_date),
          end_date: dayjs(term.end_date),
          monthly_rent: term.monthly_rent,
          rent_description: term.rent_description,
          management_fee: term.management_fee || 0,
          other_fees: term.other_fees || 0,
        }));
        setRentTerms(terms);
      }
    }
  }, [initialData, mode, form]);

  const loadAssets = async () => {
    setLoadingAssets(true);
    try {
      const response = await assetService.getAssets({ limit: 100 });
      setAssets(response.items);
    } catch (error) {
      message.error('加载资产列表失败');
    } finally {
      setLoadingAssets(false);
    }
  };

  const loadOwnerships = async () => {
    setLoadingOwnerships(true);
    try {
      const response = await ownershipService.getOwnerships({ size: 100 });
      setOwnerships(response.items);
    } catch (error) {
      message.error('加载权属方列表失败');
    } finally {
      setLoadingOwnerships(false);
    }
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (rentTerms.length === 0) {
        message.error('请至少添加一个租金条款');
        return;
      }

      // 转换租金条款数据
      const rent_terms: RentTermCreate[] = rentTerms.map(term => ({
        start_date: term.start_date.format('YYYY-MM-DD'),
        end_date: term.end_date.format('YYYY-MM-DD'),
        monthly_rent: term.monthly_rent,
        rent_description: term.rent_description,
        management_fee: term.management_fee || 0,
        other_fees: term.other_fees || 0,
        total_monthly_amount: term.monthly_rent + (term.management_fee || 0) + (term.other_fees || 0),
      }));

      const contractData: RentContractCreate = {
        contract_number: values.contract_number,
        asset_id: values.asset_id,
        ownership_id: values.ownership_id,
        tenant_name: values.tenant_name,
        tenant_contact: values.tenant_contact,
        tenant_phone: values.tenant_phone,
        tenant_address: values.tenant_address,
        sign_date: values.sign_date.format('YYYY-MM-DD'),
        start_date: values.start_date.format('YYYY-MM-DD'),
        end_date: values.end_date.format('YYYY-MM-DD'),
        total_deposit: values.total_deposit || 0,
        monthly_rent_base: values.monthly_rent_base,
        contract_status: values.contract_status || '有效',
        payment_terms: values.payment_terms,
        contract_notes: values.contract_notes,
        rent_terms,
      };

      await onSubmit(contractData);
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };

  // 添加租金条款
  const handleAddRentTerm = () => {
    setEditingTerm(null);
    termForm.resetFields();
    setShowRentTermModal(true);
  };

  // 编辑租金条款
  const handleEditRentTerm = (term: RentTermFormData) => {
    setEditingTerm(term);
    termForm.setFieldsValue(term);
    setShowRentTermModal(true);
  };

  // 删除租金条款
  const handleDeleteRentTerm = (key: string) => {
    setRentTerms(prev => prev.filter(term => term.key !== key));
  };

  // 保存租金条款
  const handleSaveRentTerm = async () => {
    try {
      const values = await termForm.validateFields();
      const termData: RentTermFormData = {
        key: editingTerm ? editingTerm.key : `term-${Date.now()}`,
        start_date: values.start_date,
        end_date: values.end_date,
        monthly_rent: values.monthly_rent,
        rent_description: values.rent_description,
        management_fee: values.management_fee || 0,
        other_fees: values.other_fees || 0,
      };

      if (editingTerm) {
        // 编辑现有条款
        setRentTerms(prev => prev.map(term => 
          term.key === editingTerm.key ? termData : term
        ));
      } else {
        // 添加新条款
        setRentTerms(prev => [...prev, termData]);
      }

      setShowRentTermModal(false);
      termForm.resetFields();
    } catch (error) {
      console.error('租金条款验证失败:', error);
    }
  };

  // 租金条款表格列定义
  const rentTermColumns: ColumnsType<RentTermFormData> = [
    {
      title: '开始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      render: (date: Dayjs) => date.format('YYYY-MM-DD'),
      width: 120,
    },
    {
      title: '结束日期',
      dataIndex: 'end_date',
      key: 'end_date',
      render: (date: Dayjs) => date.format('YYYY-MM-DD'),
      width: 120,
    },
    {
      title: '月租金',
      dataIndex: 'monthly_rent',
      key: 'monthly_rent',
      render: (amount: number) => `¥${amount.toLocaleString()}`,
      width: 120,
    },
    {
      title: '管理费',
      dataIndex: 'management_fee',
      key: 'management_fee',
      render: (amount: number) => `¥${(amount || 0).toLocaleString()}`,
      width: 100,
    },
    {
      title: '其他费用',
      dataIndex: 'other_fees',
      key: 'other_fees',
      render: (amount: number) => `¥${(amount || 0).toLocaleString()}`,
      width: 100,
    },
    {
      title: '月应收总额',
      key: 'total_amount',
      render: (record: RentTermFormData) => {
        const total = record.monthly_rent + (record.management_fee || 0) + (record.other_fees || 0);
        return `¥${total.toLocaleString()}`;
      },
      width: 120,
    },
    {
      title: '说明',
      dataIndex: 'rent_description',
      key: 'rent_description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (record: RentTermFormData) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => handleEditRentTerm(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="确实要删除这个租金条款吗？"
            onConfirm={() => handleDeleteRentTerm(record.key)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          contract_status: '有效',
        }}
      >
        {/* 基本信息 */}
        <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="合同编号"
                name="contract_number"
                tooltip="留空将自动生成"
              >
                <Input placeholder="留空将自动生成" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="签订日期"
                name="sign_date"
                rules={[{ required: true, message: '请选择签订日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="合同状态"
                name="contract_status"
                rules={[{ required: true, message: '请选择合同状态' }]}
              >
                <Select>
                  <Option value="有效">有效</Option>
                  <Option value="到期">到期</Option>
                  <Option value="终止">终止</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 关联信息 */}
        <Card title="关联信息" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="关联资产"
                name="asset_id"
                rules={[{ required: true, message: '请选择关联资产' }]}
              >
                <Select
                  showSearch
                  placeholder="选择资产"
                  loading={loadingAssets}
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {(assets || []).map(asset => (
                    <Option key={asset.id} value={asset.id}>
                      {asset.property_name} - {asset.address}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="权属方"
                name="ownership_id"
                rules={[{ required: true, message: '请选择权属方' }]}
              >
                <Select
                  showSearch
                  placeholder="选择权属方"
                  loading={loadingOwnerships}
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {(ownerships || []).map(ownership => (
                    <Option key={ownership.id} value={ownership.id}>
                      {ownership.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 承租方信息 */}
        <Card title="承租方信息" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="承租方名称"
                name="tenant_name"
                rules={[{ required: true, message: '请输入承租方名称' }]}
              >
                <Input placeholder="请输入承租方名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="联系人"
                name="tenant_contact"
              >
                <Input placeholder="请输入联系人姓名" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="联系电话"
                name="tenant_phone"
              >
                <Input placeholder="请输入联系电话" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="联系地址"
                name="tenant_address"
              >
                <Input placeholder="请输入联系地址" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 合同期限 */}
        <Card title="合同期限" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="开始日期"
                name="start_date"
                rules={[{ required: true, message: '请选择开始日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="结束日期"
                name="end_date"
                rules={[{ required: true, message: '请选择结束日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="押金总额"
                name="total_deposit"
                tooltip="单位：元"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="请输入押金总额"
                  min={0}
                  precision={2}
                  formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value!.replace(/\¥\s?|(,*)/g, '')}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 租金条款 */}
        <Card 
          title="租金条款" 
          size="small" 
          style={{ marginBottom: 16 }}
          extra={
            <Button
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              onClick={handleAddRentTerm}
            >
              添加条款
            </Button>
          }
        >
          <Table
            columns={rentTermColumns}
            dataSource={rentTerms}
            pagination={false}
            size="small"
            locale={{ emptyText: '暂无租金条款，请点击"添加条款"按钮添加' }}
          />
        </Card>

        {/* 其他信息 */}
        <Card title="其他信息" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="基础月租金"
                name="monthly_rent_base"
                tooltip="用于快速参考，实际租金以租金条款为准"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="请输入基础月租金"
                  min={0}
                  precision={2}
                  formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value!.replace(/\¥\s?|(,*)/g, '')}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="付款条款"
                name="payment_terms"
              >
                <Input placeholder="例如：每月1日前支付" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                label="合同备注"
                name="contract_notes"
              >
                <TextArea
                  rows={3}
                  placeholder="请输入合同相关备注信息"
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 操作按钮 */}
        <div style={{ textAlign: 'right', marginTop: 24 }}>
          <Space>
            <Button onClick={onCancel}>
              取消
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              icon={<SaveOutlined />}
            >
              {mode === 'create' ? '创建合同' : '更新合同'}
            </Button>
          </Space>
        </div>
      </Form>

      {/* 租金条款编辑模态框 */}
      <Modal
        title={editingTerm ? '编辑租金条款' : '添加租金条款'}
        open={showRentTermModal}
        onCancel={() => setShowRentTermModal(false)}
        onOk={handleSaveRentTerm}
        width={600}
      >
        <Form
          form={termForm}
          layout="vertical"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="开始日期"
                name="start_date"
                rules={[{ required: true, message: '请选择开始日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="结束日期"
                name="end_date"
                rules={[{ required: true, message: '请选择结束日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="月租金"
                name="monthly_rent"
                rules={[{ required: true, message: '请输入月租金' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="请输入月租金"
                  min={0}
                  precision={2}
                  formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value!.replace(/\¥\s?|(,*)/g, '')}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="管理费"
                name="management_fee"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="请输入管理费"
                  min={0}
                  precision={2}
                  formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value!.replace(/\¥\s?|(,*)/g, '')}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="其他费用"
                name="other_fees"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="请输入其他费用"
                  min={0}
                  precision={2}
                  formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value!.replace(/\¥\s?|(,*)/g, '')}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label="条款说明"
            name="rent_description"
          >
            <TextArea
              rows={2}
              placeholder="请输入该租金条款的说明信息"
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default RentContractForm;