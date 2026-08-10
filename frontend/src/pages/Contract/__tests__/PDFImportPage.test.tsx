import { describe, it, expect, vi, beforeEach } from 'vitest';
import { message } from 'antd';
import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils/test-helpers';
import PDFImportPage from '../PDFImportPage';
import { documentExtractionService } from '@/services/documentExtractionService';

vi.mock('@/services/documentExtractionService', () => ({
  documentExtractionService: {
    createContractSession: vi.fn(),
    confirm: vi.fn(),
    cancel: vi.fn(),
  },
}));

vi.mock('@/components/Project/ProjectSelect', () => ({
  default: ({
    value,
    disabled,
    onChange,
  }: {
    value?: string;
    disabled?: boolean;
    onChange?: (value: string) => void;
  }) => (
    <button
      type="button"
      data-testid="project-select"
      data-disabled={disabled === true}
      data-value={value ?? ''}
      onClick={() => onChange?.('project-1')}
    >
      set-project
    </button>
  ),
}));

vi.mock('@/components/Common/PartySelector', () => ({
  default: ({ value, onChange }: { value?: string; onChange?: (value: string) => void }) => (
    <button
      type="button"
      data-testid="party-selector"
      data-value={value ?? ''}
      onClick={() => onChange?.('party-1')}
    >
      set-party
    </button>
  ),
}));

vi.mock('@/components/Common/AssetMultiSelect', () => ({
  default: ({ onChange }: { onChange?: (ids: string[]) => void }) => (
    <button type="button" data-testid="asset-multi-select" onClick={() => onChange?.(['asset-1'])}>
      set-assets
    </button>
  ),
}));

vi.mock('@/utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
  }),
}));

const createContractSessionMock = vi.mocked(documentExtractionService.createContractSession);
const confirmMock = vi.mocked(documentExtractionService.confirm);

const session = {
  session_id: 'session-1',
  target_type: 'contract',
  status: 'ready_for_review',
  candidates: { fields: { contract_number: { conflict: false, candidates: [] } } },
  errors: [],
};

const pickSelectOption = async (combobox: HTMLElement, label: string): Promise<void> => {
  fireEvent.mouseDown(combobox);
  await waitFor(() => {
    expect(document.querySelectorAll('.ant-select-item-option').length).toBeGreaterThan(0);
  });
  const options = Array.from(document.querySelectorAll('.ant-select-item-option'));
  const target = options.find(el => el.textContent?.includes(label));
  expect(target).not.toBeUndefined();
  fireEvent.click(target as Element);
};

const pickPdfFile = (): void => {
  const uploadInput = document.querySelector('input[type="file"]');
  expect(uploadInput).not.toBeNull();
  const file = new File(['pdf-content'], 'contract.pdf', { type: 'application/pdf' });
  fireEvent.change(uploadInput as Element, { target: { files: [file] } });
};

const fillRequiredUploadFields = async (): Promise<void> => {
  // 经营模式默认承租转租；补合同方向与合同角色；选择 PDF 文件
  const comboboxes = screen.getAllByRole('combobox');
  await pickSelectOption(comboboxes[1], '出租');
  await pickSelectOption(screen.getAllByRole('combobox')[2], '下游');
  pickPdfFile();
};

describe('PDFImportPage - 上传页（中文 + 预填锁定）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('全中文标题与字段文案', () => {
    renderWithProviders(<PDFImportPage />, { route: '/contract-center/import' });

    expect(screen.getByText('合同文件解析')).toBeInTheDocument();
    expect(screen.getByText('所属项目')).toBeInTheDocument();
    expect(screen.getByText('经营模式')).toBeInTheDocument();
    expect(screen.getByText('合同方向')).toBeInTheDocument();
    expect(screen.getByText('合同角色')).toBeInTheDocument();
    expect(screen.getByText('选择 PDF 文件')).toBeInTheDocument();
    expect(screen.getByText('开始解析')).toBeInTheDocument();
  });

  it('URL 携带 project_id 时项目预填并锁定，提示来源项目详情', () => {
    renderWithProviders(<PDFImportPage />, {
      route: '/contract-center/import?project_id=project-9',
    });

    const projectSelect = screen.getByTestId('project-select');
    expect(projectSelect).toHaveAttribute('data-value', 'project-9');
    expect(projectSelect).toHaveAttribute('data-disabled', 'true');
    expect(screen.getByText(/来自项目详情/)).toBeInTheDocument();
  });

  it('开始解析时以预填项目创建解析会话', async () => {
    createContractSessionMock.mockResolvedValue(session as never);
    renderWithProviders(<PDFImportPage />, {
      route: '/contract-center/import?project_id=project-9',
    });

    await fillRequiredUploadFields();
    fireEvent.click(screen.getByText('开始解析'));

    await waitFor(() => {
      expect(createContractSessionMock).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ project_id: 'project-9' })
      );
    });
  });
});

describe('PDFImportPage - 确认页（中文 + 选择器 + 付款周期）', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createContractSessionMock.mockResolvedValue(session as never);
  });

  it('渲染中文确认页：付款周期字段卡、四个主体选择器与资产多选', async () => {
    renderWithProviders(<PDFImportPage />, {
      route: '/contract-center/import?project_id=project-9',
    });
    await fillRequiredUploadFields();
    fireEvent.click(screen.getByText('开始解析'));

    await waitFor(() => {
      expect(screen.getByText('逐项确认提取的合同字段')).toBeInTheDocument();
    });
    expect(screen.getByText('付款周期')).toBeInTheDocument();
    expect(screen.getByText('运营方主体')).toBeInTheDocument();
    expect(screen.getByText('产权方主体')).toBeInTheDocument();
    expect(screen.getByText('出租方主体')).toBeInTheDocument();
    expect(screen.getByText('承租方主体')).toBeInTheDocument();
    expect(screen.getAllByTestId('party-selector')).toHaveLength(4);
    expect(screen.getByTestId('asset-multi-select')).toBeInTheDocument();
    expect(screen.getByText('创建合同')).toBeInTheDocument();
    // antd 对两字按钮自动插入空格（autoInsertSpaceInButton）
    expect(screen.getByText(/取\s*消/)).toBeInTheDocument();
  });

  it('未逐字段处理时点击创建给出中文提示', async () => {
    const messageErrorSpy = vi.spyOn(message, 'error').mockImplementation(() => {
      // antd message 在 jsdom 中渲染不可靠，直接断言调用参数
    });
    renderWithProviders(<PDFImportPage />, {
      route: '/contract-center/import?project_id=project-9',
    });
    await fillRequiredUploadFields();
    fireEvent.click(screen.getByText('开始解析'));

    await waitFor(() => {
      expect(screen.getByText('逐项确认提取的合同字段')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('创建合同'));

    await waitFor(() => {
      expect(messageErrorSpy).toHaveBeenCalledWith('请为字段「合同编号」选择处理方式。');
    });
    expect(confirmMock).not.toHaveBeenCalled();
    messageErrorSpy.mockRestore();
  });
});
