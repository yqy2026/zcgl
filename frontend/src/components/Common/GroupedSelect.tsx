import React, { useState, useMemo } from 'react';
import { Select, Input, Tag, Space, Typography } from 'antd';
import type { SelectProps } from 'antd';
import { EnumGroup, EnumOption, EnumSearchHelper } from '@/utils/enumHelpers';
import styles from './GroupedSelect.module.css';

const { Option } = Select;
const { Search } = Input;
const { Text } = Typography;

interface GroupedSelectProps extends Omit<SelectProps, 'options'> {
  groups: EnumGroup[];
  showSearch?: boolean;
  placeholder?: string;
  onSearch?: (value: string) => void;
  allowClear?: boolean;
  showGroupLabel?: boolean;
  maxDisplayCount?: number;
}

/**
 * 支持分组和搜索的Select组件
 */
const GroupedSelect: React.FC<GroupedSelectProps> = ({
  groups,
  showSearch = true,
  placeholder = '请选择',
  onSearch,
  allowClear = true,
  showGroupLabel = true,
  maxDisplayCount = 50,
  value,
  onChange,
  ...selectProps
}) => {
  const [searchKeyword, setSearchKeyword] = useState('');

  // 过滤后的分组数据
  const filteredGroups = useMemo(() => {
    if (!searchKeyword.trim()) return groups;

    const filtered = EnumSearchHelper.searchInGroups(groups, searchKeyword);

    // 限制最大显示数量
    if (maxDisplayCount > 0) {
      let count = 0;
      return filtered
        .map(group => ({
          ...group,
          options: group.options.filter(_option => {
            count++;
            return count <= maxDisplayCount;
          }),
        }))
        .filter(group => group.options.length > 0);
    }

    return filtered;
  }, [groups, searchKeyword, maxDisplayCount]);

  // 处理搜索
  const handleSearch = (value: string) => {
    setSearchKeyword(value);
    onSearch?.(value);
  };

  // 获取选中项的显示信息
  const getSelectedOptionInfo = (selectedValue: string): EnumOption | undefined => {
    return EnumSearchHelper.findByValue(groups, selectedValue);
  };

  // 自定义下拉选择器内容
  const dropdownRender = (menu: React.ReactElement) => {
    if (
      searchKeyword !== undefined &&
      searchKeyword !== null &&
      searchKeyword !== '' &&
      filteredGroups.every(group => group.options.length === 0)
    ) {
      return (
        <div className={styles.emptyContainer}>
          <Text type="secondary">未找到匹配的选项</Text>
        </div>
      );
    }

    return (
      <div>
        {showSearch && (
          <div className={styles.searchHeader}>
            <Search
              placeholder="搜索选项..."
              value={searchKeyword}
              onChange={e => handleSearch(e.target.value)}
              className={styles.fullWidthSearch}
              allowClear
              aria-label="搜索选项"
            />
          </div>
        )}
        {menu}
      </div>
    );
  };

  // 生成选项内容
  const renderOptions = () => {
    return filteredGroups.map((group, groupIndex) => {
      if (group.options.length === 0) return null;

      if (showGroupLabel !== undefined && showGroupLabel !== null && showGroupLabel !== false) {
        // 显示分组标签
        return (
          <React.Fragment key={groupIndex}>
            <Select.OptGroup
              label={
                <Space>
                  <Text strong>{group.label}</Text>
                  <Text type="secondary">({group.options.length})</Text>
                </Space>
              }
            >
              {group.options.map(option => (
                <Option key={option.value} value={option.value}>
                  <Space>
                    {option.color != null && (
                      <span className={`${styles.colorDot} ${getColorDotClass(option.color)}`} />
                    )}
                    <span>{option.label}</span>
                    {option.description != null && (
                      <Text type="secondary" className={styles.optionDescription}>
                        - {option.description}
                      </Text>
                    )}
                  </Space>
                </Option>
              ))}
            </Select.OptGroup>
          </React.Fragment>
        );
      } else {
        // 不显示分组标签，直接渲染选项
        return group.options.map(option => (
          <Option key={option.value} value={option.value}>
            <Space>
              {option.color != null && (
                <span className={`${styles.colorDot} ${getColorDotClass(option.color)}`} />
              )}
              <span>{option.label}</span>
              {option.description != null && (
                <Text type="secondary" className={styles.optionDescription}>
                  - {option.description}
                </Text>
              )}
            </Space>
          </Option>
        ));
      }
    });
  };

  // 获取颜色点 class
  const getColorDotClass = (color: string): string => {
    const colorClassMap: Record<string, string> = {
      blue: styles.colorDotBlue,
      green: styles.colorDotGreen,
      orange: styles.colorDotOrange,
      red: styles.colorDotRed,
      purple: styles.colorDotPurple,
      cyan: styles.colorDotCyan,
      default: styles.colorDotDefault,
    };
    return colorClassMap[color] ?? colorClassMap.default;
  };

  // 自定义标签显示
  const tagRender = (props: {
    label: string;
    value: string;
    closable: boolean;
    onClose: () => void;
  }) => {
    const { label, value, closable, onClose } = props;
    const optionInfo = getSelectedOptionInfo(value);

    return (
      <Tag
        color={optionInfo !== undefined && optionInfo !== null ? optionInfo.color : undefined}
        closable={closable}
        onClose={onClose}
        className={styles.selectedTag}
      >
        {optionInfo !== undefined && optionInfo !== null ? optionInfo.label : label}
      </Tag>
    );
  };

  return (
    <Select
      {...(selectProps as SelectProps)}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      allowClear={allowClear}
      showSearch={showSearch}
      filterOption={false} // 禁用默认过滤，使用自定义搜索
      onSearch={handleSearch}
      popupRender={dropdownRender}
      tagRender={tagRender as React.ComponentProps<typeof Select>['tagRender']}
    >
      {renderOptions()}
    </Select>
  );
};

// 单选版本的GroupedSelect
export const GroupedSelectSingle: React.FC<GroupedSelectProps> = props => {
  return <GroupedSelect {...props} mode={undefined} />;
};

// 多选版本的GroupedSelect
export const GroupedSelectMultiple: React.FC<GroupedSelectProps> = props => {
  return <GroupedSelect {...props} mode="multiple" />;
};

export default GroupedSelect;
