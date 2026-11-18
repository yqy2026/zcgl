/**
 * 三表导入页（资产运营 v5 V4）
 *
 * 流程契约：选模式 → 下载模板 → 暂存扫描件 → 上传工作簿 →
 * 查看校验与差异（更新模式可逐项选择）→ 提交预览 → 整批提交 →（七日内）可撤销。
 * 任一行错误阻断提交，提示不阻断；空白单元格不覆盖现值。
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Checkbox, Input, Steps, Table, Tag, Upload, type UploadFile } from 'antd';
import { DownloadOutlined, RollbackOutlined, ThunderboltOutlined } from '@ant-design/icons';
import {
  ImportError,
  importService,
  type ImportBatchChange,
  type ImportBatchStatus,
} from '@/services/importService';
import styles from './ImportPage.module.css';

type Mode = 'create' | 'update';

const STATUS_TEXT: Record<ImportBatchStatus['status'], string> = {
  uploaded: '已上传',
  validating: '校验中',
  invalid: '校验未通过',
  ready: '待提交',
  committed: '已提交',
  reverted: '已撤销',
};

const SEVERITY_TAG: Record<ImportBatchChange['severity'], { color: string; text: string }> = {
  change: { color: 'blue', text: '变更' },
  warning: { color: 'gold', text: '提醒' },
  error: { color: 'red', text: '错误' },
};

const BLOCKER_TEXT: Record<string, string> = {
  rent_ledger: '租金台账存在人工/追补记录',
  rent_payment: '存在租金实收记录',
  contract_supplement: '存在补充协议登记',
  archive_document: '存在档案文件',
  deposit_record: '存在押金收支记录',
  management_fee_statement: '存在管理费对账单',
  upstream_coverage: '单元被本批外的上游合同覆盖',
};

const TEMPLATE_GUIDE: { name: string; columns: string }[] = [
  {
    name: '物业单元',
    columns:
      '单元编号、单元名称、主体全称、项目编号、地址、业态、获取方式、接管日、管理至、土地面积(㎡)、建筑面积(㎡)、可租面积(㎡)',
  },
  {
    name: '承租合同',
    columns:
      '合同编号、类型、名称、主体全称、运营主体全称、单元编号、开始日、结束日、周期、付款日、保证金(元)、管理费率、扫描件文件名 + 租金阶段列（阶段起/止、原定月租、递增%、免租月数、减免额、实际月租、阶段周期、缴租日）',
  },
  {
    name: '终端合同',
    columns:
      '合同编号、模式、租户主体全称、出租方主体全称、单元编号（顿号分隔=合并出租）、上游合同编号、开始日、结束日、押金(元)、收租方、扫描件文件名 + 租金阶段列',
  },
];

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function errorMessage(error: unknown): string {
  if (error instanceof ImportError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '操作失败';
}

export default function ImportPage(): React.ReactElement {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<Mode>('create');
  const [batch, setBatch] = useState<ImportBatchStatus | null>(null);
  const [actionError, setActionError] = useState('');
  const [revertReason, setRevertReason] = useState('');
  const [stagedFiles, setStagedFiles] = useState<string[]>([]);

  const changesQuery = useQuery({
    queryKey: ['import-batch-changes', batch?.id],
    queryFn: () => importService.listChanges(batch?.id ?? '', { limit: 200 }),
    enabled: batch != null,
  });

  const batchesQuery = useQuery({
    queryKey: ['import-batches'],
    queryFn: () => importService.listBatches(0, 20),
  });

  const updateTemplateMutation = useMutation({
    mutationFn: () => importService.downloadUpdateTemplate(),
    onSuccess: blob => {
      downloadBlob(blob, 'asset-import-update-base.xlsx');
      setActionError('');
    },
    onError: error => setActionError(errorMessage(error)),
  });

  const invalidateBatch = (next: ImportBatchStatus): void => {
    setBatch(next);
    void queryClient.invalidateQueries({
      queryKey: ['import-batch-changes', next.id],
    });
  };

  const templateMutation = useMutation({
    mutationFn: () => importService.downloadCreateTemplate(),
    onSuccess: blob => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'asset-import-template.xlsx';
      anchor.click();
      URL.revokeObjectURL(url);
    },
    onError: error => setActionError(errorMessage(error)),
  });

  const stagingMutation = useMutation({
    mutationFn: (files: File[]) => importService.stageScanFiles(files),
    onSuccess: staged => setStagedFiles(prev => [...prev, ...staged.map(f => f.file_name)]),
    onError: error => setActionError(errorMessage(error)),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => importService.uploadBatch(mode, file, crypto.randomUUID()),
    onSuccess: invalidateBatch,
    onError: error => setActionError(errorMessage(error)),
  });

  const selectionMutation = useMutation({
    mutationFn: (selections: Record<string, boolean>) =>
      importService.updateSelection(batch?.id ?? '', selections),
    onSuccess: invalidateBatch,
    onError: error => setActionError(errorMessage(error)),
  });

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (batch == null) {
        throw new ImportError('批次不存在', 'IMPORT_BATCH_STATE_INVALID');
      }
      const preview = await importService.commitPreview(batch.id);
      return importService.commit(batch.id, {
        commit_token: preview.commit_token,
        expected_version: batch.version,
        proposal_hash: preview.proposal_hash,
        idempotency_key: crypto.randomUUID(),
      });
    },
    onSuccess: result => {
      if (batch != null) {
        invalidateBatch({ ...batch, status: 'committed', version: batch.version + 1 });
      }
      setActionError('');
      void result;
    },
    onError: error => setActionError(errorMessage(error)),
  });

  const revertMutation = useMutation({
    mutationFn: async () => {
      if (batch == null) {
        throw new ImportError('批次不存在', 'IMPORT_BATCH_STATE_INVALID');
      }
      const preview = await importService.revertPreview(batch.id);
      return importService.revert(batch.id, {
        revert_token: preview.revert_token,
        reason: revertReason.trim(),
        idempotency_key: crypto.randomUUID(),
      });
    },
    onSuccess: () => {
      if (batch != null) {
        invalidateBatch({ ...batch, status: 'reverted', version: batch.version + 1 });
      }
      setActionError('');
    },
    onError: error => setActionError(errorMessage(error)),
  });

  const items = changesQuery.data?.items ?? [];
  const changes = items.filter(item => item.severity === 'change');

  return (
    <div className={styles.importPage}>
      <h1 className={styles.pageTitle}>数据导入</h1>
      <div className={styles.mainColumn}>
        {actionError != '' ? <Alert type="error" showIcon title={actionError} /> : null}

        <section className={styles.modeSection} aria-label="导入模式">
          <Button
            type={mode === 'create' ? 'primary' : 'default'}
            onClick={() => setMode('create')}
          >
            新增导入
          </Button>
          <Button
            type={mode === 'update' ? 'primary' : 'default'}
            onClick={() => setMode('update')}
          >
            更新导入
          </Button>
          {mode === 'create' ? (
            <Button
              icon={<DownloadOutlined />}
              onClick={() => templateMutation.mutate()}
              loading={templateMutation.isPending}
            >
              下载三表模板
            </Button>
          ) : null}
        </section>

        <Steps
          aria-label="导入步骤"
          size="small"
          current={
            batch == null
              ? 0
              : batch.status === 'invalid'
                ? 2
                : batch.status === 'ready' ||
                    batch.status === 'committed' ||
                    batch.status === 'reverted'
                  ? mode === 'create'
                    ? 3
                    : 2
                  : 1
          }
          items={
            mode === 'create'
              ? [
                  { title: '下载模板' },
                  { title: '上传并校验' },
                  { title: '处理问题' },
                  { title: '确认导入' },
                ]
              : [{ title: '导出现有台账' }, { title: '上传并核对差异' }, { title: '确认更新' }]
          }
        />

        {mode === 'create' ? (
          <section className={styles.guideSection} aria-label="模板说明">
            <h2 className={styles.sectionTitle}>1 · 下载模板</h2>
            <p className={styles.hintText}>
              一行一个最小可租单元；合并出租的合同，在「单元编号」列用顿号分隔。
            </p>
            {TEMPLATE_GUIDE.map(sheet => (
              <p key={sheet.name} className={styles.hintText}>
                <b>{sheet.name}</b>：{sheet.columns}
              </p>
            ))}
          </section>
        ) : (
          <section className={styles.guideSection} aria-label="导出现有台账">
            <h2 className={styles.sectionTitle}>1 · 导出现有台账</h2>
            <p className={styles.hintText}>
              在导出的表上改；按单元编号 / 合同号匹配，只改填了的列，留空的不动。
              出租状态、计宗等派生字段不能导入，填了也会被忽略。
            </p>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => updateTemplateMutation.mutate()}
              loading={updateTemplateMutation.isPending}
            >
              导出当前台账（Excel · 3 张表）
            </Button>
          </section>
        )}

        <section className={styles.uploadSection} aria-label="扫描件暂存">
          <h2 className={styles.sectionTitle}>第一步 暂存已签扫描件</h2>
          <Upload
            multiple
            accept=".pdf,.jpg,.jpeg,.png"
            showUploadList={false}
            beforeUpload={(file: File) => {
              stagingMutation.mutate([file]);
              return false;
            }}
          >
            <Button loading={stagingMutation.isPending}>选择扫描件（可多选）</Button>
          </Upload>
          {stagedFiles.length > 0 ? (
            <p className={styles.hintText}>
              已暂存 {stagedFiles.length} 份：{stagedFiles.join('、')}
              ；工作簿扫描件列填写这些文件名。
            </p>
          ) : (
            <p className={styles.hintText}>
              新增合同必须先暂存扫描件，Excel 引用文件名；缺件阻断整批提交。
            </p>
          )}
        </section>

        <section className={styles.uploadSection} aria-label="工作簿上传">
          <h2 className={styles.sectionTitle}>第二步 上传工作簿</h2>
          <Upload
            accept=".xlsx"
            maxCount={1}
            showUploadList={false}
            beforeUpload={(file: File) => {
              setActionError('');
              uploadMutation.mutate(file);
              return false;
            }}
          >
            <Button loading={uploadMutation.isPending}>选择三表工作簿（.xlsx）</Button>
          </Upload>
        </section>

        {batch != null ? (
          <section className={styles.batchSection} aria-label="批次状态">
            <h2 className={styles.sectionTitle}>批次状态</h2>
            <p>
              <Tag color={batch.status === 'invalid' ? 'red' : 'blue'}>
                {STATUS_TEXT[batch.status]}
              </Tag>
              行数 {batch.row_count} · 通过 {batch.valid_count} · 错误 {batch.error_count} · 提醒{' '}
              {batch.warning_count}
            </p>

            {batch.status === 'ready' || batch.status === 'invalid' ? (
              <>
                {batch.status === 'invalid' ? (
                  <Alert type="error" showIcon title="存在错误行，修正工作簿后重新上传" />
                ) : null}
                <Table<ImportBatchChange>
                  rowKey="id"
                  size="small"
                  dataSource={items}
                  loading={changesQuery.isLoading}
                  pagination={{ pageSize: 20, showSizeChanger: false }}
                  columns={[
                    {
                      title: '级别',
                      dataIndex: 'severity',
                      width: 80,
                      render: (_: unknown, record) => (
                        <Tag color={SEVERITY_TAG[record.severity].color}>
                          {SEVERITY_TAG[record.severity].text}
                        </Tag>
                      ),
                    },
                    { title: '来源', dataIndex: 'sheet_name', width: 90 },
                    { title: '行', dataIndex: 'row_number', width: 60 },
                    { title: '对象', dataIndex: 'target_key', width: 140 },
                    { title: '说明', dataIndex: 'effect_summary' },
                    ...(mode === 'update'
                      ? [
                          {
                            title: '纳入',
                            width: 70,
                            render: (_: unknown, record: ImportBatchChange) =>
                              record.severity === 'change' ? (
                                <Checkbox
                                  checked={record.selected}
                                  onChange={event =>
                                    selectionMutation.mutate({
                                      [record.id]: event.target.checked,
                                    })
                                  }
                                />
                              ) : null,
                          },
                        ]
                      : []),
                  ]}
                />
                {batch.status === 'ready' ? (
                  <Button
                    type="primary"
                    icon={<ThunderboltOutlined />}
                    loading={commitMutation.isPending}
                    disabled={batch.error_count > 0}
                    onClick={() => commitMutation.mutate()}
                  >
                    预览并整批提交（{changes.filter(item => item.selected).length} 项）
                  </Button>
                ) : null}
              </>
            ) : null}

            {batch.status === 'committed' ? (
              <div className={styles.revertBox}>
                <Input
                  aria-label="撤销原因"
                  placeholder="撤销原因（必填）"
                  value={revertReason}
                  onChange={event => setRevertReason(event.target.value)}
                />
                <Button
                  danger
                  icon={<RollbackOutlined />}
                  loading={revertMutation.isPending}
                  disabled={revertReason.trim() === ''}
                  onClick={() => revertMutation.mutate()}
                >
                  七日内整批撤销
                </Button>
              </div>
            ) : null}
          </section>
        ) : null}
      </div>

      <aside className={styles.batchesAside} aria-label="导入批次">
        <h2 className={styles.sectionTitle}>导入批次</h2>
        {batchesQuery.isLoading ? (
          <p role="status">批次列表加载中…</p>
        ) : batchesQuery.isError ? (
          <p>批次列表暂不可用。</p>
        ) : (batchesQuery.data?.items.length ?? 0) === 0 ? (
          <p>还没有导入批次。</p>
        ) : (
          batchesQuery.data?.items.map(item => (
            <div key={item.id} className={styles.batchCard}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <b style={{ fontSize: 13 }}>
                  {item.mode === 'create' ? '新增' : '更新'} ·{' '}
                  {(item.committed_at ?? '').slice(0, 10) ||
                    (item.reverted_at ?? '').slice(0, 10) ||
                    '进行中'}
                </b>
                <Tag
                  color={
                    item.status === 'committed'
                      ? 'green'
                      : item.status === 'invalid' || item.status === 'reverted'
                        ? 'red'
                        : 'blue'
                  }
                >
                  {STATUS_TEXT[item.status]}
                </Tag>
              </div>
              <p className={styles.hintText}>
                行数 {item.row_count} · 通过 {item.valid_count} · 错误 {item.error_count} · 提醒{' '}
                {item.warning_count}
              </p>
            </div>
          ))
        )}
        <p className={styles.hintText}>
          新增模式下单元编号或合同号已存在会报错；改已有数据用「更新导入」，只覆盖匹配到的字段。
        </p>
      </aside>
    </div>
  );
}

export function describeBlocker(type: string): string {
  return BLOCKER_TEXT[type] ?? `存在后继依赖（${type}）`;
}

export type { UploadFile };
