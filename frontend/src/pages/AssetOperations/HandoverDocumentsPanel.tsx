import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Drawer } from 'antd';
import { handoverArchiveService, type HandoverTarget } from '@/services/handoverArchiveService';
import { AssetOperationsError } from '@/services/assetOperationsService';
import ArchiveDocumentsPanel from '@/pages/AssetOperations/ArchiveDocumentsPanel';
import styles from './HandoverDocumentsPanel.module.css';
function status(item: HandoverTarget): string {
  if (item.can_write) return '可维护交接档案';
  switch (item.unavailable_reason) {
    case 'HANDOVER_EVENT_REVERSED':
      return '已撤销，历史档案保留';
    case 'HANDOVER_NOT_EFFECTIVE':
      return '尚未生效，暂不可维护';
    case 'HANDOVER_NOT_REQUIRED':
      return '不适用，历史档案保留';
    default:
      return '暂不可维护，请重新加载事项';
  }
}
export default function HandoverDocumentsPanel({
  kind,
  contractId,
}: {
  kind: 'upstream' | 'terminal';
  contractId: string;
}): React.ReactElement {
  return <Panel key={kind + ':' + contractId} kind={kind} contractId={contractId} />;
}
function Panel({
  kind,
  contractId,
}: {
  kind: 'upstream' | 'terminal';
  contractId: string;
}): React.ReactElement {
  const query = useQuery({
    queryKey: ['handover-targets', kind, contractId],
    queryFn: () => handoverArchiveService.list(kind, contractId),
    refetchOnMount: 'always',
    retry: false,
  });
  const error = query.error;
  const message =
    error instanceof AssetOperationsError &&
    (error.code.startsWith('PARTY_SCOPE_') || error.code === 'ASSET_OPS_PERMISSION_DENIED')
      ? '访问范围或权限已变化，请联系管理员后重新加载。'
      : '交接事项加载失败，请重新加载。';
  return (
    <section className={styles.panel}>
      <h3>交接书档案</h3>
      <p>按终止或退出事项维护交接书，事件撤销后保留历史文件。</p>
      <Button onClick={() => void query.refetch()}>重新加载交接事项</Button>
      {query.isPending ? (
        <p role="status">交接事项加载中…</p>
      ) : query.isError ? (
        <Alert type="error" title={message} />
      ) : query.data.length === 0 ? (
        <p>暂无终止或退出交接事项。</p>
      ) : (
        <ul className={styles.list}>
          {query.data.map(item => (
            <li key={item.event_id}>
              <EventDocuments item={item} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
function EventDocuments({ item }: { item: HandoverTarget }): React.ReactElement {
  const [open, setOpen] = useState(false);
  const title =
    item.effective_date + ' · ' + (item.event_type === 'terminated' ? '终止交接' : '退出交接');
  return (
    <>
      <strong>{title}</strong>
      <p>{status(item)}</p>
      <Button onClick={() => setOpen(true)}>查看档案</Button>
      <Drawer
        title={title + ' · 档案版本'}
        open={open}
        onClose={() => setOpen(false)}
        size="large"
        destroyOnHidden
      >
        {open ? (
          <ArchiveDocumentsPanel
            targetType="contract_lifecycle_event"
            targetId={item.event_id}
            readOnly={!item.can_write}
          />
        ) : null}
      </Drawer>
    </>
  );
}
