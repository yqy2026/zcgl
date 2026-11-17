import { useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Select, Tag } from 'antd';
import {
  archiveDocumentService,
  type BatchMatchPreview,
  type BatchMatchPreviewItem,
} from '@/services/archiveDocumentService';
import { AssetOperationsError } from '@/services/assetOperationsService';
import styles from './ArchivePage.module.css';

function failure(error: unknown): string {
  if (error instanceof AssetOperationsError) {
    if (error.code === 'BATCH_PREVIEW_EXPIRED') return '预览已过期（30 分钟），请重新选择文件。';
    if (error.code === 'ARCHIVE_TARGET_ALREADY_HAS_FILE')
      return '所选合同已有档案，请到合同详情改用替换，或重新选择目标。';
    if (error.code === 'ARCHIVE_BATCH_DUPLICATE_TARGET')
      return '多个文件指向同一合同，请调整后重试。';
    if (error.code === 'ARCHIVE_DUPLICATE_CONTENT') return '所选文件内容与该合同已归档文件相同。';
    if (error.code.startsWith('PARTY_SCOPE_') || error.code === 'ASSET_OPS_PERMISSION_DENIED')
      return '访问范围或操作权限已变化，请联系管理员后重试。';
    if (error.code === 'RESOURCE_NOT_FOUND' || error.code === 'NOT_FOUND')
      return '配对目标已不可访问，请重新预览后再提交。';
    return error.message;
  }
  return '批量配对失败，请重新上传并重试。';
}

type Choice = string;

function choiceOf(item: BatchMatchPreviewItem): Choice {
  if (item.detected != null) return `${item.detected.target_type}:${item.detected.target_id}`;
  return '';
}

export default function BatchMatchPanel(): React.ReactElement {
  const client = useQueryClient();
  const [selections, setSelections] = useState<Record<string, Choice>>({});
  const [remaining, setRemaining] = useState<BatchMatchPreview | null>(null);
  const preview = useMutation({
    retry: false,
    mutationFn: (files: File[]) => archiveDocumentService.previewBatchMatch(files),
    onSuccess: data => {
      const next: Record<string, Choice> = {};
      for (const item of data.items) next[item.staging_id] = choiceOf(item);
      setSelections(next);
      setRemaining(data);
    },
  });
  const commit = useMutation({
    retry: false,
    mutationFn: (token: string) => {
      const matches = (preview.data?.items ?? [])
        .filter(item => {
          const choice = selections[item.staging_id] ?? '';
          return choice !== '';
        })
        .map(item => {
          const [targetType, targetId] = (selections[item.staging_id] ?? '').split(':') as [
            'upstream_contract' | 'terminal_contract',
            string,
          ];
          return { staging_id: item.staging_id, target_type: targetType, target_id: targetId };
        });
      return archiveDocumentService.commitBatchMatch(token, matches);
    },
    onSuccess: () => {
      const submitted = new Set(selectedIds());
      setRemaining(current =>
        current == null
          ? null
          : { ...current, items: current.items.filter(item => !submitted.has(item.staging_id)) }
      );
      setSelections({});
      void client.invalidateQueries({ queryKey: ['archive-completion'] });
      void client.invalidateQueries({ queryKey: ['archive-matrix'] });
    },
  });
  // 完成率卡片的拖放/点击把文件经自定义事件转交本面板，保持单一预览入口。
  const fileInputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const dropHandler = (event: Event): void => {
      const files = (event as CustomEvent<File[]>).detail ?? [];
      commit.reset();
      if (files.length > 0 && !preview.isPending && !commit.isPending) {
        preview.mutate(files);
      }
    };
    const pickHandler = (): void => {
      fileInputRef.current?.click();
    };
    window.addEventListener('archive-batch-drop', dropHandler);
    window.addEventListener('archive-batch-pick', pickHandler);
    return () => {
      window.removeEventListener('archive-batch-drop', dropHandler);
      window.removeEventListener('archive-batch-pick', pickHandler);
    };
  }, [preview, commit]);

  const items = remaining?.items ?? [];
  function selectedIds(): string[] {
    return items
      .filter(item => (selections[item.staging_id] ?? '') !== '')
      .map(item => item.staging_id);
  }
  const selected = selectedIds();
  return (
    <section className={styles.batchMatch} aria-labelledby="archive-batch-match">
      <h2 id="archive-batch-match">批量配对扫描件</h2>
      <p>
        一次选择多份合同扫描件，系统按文件名中的合同编号（如【五羊司合字[2024]214号】）在当前范围内
        识别目标；识别结果仅是建议，提交前可逐份调整。未识别出的文件请到对应合同详情上传。
      </p>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg"
        aria-label="选择多份扫描件"
        disabled={preview.isPending || commit.isPending}
        onChange={event => {
          const files = Array.from(event.target.files ?? []);
          commit.reset();
          if (files.length > 0) preview.mutate(files);
          event.target.value = '';
        }}
      />
      {preview.isPending ? <p role="status">正在识别文件名中的合同编号…</p> : null}
      {preview.isError ? <Alert type="error" title={failure(preview.error)} /> : null}
      {commit.isError ? <Alert type="error" title={failure(commit.error)} /> : null}
      {commit.isSuccess ? <p role="status">已按所选目标归档，档案完成情况已更新。</p> : null}
      {items.length > 0 ? (
        <table className={styles.batchTable}>
          <thead>
            <tr>
              <th>文件</th>
              <th>识别结果</th>
              <th>配对目标</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => {
              const choice = selections[item.staging_id] ?? '';
              const options = [
                ...(item.detected != null ? [item.detected] : []),
                ...item.ambiguous,
              ];
              return (
                <tr key={item.staging_id}>
                  <td>{item.file_name}</td>
                  <td>
                    {item.detected != null ? (
                      <Tag>识别：{item.detected.label}</Tag>
                    ) : item.ambiguous.length > 0 ? (
                      <Tag>编号命中多份合同，请选择</Tag>
                    ) : (
                      <Tag>未识别到合同编号</Tag>
                    )}
                    {item.already_archived ? <Tag>该合同已有档案</Tag> : null}
                  </td>
                  <td>
                    {options.length > 0 ? (
                      <Select
                        aria-label={`为 ${item.file_name} 选择合同`}
                        value={choice === '' ? undefined : choice}
                        allowClear
                        placeholder="暂不配对"
                        style={{ minWidth: 220 }}
                        disabled={commit.isPending}
                        onChange={value => {
                          setSelections(current => ({
                            ...current,
                            [item.staging_id]: (value ?? '') as Choice,
                          }));
                        }}
                        options={options.map(candidate => ({
                          value: `${candidate.target_type}:${candidate.target_id}`,
                          label: candidate.label,
                        }))}
                      />
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}
      {remaining != null && remaining.items.length > 0 && !commit.isSuccess ? (
        <p>
          <Button
            type="primary"
            disabled={selected.length === 0 || commit.isPending || preview.isPending}
            loading={commit.isPending}
            onClick={() => commit.mutate(remaining?.preview_token ?? '')}
          >
            提交配对（{selected.length} / {items.length} 份）
          </Button>
        </p>
      ) : null}
    </section>
  );
}
