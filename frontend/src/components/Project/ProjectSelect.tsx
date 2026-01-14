import React, { useState, useMemo, useEffect } from 'react';
import {
  Select,
  Button,
  Modal,
  Space,
  Tooltip,
} from 'antd';
import { MessageManager } from '@/utils/messageManager';
import {
  PlusOutlined,
  ReloadOutlined,
  UnorderedListOutlined
} from '@ant-design/icons';
import { useProjectOptions } from '@/hooks/useProject';
import type { Project } from '@/types/project';
import ProjectList from '@/components/Project/ProjectList';

interface ProjectSelectProps {
  value?: string;
  onChange?: (value: string, project?: Project) => void;
  placeholder?: string;
  disabled?: boolean;
  allowClear?: boolean;
  style?: React.CSSProperties;
  size?: 'large' | 'middle' | 'small';
  showCreateButton?: boolean;
  onlyActive?: boolean;
}

const ProjectSelect: React.FC<ProjectSelectProps> = ({
  value,
  onChange,
  placeholder = '请选择项目',
  disabled = false,
  allowClear = true,
  style = {},
  size = 'middle',
  showCreateButton = true,
  onlyActive = true
}) => {
    const [selectModalVisible, setSelectModalVisible] = useState(false);

  // 内部状态，用于管理显示的项目名称
  const [displayValue, setDisplayValue] = useState('');

  // 使用React Query获取项目数据
  const { projects: allProjects, loading, refresh } = useProjectOptions(onlyActive);

  // 所有可用项目（搜索功能由Select的filterOption处理）
  const filteredProjects = useMemo(() => {
    return allProjects;
  }, [allProjects]);

  // 当前选中的项目
  const _selectedProject = useMemo(() => {
    if (value == null || value === '') return null;
    return allProjects.find(p => p.id === value) ??
           allProjects.find(p => p.name === value) ??
           null;
  }, [value, allProjects]);

  // 监听value变化，更新显示值
  useEffect(() => {
    if (value == null || value === '') {
      setDisplayValue('');
      return;
    }

    const project = allProjects.find(p => p.id === value);
    if (project != null) {
      const displayName = (project as any).short_name != null ? `${project.name} (${(project as any).short_name})` : project.name;
      setDisplayValue(displayName);
    } else {
      // 如果在allProjects中找不到项目，不要覆盖现有的显示值
      // 这可能发生在项目数据还在加载中的情况
      // 只有当displayValue为空时才设置为原始value
      if (displayValue == null || displayValue === '') {
        setDisplayValue(value);
      }
    }
  }, [value, allProjects, displayValue]);


  // 处理选择
  const handleChange = (selectedValue: string, option: {
    value: string;
    realValue?: string;
    label?: React.ReactNode;
    title?: React.ReactNode;
  }) => {
    // 从option中获取真实的项目ID
    const realValue = option?.realValue ?? option?.value;
    const selected = filteredProjects.find(p => p.id === realValue);

    if (selected != null) {
      setDisplayValue(selectedValue);
      onChange?.(selected.id, selected as any);
    } else {
      setDisplayValue(selectedValue);
      onChange?.(selectedValue);
    }
  };

  // 处理清除
  const handleClear = () => {
    onChange?.('');
    setDisplayValue('');
  };

  // 打开选择弹窗
  const openSelectModal = () => {
    setSelectModalVisible(true);
  };

  // 从弹窗中选择项目
  const handleModalSelect = (project: Project) => {
    // 更新显示值
    const displayName = (project as any).short_name != null ? `${project.name} (${(project as any).short_name})` : project.name;
    setDisplayValue(displayName);

    // 调用父组件的onChange
    onChange?.(project.id, project);
    setSelectModalVisible(false);
  };

  // 刷新列表
  const handleRefresh = () => {
    refresh();
  };

  // 创建新项目
  const handleCreateProject = () => {
    // 这里可以跳转到项目管理页面或打开创建弹窗
    MessageManager.info('创建新项目功能开发中');
  };

  return (
    <div style={style}>
      <Space.Compact style={{ width: '100%' }}>
        <Select
          value={displayValue || undefined}
          onChange={handleChange as any}
          onClear={handleClear}
          placeholder={placeholder}
          disabled={disabled}
          allowClear={allowClear}
          size={size}
          style={{ flex: 1 }}
          loading={loading}
          showSearch
          filterOption={(input, option) =>
            String(option?.children as any ?? '').toLowerCase().includes(input.toLowerCase()) ||
            String(option?.label as any ?? '').toLowerCase().includes(input.toLowerCase())
          }
          notFoundContent={loading ? '加载中...' : '暂无数据'}
          optionLabelProp="label"
          // 自定义显示文本，确保选择项目后显示项目名称而不是ID
          options={filteredProjects.map(project => ({
            label: (project as any).short_name != null ? `${project.name} (${(project as any).short_name})` : project.name,
            value: (project as any).short_name != null ? `${project.name} (${(project as any).short_name})` : project.name,
            // 存储真实的项目ID用于内部处理
            realValue: project.id,
            // 保留完整信息用于下拉显示
            title: (
              <Space>
                <span>{project.name}</span>
                {(project as any).short_name != null && (
                  <span style={{ color: '#999', fontSize: '12px' }}>
                    ({(project as any).short_name})
                  </span>
                )}
                <span style={{ color: '#666', fontSize: '12px' }}>
                  [{project.code}]
                </span>
              </Space>
            ),
          })) as any}
        />

        <Tooltip title="从列表中选择">
          <Button
            icon={<UnorderedListOutlined />}
            onClick={openSelectModal}
            disabled={disabled}
            size={size}
          />
        </Tooltip>

        {showCreateButton && (
          <Tooltip title="创建新项目">
            <Button
              icon={<PlusOutlined />}
              onClick={handleCreateProject}
              disabled={disabled}
              size={size}
            />
          </Tooltip>
        )}

        <Tooltip title="刷新">
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            disabled={disabled}
            loading={loading}
            size={size}
          />
        </Tooltip>
      </Space.Compact>

      {/* 选择弹窗 */}
      <Modal
        title="选择项目"
        open={selectModalVisible}
        onCancel={() => setSelectModalVisible(false)}
        footer={null}
        width={1200}
        destroyOnHidden
      >
        <ProjectList
          mode="select"
          onSelectProject={handleModalSelect}
        />
      </Modal>
    </div>
  );
};

export default ProjectSelect;
