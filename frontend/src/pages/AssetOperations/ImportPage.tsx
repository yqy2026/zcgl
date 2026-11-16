/**
 * 三表导入页（资产运营 v5 V4）
 *
 * 流程契约：选模式 → 下载模板 → 暂存扫描件 → 上传工作簿 →
 * 查看校验与差异（更新模式可逐项选择）→ 提交预览 → 整批提交 →（七日内）可撤销。
 * 任一行错误阻断提交，提示不阻断；空白单元格不覆盖现值。
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Checkbox, Input, Table, Tag, Upload, type UploadFile } from 'antd';
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

      {actionError != '' ? <Alert type="error" showIcon title={actionError} /> : null}

      <section className={styles.modeSection} aria-label="导入模式">
        <Button type={mode === 'create' ? 'primary' : 'default'} onClick={() => setMode('create')}>
          新增导入
        </Button>
        <Button type={mode === 'update' ? 'primary' : 'default'} onClick={() => setMode('update')}>
          更新导入
        </Button>
        <Button
          icon={<DownloadOutlined />}
          onClick={() => templateMutation.mutate()}
          loading={templateMutation.isPending}
        >
          下载三表模板
        </Button>
      </section>

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
            已暂存 {stagedFiles.length} 份：{stagedFiles.join('、')}；工作簿扫描件列填写这些文件名。
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
  );
}

export function describeBlocker(type: string): string {
  return BLOCKER_TEXT[type] ?? `存在后继依赖（${type}）`;
}

export type { UploadFile };
