/**
 * 统一项目选择组件
 * 支持单选和多选模式，基于React Query优化性能
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Select, Button, Modal, Space, Tooltip, Tag } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { PlusOutlined, ReloadOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { useProjectOptions } from '@/hooks/useProject';
import type { Project } from '@/types/project';
import ProjectList from '@/components/Project/ProjectList';

const { Option } = Select;

// Select组件标签渲染属性接口
interface CustomTagProps {
  label: React.ReactNode;
  value: string | number;
  closable: boolean;
  onClose: () => void;
}

interface UnifiedProjectSelectProps {
  /** 选中的项目ID(s) */
  value?: string | string[];
  /** 变化回调 */
  onChange?: (value: string | string[], projects?: Project | Project[]) => void;
  /** 占位符 */
  placeholder?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 是否允许清除 */
  allowClear?: boolean;
  /** 样式 */
  style?: React.CSSProperties;
  /** 尺寸 */
  size?: 'large' | 'middle' | 'small';
  /** 选择模式：single | multiple */
  mode?: 'single' | 'multiple';
  /** 是否显示创建按钮 */
  showCreateButton?: boolean;
  /** 是否只显示启用项目 */
  onlyActive?: boolean;
  /** 是否显示高级选择按钮 */
  showAdvancedSelect?: boolean;
  /** 是否显示搜索框 */
  showSearch?: boolean;
  /** 最大选择数量（多选模式） */
  maxCount?: number;
}

const UnifiedProjectSelect: React.FC<UnifiedProjectSelectProps> = ({
  value,
  onChange,
  placeholder = '请选择项目',
  disabled = false,
  allowClear = true,
  style = {},
  size = 'middle',
  mode = 'single',
  showCreateButton = false,
  onlyActive = true,
  showAdvancedSelect = true,
  showSearch = true,
  maxCount,
}) => {
  const [searchText, setSearchText] = useState('');
  const [selectModalVisible, setSelectModalVisible] = useState(false);

  // 使用React Query获取项目数据
  const { projects: allProjects, loading, refresh } = useProjectOptions(onlyActive);

  // 根据搜索文本过滤项目
  const filteredProjects = useMemo(() => {
    if (!searchText) return allProjects;

    return allProjects.filter(
      project =>
        project.name.toLowerCase().includes(searchText.toLowerCase()) ||
        project.code.toLowerCase().includes(searchText.toLowerCase())
    );
  }, [allProjects, searchText]);

  // 处理搜索 - 防抖处理
  const handleSearch = useCallback((text: string) => {
    setSearchText(text);
  }, []);

  // 处理单选
  const handleSingleChange = (selectedValue: string) => {
    const selected = allProjects.find(p => p.id === selectedValue);
    onChange?.(selectedValue, selected as any);
  };

  // 处理多选
  const handleMultipleChange = (selectedValues: string[]) => {
    const selectedProjects = allProjects.filter(p => selectedValues.includes(p.id));
    onChange?.(selectedValues, selectedProjects as any);
  };

  // 处理清除
  const handleClear = () => {
    onChange?.(mode === 'multiple' ? [] : '', mode === 'multiple' ? [] : undefined);
  };

  // 打开高级选择弹窗
  const openAdvancedSelect = () => {
    setSelectModalVisible(true);
  };

  // 从弹窗中选择项目
  const handleModalSelect = (project: Project) => {
    if (mode === 'single') {
      onChange?.(project.id, project as any);
    } else {
      // 多选模式下，添加到已选列表
      const currentValues = Array.isArray(value)
        ? value
        : value != null && value !== ''
          ? [value]
          : [];
      if (!currentValues.includes(project.id)) {
        const newValues =
          maxCount != null && maxCount > 0
            ? [...currentValues.slice(-maxCount + 1), project.id]
            : [...currentValues, project.id];
        const selectedProjects = allProjects.filter(p => newValues.includes(p.id));
        onChange?.(newValues, selectedProjects as any);
      }
    }
    setSelectModalVisible(false);
  };

  // 刷新列表
  const handleRefresh = () => {
    refresh();
  };

  // 创建新项目
  const handleCreateProject = () => {
    MessageManager.info('创建新项目功能开发中');
  };

  // 多选模式下已选项目的标签渲染
  const tagRender = (props: CustomTagProps) => {
    const { value, closable, onClose } = props;
    const project = allProjects.find(p => p.id === value);

    return (
      <Tag
        color={project?.is_active === true ? 'blue' : 'red'}
        closable={closable}
        onClose={onClose}
        style={{ marginRight: 3 }}
      >
        {project?.name ?? value}
      </Tag>
    );
  };

  return (
    <div style={style}>
      <Space.Compact style={{ width: '100%' }}>
        <Select
          value={value != null ? (value as any) : mode === 'multiple' ? [] : undefined}
          onChange={
            mode === 'multiple' ? (handleMultipleChange as any) : (handleSingleChange as any)
          }
          onClear={handleClear}
          placeholder={placeholder}
          disabled={disabled}
          allowClear={allowClear}
          size={size}
          style={{ flex: 1 }}
          loading={loading}
          showSearch={showSearch}
          filterOption={false}
          onSearch={showSearch ? handleSearch : undefined}
          notFoundContent={loading ? '加载中...' : '暂无数据'}
          optionLabelProp="children"
          mode={mode === 'multiple' ? 'multiple' : undefined}
          maxCount={maxCount}
          tagRender={mode === 'multiple' ? tagRender : undefined}
        >
          {filteredProjects.map(project => (
            <Option key={project.id} value={project.id}>
              {project.name}
            </Option>
          ))}
        </Select>

        {showAdvancedSelect && (
          <Tooltip title="高级选择">
            <Button
              icon={<UnorderedListOutlined />}
              onClick={openAdvancedSelect}
              disabled={disabled}
              size={size}
            />
          </Tooltip>
        )}

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

      {/* 高级选择弹窗 */}
      <Modal
        title={`选择项目${mode === 'multiple' ? '（可多选）' : ''}`}
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

export default UnifiedProjectSelect;
