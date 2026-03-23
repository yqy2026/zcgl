import React, { useState } from 'react';
import {
  Card,
  Button,
  Space,
  Dropdown,
  Modal,
  Form,
  Select,
  Input,
  Popconfirm,
  Typography,
  Alert,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  DeleteOutlined,
  EditOutlined,
  ExportOutlined,
  DownOutlined,
  TagOutlined,
} from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { Asset, AssetUpdateRequest } from '@/types/asset';
import { assetService } from '@/services/assetService';
import { excelService } from '@/services/excelService';
import styles from './AssetBatchActions.module.css';

const { Option } = Select;
const { TextArea } = Input;
const { Text } = Typography;

interface AssetBatchActionsProps {
  selectedAssets: Asset[];
  selectedRowKeys: string[];
  onClearSelection: () => void;
  onRefresh: () => void;
}

const AssetBatchActions: React.FC<AssetBatchActionsProps> = ({
  selectedRowKeys,
  onClearSelection,
  onRefresh,
}) => {
  const [batchEditVisible, setBatchEditVisible] = useState(false);
  const [exportVisible, setExportVisible] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 批量删除
  const deleteMutation = useMutation({
    mutationFn: (ids: string[]) => assetService.deleteAssets(ids),
    onSuccess: () => {
      MessageManager.success(`成功删除 ${selectedRowKeys.length} 个资产`);
      onClearSelection();
      onRefresh();
      queryClient.invalidateQueries({ queryKey: ['assets-list'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (error: unknown) => {
      MessageManager.error(`批量删除失败: ${error instanceof Error ? error.message : '未知错误'}`);
    },
  });

  // 批量更新
  const updateMutation = useMutation({
    mutationFn: async (data: { ids: string[]; updates: AssetUpdateRequest }) => {
      // 这里需要后端支持批量更新API
      const promises = data.ids.map(id => assetService.updateAsset(id, data.updates));
      return Promise.all(promises);
    },
    onSuccess: () => {
      MessageManager.success(`成功更新 ${selectedRowKeys.length} 个资产`);
      setBatchEditVisible(false);
      form.resetFields();
      onClearSelection();
      onRefresh();
      queryClient.invalidateQueries({ queryKey: ['assets-list'] });
      queryClient.invalidateQueries({ queryKey: ['asset'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
    onError: (error: unknown) => {
      MessageManager.error(`批量更新失败: ${error instanceof Error ? error.message : '未知错误'}`);
    },
  });

  // 批量导出
  const exportMutation = useMutation({
    mutationFn: (ids: string[]) =>
      excelService.exportExcel({
        filters: { ids },
        format: 'xlsx',
        include_headers: true,
      }),
    onSuccess: result => {
      MessageManager.success('导出成功，开始下载...');
      excelService.downloadExportFile(result.file_name);
    },
    onError: (error: unknown) => {
      MessageManager.error(`导出失败: ${error instanceof Error ? error.message : '未知错误'}`);
    },
  });

  // 处理批量删除
  const handleBatchDelete = () => {
    deleteMutation.mutate(selectedRowKeys);
  };

  // 处理批量编辑
  const handleBatchEdit = () => {
    form.validateFields().then(values => {
      // 过滤空值
      const updates = Object.entries(values).reduce<Partial<AssetUpdateRequest>>(
        (acc, [key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            const typedKey = key as keyof AssetUpdateRequest;
            (acc[typedKey] as unknown) = value;
          }
          return acc;
        },
        {} as Partial<AssetUpdateRequest>
      );

      if (Object.keys(updates).length === 0) {
        MessageManager.warning('请至少选择一个字段进行更新');
        return;
      }

      updateMutation.mutate({
        ids: selectedRowKeys,
        updates,
      });
    });
  };

  // 处理批量导出
  const handleBatchExport = () => {
    exportMutation.mutate(selectedRowKeys);
  };

  // 更多操作菜单
  const moreActions = [
    {
      key: 'tag',
      label: '批量标记',
      icon: <TagOutlined />,
      onClick: () => {
        // 实现批量标记功能
        MessageManager.info('批量标记功能开发中...');
      },
    },
    {
      key: 'move',
      label: '批量移动',
      icon: <EditOutlined />,
      onClick: () => {
        // 实现批量移动功能
        MessageManager.info('批量移动功能开发中...');
      },
    },
  ];

  if (selectedRowKeys.length === 0) {
    return null;
  }

  return (
    <>
      <Card size="small" className={styles.batchActionCard}>
        <div className={styles.batchActionHeader}>
          <div>
            <Text strong>已选择 {selectedRowKeys.length} 个资产</Text>
            <Button
              type="link"
              size="small"
              onClick={onClearSelection}
              className={styles.clearSelectionButton}
            >
              清空选择
            </Button>
          </div>

          <Space>
            <Button icon={<EditOutlined />} onClick={() => setBatchEditVisible(true)}>
              批量编辑
            </Button>

            <Button
              icon={<ExportOutlined />}
              onClick={handleBatchExport}
              loading={exportMutation.isPending}
            >
              批量导出
            </Button>

            <Popconfirm
              title={`确定要删除这 ${selectedRowKeys.length} 个资产吗？`}
              description="删除后无法恢复，请谨慎操作"
              onConfirm={handleBatchDelete}
              okText="确定"
              cancelText="取消"
              okType="danger"
            >
              <Button danger icon={<DeleteOutlined />} loading={deleteMutation.isPending}>
                批量删除
              </Button>
            </Popconfirm>

            <Dropdown
              menu={{
                items: moreActions,
                onClick: ({ key }) => {
                  const action = moreActions.find(item => item.key === key);
                  action?.onClick();
                },
              }}
            >
              <Button>
                更多操作 <DownOutlined />
              </Button>
            </Dropdown>
          </Space>
        </div>
      </Card>

      {/* 批量编辑对话框 */}
      <Modal
        title={`批量编辑 ${selectedRowKeys.length} 个资产`}
        open={batchEditVisible}
        onCancel={() => {
          setBatchEditVisible(false);
          form.resetFields();
        }}
        onOk={handleBatchEdit}
        confirmLoading={updateMutation.isPending}
        width={600}
      >
        <Alert
          title="批量编辑说明"
          description="只有填写的字段会被更新，空字段将保持原值不变"
          type="info"
          showIcon
          className={styles.batchEditAlert}
        />

        <Form form={form} layout="vertical">
          <Form.Item name="ownership_status" label="确权状态">
            <Select placeholder="请选择（不修改请留空）" allowClear>
              <Option value="已确权">已确权</Option>
              <Option value="未确权">未确权</Option>
              <Option value="部分确权">部分确权</Option>
            </Select>
          </Form.Item>

          <Form.Item name="property_nature" label="物业性质">
            <Select placeholder="请选择（不修改请留空）" allowClear>
              <Option value="经营类">经营类</Option>
              <Option value="非经营类">非经营类</Option>
            </Select>
          </Form.Item>

          <Form.Item name="usage_status" label="使用状态">
            <Select placeholder="请选择（不修改请留空）" allowClear>
              <Option value="出租">出租</Option>
              <Option value="闲置">闲置</Option>
              <Option value="自用">自用</Option>
              <Option value="公房">公房</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Form.Item>

          <Form.Item name="manager_party_id" label="经营管理方ID">
            <Input placeholder="请输入（不修改请留空）" />
          </Form.Item>

          <Form.Item name="business_category" label="业态类别">
            <Input placeholder="请输入（不修改请留空）" />
          </Form.Item>

          <Form.Item name="certificated_usage" label="证载用途">
            <Input placeholder="请输入（不修改请留空）" />
          </Form.Item>

          <Form.Item name="actual_usage" label="实际用途">
            <Input placeholder="请输入（不修改请留空）" />
          </Form.Item>

          <Form.Item name="is_litigated" label="是否涉诉">
            <Select placeholder="请选择（不修改请留空）" allowClear>
              <Option value={true}>是</Option>
              <Option value={false}>否</Option>
            </Select>
          </Form.Item>

          <Form.Item name="notes" label="备注">
            <TextArea placeholder="请输入备注（不修改请留空）" rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 导出配置对话框 */}
      <Modal
        title="导出配置"
        open={exportVisible}
        onCancel={() => setExportVisible(false)}
        onOk={() => {
          // 处理导出配置
          setExportVisible(false);
        }}
        width={500}
      >
        <Form layout="vertical">
          <Form.Item label="导出格式">
            <Select defaultValue="xlsx">
              <Option value="xlsx">Excel (.xlsx)</Option>
              <Option value="csv">CSV (.csv)</Option>
            </Select>
          </Form.Item>

          <Form.Item label="包含字段">
            <Select
              mode="multiple"
              placeholder="选择要导出的字段"
              defaultValue={['asset_name', 'owner_party_name', 'address']}
            >
              <Option value="asset_name">物业名称</Option>
              <Option value="owner_party_name">权属方</Option>
              <Option value="manager_party_name">经营管理方</Option>
              <Option value="address">所在地址</Option>
              <Option value="land_area">土地面积</Option>
              <Option value="actual_property_area">实际面积</Option>
              <Option value="rentable_area">可出租面积</Option>
              <Option value="rented_area">已出租面积</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default AssetBatchActions;
