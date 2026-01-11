/**
 * PDF导入功能帮助指引组件
 * 提供使用说明、常见问题解答和最佳实践
 */

import React, { useState } from 'react';
import {
  Card,
  Collapse,
  Typography,
  Space,
  Tag,
  Alert,
  Steps,
  Row,
  Col,
  Button,
  Modal,
  Table,
  Divider,
} from 'antd';
import {
  QuestionCircleOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  BookOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  EyeOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { COLORS } from '@/styles/colorMap';

const { Title, Text } = Typography;
const { Panel } = Collapse;
const { Step } = Steps;

interface PDFImportHelpProps {
  visible: boolean;
  onClose: () => void;
}

const PDFImportHelp: React.FC<PDFImportHelpProps> = ({ visible, onClose }) => {
  const [activeTab, setActiveTab] = useState<'guide' | 'faq' | 'best' | 'fields'>('guide');

  // 常见问题数据
  const faqData = [
    {
      key: '1',
      question: '支持哪些PDF格式？',
      answer:
        '支持标准PDF格式（.pdf），包括文本型PDF和扫描型PDF。文本型PDF提取效果更好，扫描型PDF会使用OCR技术进行识别。',
    },
    {
      key: '2',
      question: '文件大小有限制吗？',
      answer: '单个PDF文件大小不能超过50MB。如果文件过大，建议压缩分割后再上传。',
    },
    {
      key: '3',
      question: '能提取哪些信息？',
      answer:
        '系统可以提取58个关键字段，包括合同编号、承租方、出租方、物业地址、租赁面积、租金、租期等完整的合同信息。',
    },
    {
      key: '4',
      question: '提取准确率如何？',
      answer:
        '对于标准格式的文本型PDF，准确率可达95%以上。扫描型PDF的准确率取决于扫描质量，通常在80-90%之间。',
    },
    {
      key: '5',
      question: '处理需要多长时间？',
      answer: '一般情况下，处理时间为30-60秒，具体取决于文件大小和复杂度。',
    },
    {
      key: '6',
      question: '可以修改提取的信息吗？',
      answer: '当然可以！在确认阶段，您可以查看和编辑所有提取的字段，确保数据准确性。',
    },
    {
      key: '7',
      question: '如何处理重复合同？',
      answer: '系统会自动检测重复合同，并在确认阶段提醒您。您可以选择跳过重复合同或创建新记录。',
    },
    {
      key: '8',
      question: '如果处理失败了怎么办？',
      answer: '系统会显示具体的错误信息。您可以根据提示修改文件或调整参数后重试。',
    },
  ];

  // 最佳实践数据
  const bestPractices = [
    {
      icon: <FileTextOutlined />,
      title: '文件准备',
      description: '确保PDF文件清晰可读，避免模糊、倾斜或缺失内容',
      tips: [
        '使用清晰扫描的PDF文件',
        '确保文字没有被遮挡或裁切',
        '避免水印干扰关键信息',
        '检查文件完整性',
      ],
    },
    {
      icon: <DatabaseOutlined />,
      title: '信息完整性',
      description: '确保合同包含完整的必要信息字段',
      tips: [
        '合同编号清晰可见',
        '承租方和出租方信息完整',
        '物业地址准确详细',
        '租赁面积和租金明确',
        '租期起止日期清楚',
      ],
    },
    {
      icon: <EyeOutlined />,
      title: '结果确认',
      description: '仔细核对提取结果，必要时进行手动调整',
      tips: [
        '逐个检查关键字段',
        '特别注意金额和日期',
        '验证匹配的资产信息',
        '确认权属关系正确',
        '保存前再次审核',
      ],
    },
    {
      icon: <SettingOutlined />,
      title: '系统优化',
      description: '合理使用系统功能提高处理效率',
      tips: [
        '定期清理历史会话',
        '关注系统状态提示',
        '及时更新资产信息',
        '维护标准合同模板',
        '反馈处理问题',
      ],
    },
  ];

  // 关键字段列表
  const keyFields = [
    { category: '基本信息', fields: ['合同编号', '物业名称', '物业地址', '权属状态', '物业性质'] },
    {
      category: '面积信息',
      fields: ['土地面积', '实际面积', '可出租面积', '已出租面积', '未出租面积'],
    },
    {
      category: '租赁信息',
      fields: ['承租方', '承租方类型', '租赁合同号', '合同开始日期', '合同结束日期'],
    },
    { category: '财务信息', fields: ['月租金', '押金', '年收入', '年支出', '净收入'] },
    { category: '管理信息', fields: ['商业模式', '运营状态', '管理人', '数据状态', '版本'] },
  ];

  // 使用步骤
  const usageSteps = [
    {
      title: '准备文件',
      description: '确保PDF合同文件完整清晰',
      icon: <FileTextOutlined />,
    },
    {
      title: '上传文件',
      description: '拖拽或点击上传PDF文件',
      icon: <DatabaseOutlined />,
    },
    {
      title: '等待处理',
      description: '系统自动转换和提取信息',
      icon: <VideoCameraOutlined />,
    },
    {
      title: '确认信息',
      description: '核对并编辑提取的字段',
      icon: <EyeOutlined />,
    },
    {
      title: '完成导入',
      description: '确认后导入系统',
      icon: <CheckCircleOutlined />,
    },
  ];

  return (
    <Modal
      title="PDF合同智能导入 - 使用帮助"
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" type="primary" onClick={onClose}>
          我知道了
        </Button>,
      ]}
      width={1000}
      style={{ top: 20 }}
    >
      <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
        {/* 快速导航 */}
        <Card style={{ marginBottom: 16 }}>
          <Title level={4}>快速导航</Title>
          <Row gutter={16}>
            <Col span={6}>
              <Button
                type={activeTab === 'guide' ? 'primary' : 'default'}
                block
                icon={<BookOutlined />}
                onClick={() => setActiveTab('guide')}
              >
                使用指南
              </Button>
            </Col>
            <Col span={6}>
              <Button
                type={activeTab === 'faq' ? 'primary' : 'default'}
                block
                icon={<QuestionCircleOutlined />}
                onClick={() => setActiveTab('faq')}
              >
                常见问题
              </Button>
            </Col>
            <Col span={6}>
              <Button
                type={activeTab === 'best' ? 'primary' : 'default'}
                block
                icon={<CheckCircleOutlined />}
                onClick={() => setActiveTab('best')}
              >
                最佳实践
              </Button>
            </Col>
            <Col span={6}>
              <Button
                type={activeTab === 'fields' ? 'primary' : 'default'}
                block
                icon={<DatabaseOutlined />}
                onClick={() => setActiveTab('fields')}
              >
                字段说明
              </Button>
            </Col>
          </Row>
        </Card>

        {/* 使用指南 */}
        {activeTab === 'guide' && (
          <div>
            <Alert
              message="功能特点"
              description="PDF合同智能导入功能可以自动识别和提取合同中的关键信息，大幅提高数据录入效率。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Card title="使用流程" style={{ marginBottom: 16 }}>
              <Steps direction="vertical" current={0}>
                {usageSteps.map((step, index) => (
                  <Step
                    key={index}
                    title={step.title}
                    description={step.description}
                    icon={step.icon}
                    status={index === 0 ? 'process' : 'wait'}
                  />
                ))}
              </Steps>
            </Card>

            <Card title="详细步骤说明">
              <Collapse>
                <Panel header="步骤1: 准备文件" key="1">
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Text>
                      <strong>文件要求：</strong>
                    </Text>
                    <ul>
                      <li>格式：PDF（.pdf）</li>
                      <li>大小：不超过50MB</li>
                      <li>内容：清晰的合同文本</li>
                      <li>语言：中文（支持简体中文）</li>
                    </ul>
                    <Text>
                      <strong>注意事项：</strong>
                    </Text>
                    <ul>
                      <li>避免模糊不清的扫描件</li>
                      <li>确保文字没有被遮挡</li>
                      <li>检查文件完整性</li>
                    </ul>
                  </Space>
                </Panel>
                <Panel header="步骤2: 上传文件" key="2">
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Text>
                      <strong>上传方式：</strong>
                    </Text>
                    <ul>
                      <li>拖拽文件到上传区域</li>
                      <li>点击上传区域选择文件</li>
                    </ul>
                    <Text>
                      <strong>上传提示：</strong>
                    </Text>
                    <ul>
                      <li>系统会自动验证文件格式和大小</li>
                      <li>上传成功后会显示处理进度</li>
                      <li>可以随时取消上传</li>
                    </ul>
                  </Space>
                </Panel>
                <Panel header="步骤3: 等待处理" key="3">
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Text>
                      <strong>处理过程：</strong>
                    </Text>
                    <ul>
                      <li>PDF转换为Markdown格式</li>
                      <li>智能提取合同信息</li>
                      <li>验证数据完整性</li>
                      <li>匹配现有资产数据</li>
                    </ul>
                    <Text>
                      <strong>状态监控：</strong>
                    </Text>
                    <ul>
                      <li>实时显示处理进度</li>
                      <li>显示当前处理步骤</li>
                      <li>遇到错误会及时提示</li>
                    </ul>
                  </Space>
                </Panel>
                <Panel header="步骤4: 确认信息" key="4">
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Text>
                      <strong>确认内容：</strong>
                    </Text>
                    <ul>
                      <li>分页显示提取的字段</li>
                      <li>高亮显示可疑数据</li>
                      <li>支持在线编辑修改</li>
                      <li>显示匹配建议</li>
                    </ul>
                    <Text>
                      <strong>操作建议：</strong>
                    </Text>
                    <ul>
                      <li>仔细核对关键字段</li>
                      <li>特别注意金额和日期</li>
                      <li>确认匹配关系正确</li>
                    </ul>
                  </Space>
                </Panel>
                <Panel header="步骤5: 完成导入" key="5">
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Text>
                      <strong>导入确认：</strong>
                    </Text>
                    <ul>
                      <li>最终确认所有数据</li>
                      <li>系统会进行最终验证</li>
                      <li>成功导入到数据库</li>
                      <li>生成完整的审计记录</li>
                    </ul>
                    <Text>
                      <strong>后续操作：</strong>
                    </Text>
                    <ul>
                      <li>查看导入结果</li>
                      <li>处理历史记录</li>
                      <li>继续导入其他合同</li>
                    </ul>
                  </Space>
                </Panel>
              </Collapse>
            </Card>
          </div>
        )}

        {/* 常见问题 */}
        {activeTab === 'faq' && (
          <Card>
            <Collapse>
              {faqData.map(faq => (
                <Panel header={faq.question} key={faq.key}>
                  <Text>{faq.answer}</Text>
                </Panel>
              ))}
            </Collapse>
          </Card>
        )}

        {/* 最佳实践 */}
        {activeTab === 'best' && (
          <div>
            <Alert
              message="最佳实践建议"
              description="遵循以下建议可以获得更好的处理效果和用户体验。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Row gutter={16}>
              {bestPractices.map((practice, index) => (
                <Col span={12} key={index}>
                  <Card style={{ height: '100%', marginBottom: 16 }}>
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 32, color: COLORS.primary }}>{practice.icon}</div>
                        <Title level={4} style={{ margin: 0 }}>
                          {practice.title}
                        </Title>
                        <Text type="secondary">{practice.description}</Text>
                      </div>
                      <div>
                        <Text strong>建议要点：</Text>
                        <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                          {practice.tips.map((tip, tipIndex) => (
                            <li key={tipIndex} style={{ marginBottom: 4 }}>
                              <Text style={{ fontSize: 14 }}>{tip}</Text>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        )}

        {/* 字段说明 */}
        {activeTab === 'fields' && (
          <div>
            <Alert
              message="58个关键字段说明"
              description="系统会自动提取以下58个关键字段，覆盖合同的完整信息。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Row gutter={16}>
              <Col span={12}>
                <Card title="字段分类统计" style={{ marginBottom: 16 }}>
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    {keyFields.map((category, index) => (
                      <div key={index}>
                        <Text strong>{category.category}：</Text>
                        <div style={{ marginTop: 4 }}>
                          {category.fields.map((field, fieldIndex) => (
                            <Tag key={fieldIndex} color="blue" style={{ marginBottom: 4 }}>
                              {field}
                            </Tag>
                          ))}
                        </div>
                      </div>
                    ))}
                  </Space>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="提取准确率说明" style={{ marginBottom: 16 }}>
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <div>
                      <Text strong>高准确率字段 (&gt;90%)：</Text>
                      <div style={{ marginTop: 4 }}>
                        <Tag color="green">合同编号</Tag>
                        <Tag color="green">物业名称</Tag>
                        <Tag color="green">物业地址</Tag>
                        <Tag color="green">承租方</Tag>
                        <Tag color="green">月租金</Tag>
                      </div>
                    </div>
                    <div>
                      <Text strong>中等准确率字段 (70-90%)：</Text>
                      <div style={{ marginTop: 4 }}>
                        <Tag color="orange">面积信息</Tag>
                        <Tag color="orange">租期日期</Tag>
                        <Tag color="orange">押金</Tag>
                        <Tag color="orange">联系人</Tag>
                      </div>
                    </div>
                    <div>
                      <Text strong>需要人工确认字段：</Text>
                      <div style={{ marginTop: 4 }}>
                        <Tag color="red">权属状态</Tag>
                        <Tag color="red">物业性质</Tag>
                        <Tag color="red">商业模式</Tag>
                        <Tag color="red">运营状态</Tag>
                      </div>
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>

            <Card title="字段详情">
              <Table
                dataSource={[
                  {
                    field: '合同编号',
                    type: '文本',
                    required: true,
                    description: '租赁合同的唯一标识编号',
                  },
                  {
                    field: '物业名称',
                    type: '文本',
                    required: true,
                    description: '租赁物业的名称',
                  },
                  {
                    field: '物业地址',
                    type: '文本',
                    required: true,
                    description: '租赁物业的详细地址',
                  },
                  { field: '承租方', type: '文本', required: true, description: '租赁方的名称' },
                  { field: '月租金', type: '数字', required: true, description: '每月租金金额' },
                  {
                    field: '租赁面积',
                    type: '数字',
                    required: false,
                    description: '租赁的实际面积',
                  },
                  {
                    field: '合同开始日期',
                    type: '日期',
                    required: true,
                    description: '租赁期开始日期',
                  },
                  {
                    field: '合同结束日期',
                    type: '日期',
                    required: true,
                    description: '租赁期结束日期',
                  },
                ]}
                columns={[
                  {
                    title: '字段名称',
                    dataIndex: 'field',
                    key: 'field',
                    width: 120,
                  },
                  {
                    title: '数据类型',
                    dataIndex: 'type',
                    key: 'type',
                    width: 80,
                    render: (type: string) => (
                      <Tag color={type === '文本' ? 'blue' : type === '数字' ? 'green' : 'orange'}>
                        {type}
                      </Tag>
                    ),
                  },
                  {
                    title: '必填',
                    dataIndex: 'required',
                    key: 'required',
                    width: 60,
                    render: (required: boolean) => (
                      <Tag color={required ? 'red' : 'default'}>{required ? '是' : '否'}</Tag>
                    ),
                  },
                  {
                    title: '说明',
                    dataIndex: 'description',
                    key: 'description',
                  },
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          </div>
        )}

        {/* 联系支持 */}
        <Divider />
        <Card>
          <Row justify="space-between" align="middle">
            <Col>
              <Text type="secondary">如果您需要更多帮助或有其他问题，请联系技术支持。</Text>
            </Col>
            <Col>
              <Space>
                <Button icon={<InfoCircleOutlined />}>查看更多文档</Button>
                <Button type="primary" icon={<VideoCameraOutlined />}>
                  观看操作视频
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>
      </div>
    </Modal>
  );
};

export default PDFImportHelp;
