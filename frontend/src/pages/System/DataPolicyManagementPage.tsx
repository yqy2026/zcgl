import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Empty,
  Input,
  Row,
  Space,
  Tag,
  Typography,
} from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PageContainer } from '@/components/Common';
import { dataPolicyService } from '@/services/dataPolicyService';
import { MessageManager } from '@/utils/messageManager';
import type { DataPolicyPackageCode } from '@/types/dataPolicy';

interface UpdateRolePoliciesVariables {
  roleId: string;
  policyPackages: DataPolicyPackageCode[];
}

const DataPolicyManagementPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [roleIdInput, setRoleIdInput] = useState('');
  const [activeRoleId, setActiveRoleId] = useState<string | null>(null);
  const [selectedPackages, setSelectedPackages] = useState<DataPolicyPackageCode[]>([]);

  const templatesQuery = useQuery({
    queryKey: ['data-policy-templates'],
    queryFn: () => dataPolicyService.getDataPolicyTemplates(),
    staleTime: 5 * 60 * 1000,
  });

  const rolePoliciesQuery = useQuery({
    queryKey: ['role-data-policies', activeRoleId],
    queryFn: async () => {
      if (activeRoleId == null || activeRoleId.trim() === '') {
        throw new Error('缺少角色 ID');
      }
      return dataPolicyService.getRoleDataPolicies(activeRoleId);
    },
    enabled: activeRoleId != null && activeRoleId.trim() !== '',
  });

  useEffect(() => {
    const policyPackages = rolePoliciesQuery.data?.policy_packages;
    if (policyPackages != null) {
      setSelectedPackages(policyPackages);
    }
  }, [rolePoliciesQuery.data?.policy_packages]);

  const hasActiveRole = activeRoleId != null && activeRoleId.trim() !== '';
  const isCurrentRolePoliciesLoaded =
    hasActiveRole &&
    rolePoliciesQuery.isSuccess &&
    rolePoliciesQuery.data?.role_id === activeRoleId;

  const updateMutation = useMutation({
    mutationFn: async (variables: UpdateRolePoliciesVariables) => {
      if (variables.roleId.trim() === '') {
        throw new Error('请先选择角色 ID');
      }

      if (!isCurrentRolePoliciesLoaded) {
        throw new Error('请先成功加载当前角色策略后再保存');
      }

      return dataPolicyService.updateRoleDataPolicies(variables.roleId, {
        policy_packages: variables.policyPackages,
      });
    },
    onSuccess: (data, variables) => {
      MessageManager.success('策略包配置已保存');
      const responseRoleId = data.role_id.trim() !== '' ? data.role_id : variables.roleId;
      queryClient.setQueryData(['role-data-policies', responseRoleId], data);
    },
    onError: error => {
      const message = error instanceof Error ? error.message : '保存失败';
      MessageManager.error(message);
    },
  });

  const templateOptions = useMemo(() => {
    return (templatesQuery.data ?? []).map(template => ({
      label: (
        <Space orientation="vertical" size={0}>
          <Typography.Text>{template.name}</Typography.Text>
          <Typography.Text type="secondary">{template.description}</Typography.Text>
        </Space>
      ),
      value: template.code,
    }));
  }, [templatesQuery.data]);

  const handleLoadRolePolicies = () => {
    const normalizedRoleId = roleIdInput.trim();
    if (normalizedRoleId === '') {
      return;
    }

    if (normalizedRoleId !== roleIdInput) {
      setRoleIdInput(normalizedRoleId);
    }

    if (activeRoleId === normalizedRoleId) {
      void rolePoliciesQuery.refetch();
      return;
    }

    setSelectedPackages([]);
    setActiveRoleId(normalizedRoleId);
  };

  return (
    <PageContainer title="数据策略包管理" subTitle="按角色配置 ABAC 数据策略包（policy_packages）">
      <Space orientation="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <Typography.Text strong>角色选择</Typography.Text>
            <Row gutter={12}>
              <Col flex="auto">
                <Input
                  placeholder="请输入角色 ID（role_id）"
                  value={roleIdInput}
                  onChange={event => setRoleIdInput(event.target.value)}
                  onPressEnter={() => {
                    handleLoadRolePolicies();
                  }}
                />
              </Col>
              <Col>
                <Button
                  type="primary"
                  onClick={() => {
                    handleLoadRolePolicies();
                  }}
                  disabled={roleIdInput.trim() === ''}
                >
                  加载当前策略
                </Button>
              </Col>
            </Row>
            {activeRoleId != null && activeRoleId.trim() !== '' ? (
              <Typography.Text type="secondary">当前角色：{activeRoleId}</Typography.Text>
            ) : null}
          </Space>
        </Card>

        <Card
          title="策略包模板"
          extra={
            <Button
              type="primary"
              onClick={() => {
                if (activeRoleId == null || activeRoleId.trim() === '') {
                  return;
                }

                void updateMutation.mutateAsync({
                  roleId: activeRoleId,
                  policyPackages: selectedPackages,
                });
              }}
              loading={updateMutation.isPending}
              disabled={!isCurrentRolePoliciesLoaded}
            >
              保存配置
            </Button>
          }
        >
          {templatesQuery.isLoading ? <Typography.Text>加载中...</Typography.Text> : null}
          {templatesQuery.isError ? (
            <Alert
              type="error"
              showIcon
              title={
                templatesQuery.error instanceof Error ? templatesQuery.error.message : '加载失败'
              }
            />
          ) : null}
          {!templatesQuery.isLoading &&
          !templatesQuery.isError &&
          (templateOptions.length ?? 0) > 0 ? (
            <Checkbox.Group
              style={{ width: '100%' }}
              value={selectedPackages}
              onChange={values => {
                setSelectedPackages(values as DataPolicyPackageCode[]);
              }}
            >
              <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
                {templateOptions.map(option => (
                  <Checkbox key={option.value} value={option.value}>
                    {option.label}
                  </Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          ) : null}
          {!templatesQuery.isLoading &&
          !templatesQuery.isError &&
          (templateOptions.length ?? 0) === 0 ? (
            <Empty description="暂无可用模板" />
          ) : null}
        </Card>

        <Card title="当前绑定结果">
          {rolePoliciesQuery.isLoading ? <Typography.Text>加载中...</Typography.Text> : null}
          {rolePoliciesQuery.isError ? (
            <Alert
              type="error"
              showIcon
              title={
                rolePoliciesQuery.error instanceof Error
                  ? rolePoliciesQuery.error.message
                  : '加载失败'
              }
            />
          ) : null}
          {!rolePoliciesQuery.isLoading && !rolePoliciesQuery.isError ? (
            <Space wrap>
              {(selectedPackages.length ?? 0) > 0 ? (
                selectedPackages.map(code => <Tag key={code}>{code}</Tag>)
              ) : (
                <Typography.Text type="secondary">当前角色暂无绑定策略包</Typography.Text>
              )}
            </Space>
          ) : null}
        </Card>
      </Space>
    </PageContainer>
  );
};

export default DataPolicyManagementPage;
