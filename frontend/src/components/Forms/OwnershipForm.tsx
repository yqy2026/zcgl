/**
 * 权属方表单组件
 */

import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  Button,
  Space,
  Card,
  Row,
  Col,
  Divider,
  Switch,
  Select
} from 'antd';
import { MessageManager } from '@/utils/messageManager';

const { Option } = Select;

import { ownershipService } from '@/services/ownershipService';
import { projectService } from '@/services/projectService';
import type { Ownership, OwnershipCreate, OwnershipUpdate } from '@/types/ownership';
import type { ProjectDropdownOption } from '@/types/project';

interface OwnershipFormValues {
  name: string;
  code?: string;
  short_name?: string;
  is_active?: boolean;
  description?: string;
  related_projects?: string[];
}

interface OwnershipFormProps {
  initialValues?: Ownership | null;
  onSuccess: () => void;
  onCancel: () => void;
}

const OwnershipForm: React.FC<OwnershipFormProps> = ({
  initialValues,
  onSuccess,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [projectOptions, setProjectOptions] = useState<ProjectDropdownOption[]>([]);

  // 加载项目选项
  const loadProjectOptions = async () => {
    try {
      // Loading project options
      const response = await projectService.getProjectOptions(true);
      // Got project options response

      // 确保响应数据是数组
      const projects = Array.isArray(response)
        ? response
        : (typeof response === 'object' && response != null && 'data' in (response as Record<string, unknown>)
            ? Array.isArray((response as Record<string, unknown>).data) ? (response as Record<string, unknown>).data as ProjectDropdownOption[] : []
            : []);

      setProjectOptions(projects as ProjectDropdownOption[]);
    } catch {
      MessageManager.error('加载项目选项失败');
      setProjectOptions([]); // 设置为空数组避免 undefined 错误
    }
  };

  // 设置初始值
  useEffect(() => {
    if (initialValues !== undefined && initialValues !== null) {
      form.setFieldsValue(initialValues);
    } else {
      form.resetFields();
    }
    loadProjectOptions();
  }, [initialValues, form]);

  // 表单验证规则接口
  interface FormValidationRule {
    field?: string
    fullField?: string
    type?: string
    validator?: (rule: FormValidationRule, value: unknown) => Promise<void>
  }

  // 验证名称唯一性
  const validateName = async (_: FormValidationRule, value: string) => {
    if (value == null) return Promise.resolve();

    const isUnique = await ownershipService.validateOwnershipName(
      value,
      initialValues?.id
    );
    if (!isUnique) {
      return Promise.reject('该名称已存在');
    }

    return Promise.resolve();
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields() as OwnershipFormValues;
      setLoading(true);

      if (initialValues !== undefined && initialValues !== null) {
        // 更新权属方
        const updateData: OwnershipUpdate = {
          name: values.name,
          code: values.code,
          short_name: values.short_name,
          is_active: values.is_active
        };

        // Submit update data
        // console.log('提交的更新数据:', updateData);
        // console.log('关联项目数据:', values.related_projects);

        // 先更新基本信息
        await ownershipService.updateOwnership(initialValues.id, updateData);

        // 如果有关联项目数据，则更新关联项目
        if (values.related_projects != null && Array.isArray(values.related_projects)) {
          try {
            await (ownershipService as unknown as { updateOwnershipProjects: (id: string, projects: string[]) => Promise<void> }).updateOwnershipProjects(initialValues.id, values.related_projects);
          } catch {
            MessageManager.warning('基本信息更新成功，但关联项目更新失败');
          }
        }

        MessageManager.success('更新成功');
      } else {
        // 创建权属方 - 编码将由后端自动生成
        const createData: OwnershipCreate = {
          name: values.name,
          code: values.code ?? '',  // 临时设为空字符串，后端会自动生成
          short_name: values.short_name
        };

        await ownershipService.createOwnership(createData);
        MessageManager.success('创建成功');
      }

      onSuccess();
    } catch (error: unknown) {
      const errorMsg = error instanceof Error ? error.message : '操作失败';
      MessageManager.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      initialValues={{
        is_active: true
      }}
    >
      <Card title="基本信息" size="small">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="权属方全称"
              name="name"
              rules={[
                { required: true, message: '请输入权属方全称' },
                { validator: validateName as any }
              ]}
            >
              <Input placeholder="请输入权属方全称" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="权属方简称"
              name="short_name"
            >
              <Input placeholder="请输入权属方简称（可选）" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              label="关联项目"
              name="related_projects"
              help="选择与该权属方关联的项目"
            >
              <Select
                mode="multiple"
                placeholder="请选择关联项目"
                style={{ width: '100%' }}
                showSearch
                filterOption={(input, option) => {
                  if (option?.children == null) return false;
                  const optionText = String(option.children).toLowerCase();
                  return optionText.includes(input.toLowerCase());
                }}
              >
                {(projectOptions.length > 0 ? projectOptions : []).map(project => (
                  <Option key={project.id} value={project.id}>
                    {project.name} ({project.code})
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        {initialValues && (
          <Form.Item
            label="状态"
            name="is_active"
            valuePropName="checked"
          >
            <Switch
              checkedChildren="启用"
              unCheckedChildren="禁用"
            />
          </Form.Item>
        )}
      </Card>

      <Divider />

      <Row>
        <Col span={24} style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={onCancel}>
              取消
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
            >
              {initialValues ? '更新' : '创建'}
            </Button>
          </Space>
        </Col>
      </Row>
    </Form>
  );
};

export default OwnershipForm;
