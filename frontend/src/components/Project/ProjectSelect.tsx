import React, { useState, useCallback, useMemo } from 'react';
import {
  Select,
  Button,
  Modal,
  message,
  Space,
  Input,
  Tooltip
} from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useProjectOptions } from '@/hooks/useProject';
import type { Project } from '@/types/project';
import ProjectList from '@/components/Project/ProjectList';

const { Option } = Select;
const { Search } = Input;

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
  const [searchText, setSearchText] = useState('');
  const [selectModalVisible, setSelectModalVisible] = useState(false);

  // 使用React Query获取项目数据
  const { projects: allProjects, loading, refresh } = useProjectOptions(onlyActive);

  // 根据搜索文本过滤项目
  const filteredProjects = useMemo(() => {
    if (!searchText) return allProjects;

    return allProjects.filter(project =>
      project.name.toLowerCase().includes(searchText.toLowerCase()) ||
      project.code.toLowerCase().includes(searchText.toLowerCase()) ||
      project.short_name?.toLowerCase().includes(searchText.toLowerCase())
    );
  }, [allProjects, searchText]);

  // 当前选中的项目
  const selectedProject = useMemo(() => {
    if (!value) return null;
    return filteredProjects.find(p => p.id === value) ||
           filteredProjects.find(p => p.name === value) ||
           null;
  }, [value, filteredProjects]);

  // 处理搜索 - 防抖处理
  const handleSearch = useCallback((text: string) => {
    setSearchText(text);
  }, []);

  // 处理选择
  const handleChange = (selectedValue: string) => {
    const selected = filteredProjects.find(p => p.id === selectedValue) ||
                    filteredProjects.find(p => p.name === selectedValue);

    if (selected) {
      onChange?.(selected.id, selected);
    } else {
      onChange?.(selectedValue);
    }
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
    message.info('创建新项目功能开发中');
  };

  return (
    <div style={style}>
      <Space.Compact style={{ width: '100%' }}>
        <Select
          value={value || undefined}
          onChange={handleChange}
          onClear={handleClear}
          placeholder={placeholder}
          disabled={disabled}
          allowClear={allowClear}
          size={size}
          style={{ flex: 1 }}
          loading={loading}
          showSearch
          filterOption={false}
          onSearch={handleSearch}
          notFoundContent={loading ? '加载中...' : '暂无数据'}
          optionLabelProp="children"
        >
          {filteredProjects.map(project => (
            <Option key={project.id} value={project.id}>
              <Space>
                <span>{project.name}</span>
                {project.short_name && (
                  <span style={{ color: '#999', fontSize: '12px' }}>
                    ({project.short_name})
                  </span>
                )}
                <span style={{ color: '#666', fontSize: '12px' }}>
                  [{project.code}]
                </span>
              </Space>
            </Option>
          ))}
        </Select>

        <Tooltip title="从列表中选择">
          <Button
            icon={<SearchOutlined />}
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
        destroyOnClose
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