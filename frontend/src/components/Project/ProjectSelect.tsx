import React, { useState, useMemo, useEffect } from 'react';
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
    return allProjects.find(p => p.id === value) ?? allProjects.find(p => p.name === value) ?? null;
  }, [value, allProjects]);

  // 监听value变化，更新显示值
  useEffect(() => {
    if (value == null || value === '') {
      setDisplayValue('');
      return;
    }

    const project = allProjects.find(p => p.id === value);
    if (project != null) {
      const displayName =
        project.short_name != null ? `${project.name} (${project.short_name})` : project.name;
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
  const handleChange: SelectProps<string, ProjectOption>['onChange'] = (selectedValue, option) => {
    if (selectedValue == null) {
      setDisplayValue('');
      onChange?.('');
      return;
    }

    const resolvedOption = Array.isArray(option) ? option[0] : option;
    const realValue = resolvedOption?.realValue ?? resolvedOption?.value;
    const selected = filteredProjects.find(p => p.id === realValue);

    if (selected != null) {
      setDisplayValue(selectedValue);
      onChange?.(selected.id, selected);
    } else {
      setDisplayValue(selectedValue);
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
    setDisplayValue('');
  };

  // 打开选择弹窗
  const openSelectModal = () => {
    setSelectModalVisible(true);
  };

  // 从弹窗中选择项目
  const handleModalSelect = (project: Project) => {
    // 更新显示值
    const displayName =
      project.short_name != null ? `${project.name} (${project.short_name})` : project.name;
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
      <Space.Compact className={styles.fullWidthCompact}>
        <Select<string, ProjectOption>
          value={displayValue || undefined}
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
          optionLabelProp="label"
          // 自定义显示文本，确保选择项目后显示项目名称而不是ID
          options={filteredProjects.map(project => {
            const nameLabel =
              project.short_name != null ? `${project.name} (${project.short_name})` : project.name;
            return {
              label: (
                <Space>
                  <span>{project.name}</span>
                  {project.short_name != null && (
                    <span className={styles.shortNameText}>({project.short_name})</span>
                  )}
                  <span className={styles.codeText}>[{project.code}]</span>
                </Space>
              ),
              value: nameLabel,
              realValue: project.id,
              title: `${nameLabel} [${project.code}]`,
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
