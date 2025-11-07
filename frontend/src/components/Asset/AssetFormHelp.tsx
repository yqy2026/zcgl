import React, { useState } from 'react'
import { Collapse, Typography, Tag, Space, Button, Modal } from 'antd'
import {
  QuestionCircleOutlined,
  InfoCircleOutlined,
  BulbOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'

const { Panel: CollapsePanel } = Collapse
const { Text, Paragraph } = Typography

interface AssetFormHelpProps {
  visible?: boolean
  onClose?: () => void
}

const AssetFormHelp: React.FC<AssetFormHelpProps> = ({
  visible = false,
  onClose,
}) => {
  const helpSections = [
    {
      key: 'basic',
      title: '基本信息填写指南',
      icon: <InfoCircleOutlined />,
      content: (
        <div>
          <Paragraph>
            <Text strong>物业名称：</Text>
            请填写完整的物业名称，建议包含楼栋号或具体位置信息。
          </Paragraph>
          <Paragraph>
            <Text strong>权属方：</Text>
            填写物业的法定所有者，通常是公司或机构名称。
          </Paragraph>
          <Paragraph>
            <Text strong>经营管理方：</Text>
            如果物业委托给第三方管理，请填写管理公司名称。
          </Paragraph>
          <Paragraph>
            <Text strong>所在地址：</Text>
            请填写详细地址，包括省市区街道门牌号。
          </Paragraph>
        </div>
      ),
    },
    {
      key: 'area',
      title: '面积信息填写说明',
      icon: <BulbOutlined />,
      content: (
        <div>
          <Paragraph>
            <Text strong>面积单位：</Text>
            所有面积字段单位均为平方米（㎡）。
          </Paragraph>
          <Paragraph>
            <Text strong>面积关系：</Text>
            <ul>
              <li>实际房产面积 ≥ 可出租面积</li>
              <li>可出租面积 = 已出租面积 + 未出租面积</li>
              <li>系统会自动计算出租率和未出租面积</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>特殊说明：</Text>
            <Tag color="blue">经营类物业</Tag> 需要填写出租相关面积，
            <Tag color="green">非经营类物业</Tag> 主要填写非经营物业面积。
          </Paragraph>
        </div>
      ),
    },
    {
      key: 'status',
      title: '状态信息选择指南',
      icon: <CheckCircleOutlined />,
      content: (
        <div>
          <Paragraph>
            <Text strong>确权状态：</Text>
            <ul>
              <li><Tag color="green">已确权</Tag>：已完成产权登记</li>
              <li><Tag color="red">未确权</Tag>：尚未完成产权登记</li>
              <li><Tag color="orange">部分确权</Tag>：部分完成产权登记</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>物业性质：</Text>
            <ul>
              <li><Tag color="blue">经营类</Tag>：用于商业经营的物业</li>
              <li><Tag color="default">非经营类</Tag>：非商业用途的物业</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>使用状态：</Text>
            <ul>
              <li><Tag color="green">出租</Tag>：已出租给第三方使用</li>
              <li><Tag color="red">闲置</Tag>：暂时未使用</li>
              <li><Tag color="blue">自用</Tag>：自己使用</li>
              <li><Tag color="purple">公房</Tag>：公共用房</li>
              <li><Tag color="default">其他</Tag>：其他特殊情况</li>
            </ul>
          </Paragraph>
        </div>
      ),
    },
    {
      key: 'dynamic',
      title: '动态字段显示规则',
      icon: <QuestionCircleOutlined />,
      content: (
        <div>
          <Paragraph>
            系统会根据您的选择自动显示或隐藏相关字段：
          </Paragraph>
          <Paragraph>
            <Text strong>经营类物业：</Text>
            显示可出租面积、已出租面积、未出租面积、出租率等字段。
          </Paragraph>
          <Paragraph>
            <Text strong>非经营类物业：</Text>
            显示非经营物业面积字段。
          </Paragraph>
          <Paragraph>
            <Text strong>出租状态：</Text>
            显示租户名称、合同信息、合同日期等字段。
          </Paragraph>
          <Paragraph>
            <Text strong>有业态类别：</Text>
            显示接收模式字段。
          </Paragraph>
          <Paragraph>
            <Text strong>有五羊项目：</Text>
            显示接收协议开始和结束日期字段。
          </Paragraph>
        </div>
      ),
    },
    {
      key: 'validation',
      title: '数据验证规则',
      icon: <InfoCircleOutlined />,
      content: (
        <div>
          <Paragraph>
            <Text strong>必填字段：</Text>
            物业名称、权属方、所在地址、确权状态、物业性质、使用状态。
          </Paragraph>
          <Paragraph>
            <Text strong>面积验证：</Text>
            <ul>
              <li>所有面积必须为非负数</li>
              <li>已出租面积不能大于可出租面积</li>
              <li>未出租面积不能大于可出租面积</li>
              <li>已出租面积 + 未出租面积应等于可出租面积</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>日期验证：</Text>
            合同结束日期必须晚于开始日期，接收协议结束日期必须晚于开始日期。
          </Paragraph>
          <Paragraph>
            <Text strong>字符限制：</Text>
            各字段都有相应的字符长度限制，请注意输入框下方的提示。
          </Paragraph>
        </div>
      ),
    },
    {
      key: 'tips',
      title: '填写技巧和建议',
      icon: <BulbOutlined />,
      content: (
        <div>
          <Paragraph>
            <Text strong>提高效率：</Text>
            <ul>
              <li>先填写基本信息和状态信息，系统会自动显示相关字段</li>
              <li>使用Tab键快速切换字段</li>
              <li>面积字段支持千分位显示，便于阅读</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>数据准确性：</Text>
            <ul>
              <li>建议参考产权证书填写面积信息</li>
              <li>合同信息建议参考实际签署的合同</li>
              <li>定期更新出租状态和面积信息</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>表单完成度：</Text>
            页面顶部的进度条显示表单完成度，建议达到80%以上以确保数据完整性。
          </Paragraph>
        </div>
      ),
    },
  ]

  return (
    <Modal
      title="资产表单填写帮助"
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" type="primary" onClick={onClose}>
          我知道了
        </Button>,
      ]}
      width={800}
      style={{ top: 20 }}
    >
      <Collapse
        defaultActiveKey={['basic']}
        ghost
        expandIconPosition="start"
      >
        {helpSections.map((section) => (
          <Panel
            header={
              <Space>
                {section.icon}
                <Text strong>{section.title}</Text>
              </Space>
            }
            key={section.key}
          >
            {section.content}
          </Panel>
        ))}
      </Collapse>
    </Modal>
  )
}

// 帮助按钮组件
export const AssetFormHelpButton: React.FC = () => {
  const [helpVisible, setHelpVisible] = useState(false)

  return (
    <>
      <Button
        type="text"
        icon={<QuestionCircleOutlined />}
        onClick={() => setHelpVisible(true)}
        style={{ color: '#1890ff' }}
      >
        填写帮助
      </Button>
      
      <AssetFormHelp
        visible={helpVisible}
        onClose={() => setHelpVisible(false)}
      />
    </>
  )
}

export default AssetFormHelp