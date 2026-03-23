import React, { useState, useMemo } from 'react';
import { Select, Button, Modal, Space, Tooltip } from 'antd';
import type { SelectProps } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { MessageManager } from '@/utils/messageManager';
import { PlusOutlined, ReloadOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { useProjectOptions } from '@/hooks/useProject';
import type { Project, ProjectDropdownOption } from '@/types/project';
import ProjectList from '@/components/Project/ProjectList';
import styles from './ProjectSelect.module.css';

interface ProjectSelectProps {
  value?: string;
  onChange?: (value: string, project?: Project | ProjectDropdownOption) => void;
  placeholder?: string;
  disabled?: boolean;
  allowClear?: boolean;
  style?: React.CSSProperties;
  size?: 'large' | 'middle' | 'small';
  showCreateButton?: boolean;
  onlyActive?: boolean;
}

interface ProjectOption extends Omit<DefaultOptionType, 'label' | 'title' | 'value'> {
  label: React.ReactNode;
  value: string;
  realValue: string;
  title?: string;
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
  onlyActive = true,
}) => {
  const [selectModalVisible, setSelectModalVisible] = useState(false);

  // 使用React Query获取项目数据
  const statusFilter = onlyActive ? 'active' : '';
  const { projects: allProjects, loading, refresh } = useProjectOptions(statusFilter);

  // 所有可用项目（搜索功能由Select的filterOption处理）
  const filteredProjects = useMemo(() => {
    return allProjects;
  }, [allProjects]);

  // 处理选择
  const handleChange: SelectProps<string, ProjectOption>['onChange'] = (selectedValue, option) => {
    if (selectedValue == null) {
      onChange?.('');
      return;
    }

    const resolvedOption = Array.isArray(option) ? option[0] : option;
    const realValue = resolvedOption?.realValue ?? resolvedOption?.value;
    const selected = filteredProjects.find(p => p.id === realValue);

    if (selected != null) {
      onChange?.(selected.id, selected);
    } else {
      onChange?.(selectedValue);
    }
  };

  const filterOption: SelectProps<string, ProjectOption>['filterOption'] = (input, option) => {
    const labelText = option?.title ?? (typeof option?.label === 'string' ? option.label : '');
    return labelText.toLowerCase().includes(input.toLowerCase());
  };

  // 处理清除
  const handleClear = () => {
    onChange?.('');
  };

  // 打开选择弹窗
  const openSelectModal = () => {
    setSelectModalVisible(true);
  };

  // 从弹窗中选择项目
  const handleModalSelect = (project: Project) => {
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
      <Space.Compact className={styles.fullWidthCompact}>
        <Select<string, ProjectOption>
          value={value}
          onChange={handleChange}
          onClear={handleClear}
          placeholder={placeholder}
          disabled={disabled}
          allowClear={allowClear}
          size={size}
          className={styles.flexSelect}
          loading={loading}
          showSearch
          filterOption={filterOption}
          notFoundContent={loading ? '加载中...' : '暂无数据'}
          optionLabelProp="title"
          options={filteredProjects.map(project => {
            const title = `${project.project_name} [${project.project_code}]`;
            return {
              label: (
                <Space>
                  <span>{project.project_name}</span>
                  <span className={styles.codeText}>[{project.project_code}]</span>
                </Space>
              ),
              value: project.id,
              realValue: project.id,
              title,
            };
          })}
        />

        <Tooltip title="从列表中选择">
          <Button
            icon={<UnorderedListOutlined />}
            onClick={openSelectModal}
            disabled={disabled}
            size={size}
            aria-label="从列表中选择"
          />
        </Tooltip>

        {showCreateButton && (
          <Tooltip title="创建新项目">
            <Button
              icon={<PlusOutlined />}
              onClick={handleCreateProject}
              disabled={disabled}
              size={size}
              aria-label="创建新项目"
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
            aria-label="刷新"
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
        <ProjectList mode="select" onSelectProject={handleModalSelect} />
      </Modal>
    </div>
  );
};

export default ProjectSelect;
