/**
 * 权属方管理简化页面（用于测试）
 */

import React from 'react';
import { Card, Button, Table, Tag, Space, Modal, Form, Input, Select, message, Row, Col, Typography } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';

const { Option } = Select;
const { Title } = Typography;

// 模拟数据
const mockOwnerships = [
  {
    id: '1',
    name: 'XX集团',
    code: 'XXJT',
    contact_person: '张三',
    contact_phone: '13800138000',
    is_active: true,
    created_at: '2024-01-01',
  },
  {
    id: '2',
    name: 'YY公司',
    code: 'YYGS',
    contact_person: '李四',
    contact_phone: '13900139000',
    is_active: true,
    created_at: '2024-01-02',
  }
];

const OwnershipSimplePage: React.FC = () => {
  const [ownerships, setOwnerships] = React.useState(mockOwnerships);
  const [modalVisible, setModalVisible] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [form] = Form.useForm();

  const columns = [
    {
      title: '权属方名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: any) => (
        <div>
          <div style={{ fontWeight: 500, color: '#1890ff' }}>{text}</div>
          {record.short_name && (
            <div style={{ fontSize: '12px', color: '#999' }}>
              {record.short_name}
            </div>
          )}
        </div>
      ),
    },
    {
      title: '简称',
      dataIndex: 'short_name',
      key: 'short_name',
      width: 120,
      render: (short_name: string) => short_name || '-',
    },
    {
      title: '编码',
      dataIndex: 'code',
      key: 'code',
      width: 100,
      render: (code: string) => (
        <Tag color="blue">{code}</Tag>
      ),
    },
    {
      title: '联系人',
      dataIndex: 'contact_person',
      key: 'contact_person',
    },
    {
      title: '联系电话',
      dataIndex: 'contact_phone',
      key: 'contact_phone',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (record: any) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            icon={<DeleteOutlined />}
            danger
            size="small"
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const handleEdit = (record: any) => {
    setEditingId(record.id);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = (record: any) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除权属方"${record.name}"吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        setOwnerships(ownerships.filter(item => item.id !== record.id));
        message.success('删除成功');
      },
    });
  };

  const handleAdd = () => {
    setEditingId(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();

      if (editingId) {
        // 编辑模式
        setOwnerships(ownerships.map(item =>
          item.id === editingId ? { ...item, ...values } : item
        ));
        message.success('编辑成功');
      } else {
        // 新增模式
        // 自动生成编码
        const generateCode = (name: string) => {
          // 去除空格，提取首字母
          const cleanName = name.replace(/\s+/g, '');
          if (cleanName.length >= 2) {
            return cleanName.substring(0, 2).toUpperCase();
          }
          return cleanName.toUpperCase();
        };

        const newOwnership = {
          ...values,
          code: generateCode(values.name),
          id: Date.now().toString(),
          created_at: new Date().toISOString().split('T')[0],
        };
        setOwnerships([...ownerships, newOwnership]);
        message.success('添加成功');
      }

      setModalVisible(false);
      setEditingId(null);
      form.resetFields();
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>权属方管理</Title>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              新增权属方
            </Button>
          </Col>
        </Row>
      </div>

      {/* 权属方列表 */}
      <Table
        columns={columns}
        dataSource={ownerships}
        rowKey="id"
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条记录`,
        }}
      />

      {/* 新增/编辑弹窗 */}
      <Modal
        title={editingId ? "编辑权属方" : "新增权属方"}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => {
          setModalVisible(false);
          setEditingId(null);
          form.resetFields();
        }}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="权属方名称"
            name="name"
            rules={[{ required: true, message: '请输入权属方名称' }]}
          >
            <Input placeholder="请输入权属方名称" />
          </Form.Item>

          <Form.Item
            label="权属方简称"
            name="short_name"
          >
            <Input placeholder="请输入权属方简称（可选）" />
          </Form.Item>

          <Form.Item
            label="联系人"
            name="contact_person"
          >
            <Input placeholder="请输入联系人" />
          </Form.Item>

          <Form.Item
            label="联系电话"
            name="contact_phone"
          >
            <Input placeholder="请输入联系电话" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default OwnershipSimplePage;