/**
 * Ant Design Icons Mock
 */

import React from 'react';
import type { FC } from 'react';

interface IconProps {
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}

const createMockIcon = (name: string): FC<IconProps> => {
  const Icon: FC<IconProps> = (props) => (
    <span data-testid={`icon-${name.toLowerCase()}`} {...props} />
  );
  Icon.displayName = name;
  return Icon;
};

// 常用图标 Mock
export const EditOutlined = createMockIcon('edit');
export const DeleteOutlined = createMockIcon('delete');
export const EyeOutlined = createMockIcon('eye');
export const PlusOutlined = createMockIcon('plus');
export const SearchOutlined = createMockIcon('search');
export const DownloadOutlined = createMockIcon('download');
export const UploadOutlined = createMockIcon('upload');
export const SettingOutlined = createMockIcon('setting');
export const UserOutlined = createMockIcon('user');
export const HomeOutlined = createMockIcon('home');
export const MenuOutlined = createMockIcon('menu');
export const CloseOutlined = createMockIcon('close');
export const CheckOutlined = createMockIcon('check');
export const WarningOutlined = createMockIcon('warning');
export const InfoCircleOutlined = createMockIcon('info-circle');
export const ExclamationCircleOutlined = createMockIcon('exclamation-circle');
export const LoadingOutlined = createMockIcon('loading');
export const HistoryOutlined = createMockIcon('history');
export const EnvironmentOutlined = createMockIcon('environment');
export const FileOutlined = createMockIcon('file');
export const FolderOutlined = createMockIcon('folder');
export const SyncOutlined = createMockIcon('sync');
export const ReloadOutlined = createMockIcon('reload');
export const FilterOutlined = createMockIcon('filter');
export const SortAscendingOutlined = createMockIcon('sort-ascending');
export const SortDescendingOutlined = createMockIcon('sort-descending');
export const MoreOutlined = createMockIcon('more');
export const EllipsisOutlined = createMockIcon('ellipsis');
export const CopyOutlined = createMockIcon('copy');
export const SaveOutlined = createMockIcon('save');
export const UndoOutlined = createMockIcon('undo');
export const RedoOutlined = createMockIcon('redo');
export const QuestionCircleOutlined = createMockIcon('question-circle');
export const CheckCircleOutlined = createMockIcon('check-circle');
export const CloseCircleOutlined = createMockIcon('close-circle');
export const RightOutlined = createMockIcon('right');
export const LeftOutlined = createMockIcon('left');
export const UpOutlined = createMockIcon('up');
export const DownOutlined = createMockIcon('down');
export const CalendarOutlined = createMockIcon('calendar');
export const TeamOutlined = createMockIcon('team');
export const BankOutlined = createMockIcon('bank');
export const BuildOutlined = createMockIcon('build');
export const ToolOutlined = createMockIcon('tool');
export const DashboardOutlined = createMockIcon('dashboard');
export const BarChartOutlined = createMockIcon('bar-chart');
export const LineChartOutlined = createMockIcon('line-chart');
export const PieChartOutlined = createMockIcon('pie-chart');
export const AreaChartOutlined = createMockIcon('area-chart');

/**
 * 创建完整的 @ant-design/icons Mock
 */
export function createIconsMock() {
  return {
    EditOutlined,
    DeleteOutlined,
    EyeOutlined,
    PlusOutlined,
    SearchOutlined,
    DownloadOutlined,
    UploadOutlined,
    SettingOutlined,
    UserOutlined,
    HomeOutlined,
    MenuOutlined,
    CloseOutlined,
    CheckOutlined,
    WarningOutlined,
    InfoCircleOutlined,
    ExclamationCircleOutlined,
    LoadingOutlined,
    HistoryOutlined,
    EnvironmentOutlined,
    FileOutlined,
    FolderOutlined,
    SyncOutlined,
    ReloadOutlined,
    FilterOutlined,
    SortAscendingOutlined,
    SortDescendingOutlined,
    MoreOutlined,
    EllipsisOutlined,
    CopyOutlined,
    SaveOutlined,
    UndoOutlined,
    RedoOutlined,
    QuestionCircleOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    RightOutlined,
    LeftOutlined,
    UpOutlined,
    DownOutlined,
    CalendarOutlined,
    TeamOutlined,
    BankOutlined,
    BuildOutlined,
    ToolOutlined,
    DashboardOutlined,
    BarChartOutlined,
    LineChartOutlined,
    PieChartOutlined,
    AreaChartOutlined,
  };
}
