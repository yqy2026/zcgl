import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Tag } from 'antd';
import CapabilityGuard from '@/components/System/CapabilityGuard';
import { archiveDocumentService, type ArchiveTargetType } from '@/services/archiveDocumentService';
import { AssetOperationsError } from '@/services/assetOperationsService';
import styles from './AssetUnitsPage.module.css';

function PdfThumbnail({ documentId, fileName }: {
  documentId: string;
  fileName: string;
}): React.ReactElement | null {
  const query = useQuery({
    queryKey: ['archive-thumbnail', documentId],
    queryFn: () => archiveDocumentService.thumbnail(documentId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const objectUrl = query.data == null ? null : URL.createObjectURL(query.data);
  useEffect(() => {
    return () => {
      if (objectUrl != null) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);
  if (objectUrl == null) return null;
  return (
    <img
      src={objectUrl}
      alt={`${fileName} 首页缩略图`}
      width={160}
      style={{ display: 'block', border: '1px solid #d9d9d9', borderRadius: 4, marginTop: 8 }}
    />
  );
}

interface PanelProps {
  targetId: string;
  targetType: ArchiveTargetType;
  readOnly?: boolean;
}
export default function ArchiveDocumentsPanel(props: PanelProps): React.ReactElement {
  return <DocumentList key={props.targetType + ':' + props.targetId} {...props} />;
}
function failure(error: unknown): string {
  if (error instanceof AssetOperationsError) {
    if (error.code === 'HANDOVER_EVENT_REVERSED')
      return '此交接事件已撤销，仅可查看和下载历史档案。';
    if (error.code === 'HANDOVER_NOT_EFFECTIVE') return '此交接事件尚未生效，请重新加载交接事项。';
    if (error.code === 'HANDOVER_NOT_REQUIRED')
      return '此事件不要求交接书，仅可查看和下载历史档案。';
    if (error.code === 'SUPPLEMENT_WITHDRAWN') return '此登记已撤回，仅可查看和下载历史档案。';
    if (error.code === 'ARCHIVE_DUPLICATE_CONTENT') return '此文件已归档，请选择内容不同的文件。';
    if (error.code === 'ARCHIVE_VERSION_STALE') return '此版本已被替换，请重新加载后选择现行版本。';
    if (error.code.startsWith('PARTY_SCOPE_') || error.code === 'ASSET_OPS_PERMISSION_DENIED')
      return '访问范围或操作权限已变化，请联系管理员后重试。';
    if (error.code === 'RESOURCE_NOT_FOUND' || error.code === 'NOT_FOUND')
      return '档案对象已不可访问，请刷新后重新选择。';
    return error.message;
  }
  return '操作失败，请重新加载后重试。';
}

function DocumentList({ targetId, targetType, readOnly }: PanelProps): React.ReactElement {
  const query = useQuery({
    queryKey: ['archive-documents', targetType, targetId],
    queryFn: () =>
      targetType === 'property_certificate'
        ? archiveDocumentService.list(targetId)
        : archiveDocumentService.list(targetId, targetType),
    refetchOnMount: 'always',
    retry: false,
  });
  const download = useMutation({
    mutationFn: async (item: { id: string; file_name: string }) => {
      const blob = await archiveDocumentService.download(item.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = item.file_name;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    },
  });
  return (
    <div className={styles.certificates}>
      <Button disabled={query.isFetching} onClick={() => void query.refetch()}>
        重新加载档案
      </Button>
      <CapabilityGuard action="archive" resource="asset_ops" fallback={<></>}>
        {!readOnly ? <DocumentUpload targetId={targetId} targetType={targetType} /> : null}
      </CapabilityGuard>
      {query.isPending ? (
        <p role="status">档案加载中…</p>
      ) : query.isError ? (
        <>
          <Alert type="error" title={failure(query.error)} />
        </>
      ) : query.data.length === 0 ? (
        <p>
          {targetType === 'property_certificate'
            ? '此证照暂无已归档文件。'
            : targetType === 'contract_lifecycle_event'
              ? '此次交接暂无已归档文件。'
              : targetType === 'upstream_contract' || targetType === 'terminal_contract'
                ? '此合同暂无已归档扫描件。'
                : targetType === 'management_fee_statement'
                  ? '此对账单暂无盖章件。'
                  : '此协议暂无已归档文件。'}
        </p>
      ) : (
        query.data.map(item => (
          <article key={item.id}>
            <h4>{item.file_name}</h4>
            {item.content_type === 'application/pdf' ? (
              <PdfThumbnail documentId={item.id} fileName={item.file_name} />
            ) : null}
            <Tag>{item.is_current ? '现行版本' : '历史版本'}</Tag>
            <p>
              版本 {item.document_version} ·{' '}
              {new Intl.DateTimeFormat('zh-CN', {
                timeZone: 'Asia/Shanghai',
                dateStyle: 'short',
                timeStyle: 'short',
              }).format(
                new Date(
                  /(?:Z|[+-]\d{2}:\d{2})$/.test(item.uploaded_at)
                    ? item.uploaded_at
                    : item.uploaded_at + 'Z'
                )
              ) + ' 北京时间'}
            </p>
            <Button disabled={download.isPending} onClick={() => download.mutate(item)}>
              下载 {item.file_name}
            </Button>
            {item.is_current && !readOnly ? (
              <CapabilityGuard action="archive" resource="asset_ops" fallback={<></>}>
                <DocumentUpload targetId={targetId} targetType={targetType} documentId={item.id} />
              </CapabilityGuard>
            ) : null}
          </article>
        ))
      )}
      {download.isError ? <Alert type="error" title={failure(download.error)} /> : null}
    </div>
  );
}

function DocumentUpload({
  targetId,
  targetType,
  documentId,
}: {
  targetId: string;
  targetType: ArchiveTargetType;
  documentId?: string;
}): React.ReactElement {
  const client = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const form = useForm();
  const mutation = useMutation({
    retry: false,
    mutationFn: (selected: File) =>
      documentId == null
        ? targetType === 'property_certificate'
          ? archiveDocumentService.upload(targetId, selected)
          : archiveDocumentService.upload(targetId, selected, targetType)
        : archiveDocumentService.replace(documentId, selected),
    onError: error => {
      if (error instanceof AssetOperationsError && error.code.startsWith('HANDOVER_'))
        void client.invalidateQueries({ queryKey: ['handover-targets'] });
      if (error instanceof AssetOperationsError && error.code === 'SUPPLEMENT_WITHDRAWN') {
        void client.invalidateQueries({ queryKey: ['contract-supplements'] });
      }
      if (error instanceof AssetOperationsError && error.code === 'ARCHIVE_VERSION_STALE') {
        void client.invalidateQueries({ queryKey: ['archive-documents', targetType, targetId] });
      }
    },
    onSuccess: () => {
      setFile(null);
      form.reset();
      void client.invalidateQueries({ queryKey: ['archive-documents', targetType, targetId] });
      void client.invalidateQueries({ queryKey: ['archive-completion'] });
      void client.invalidateQueries({ queryKey: ['archive-matrix'] });
    },
  });
  return (
    <form
      className={styles.certificateForm}
      noValidate
      onSubmit={form.handleSubmit(() => {
        if (file != null && !mutation.isPending) mutation.mutate(file);
      })}
    >
      <label>
        {documentId == null ? '选择归档文件' : '选择替换文件'}
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          required
          disabled={mutation.isPending}
          {...form.register('file')}
          onChange={event => {
            void form.register('file').onChange(event);
            setFile(event.target.files?.[0] ?? null);
            mutation.reset();
          }}
        />
      </label>
      <p>支持 PDF、PNG、JPG；替换后保留历史版本。</p>
      <Button
        htmlType="submit"
        loading={mutation.isPending}
        disabled={file == null || mutation.isPending}
      >
        {documentId == null ? '上传档案' : '保存替换版本'}
      </Button>
      {mutation.isError ? <Alert type="error" title={failure(mutation.error)} /> : null}
      {mutation.isSuccess ? <p role="status">档案已保存。</p> : null}
    </form>
  );
}
