import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Timeline } from 'antd';

import {
  businessChangeService,
  type BusinessChangeEvent,
  type BusinessChangeTargetType,
} from '@/services/businessChangeService';
import { AssetOperationsError } from '@/services/assetOperationsService';

import styles from './HandoverDocumentsPanel.module.css';

const ACTION_LABELS: Record<string, string> = {
  confirmed: '确认',
  updated: '修改',
  renewed: '续签',
  terminated: '终止',
  exited: '退出',
  reversed: '撤销',
  created: '新建',
  create: '新建',
  split: '拆分',
  merge: '合并',
  update_vacancy_note: '空置备注',
  rent_schedule_corrected: '租金阶段更正',
  manual_rent_created: '手工台账新增',
  manual_rent_voided: '手工台账作废',
  rent_payment_registered: '租金登记',
  rent_payment_reversed: '租金撤销',
  rent_clawback_created: '补收免租',
  rent_obligations_replanned: '义务重排',
  deposit_record_registered: '押金收支登记',
  deposit_record_reversed: '押金收支撤销',
  certificate_link_added: '证照关联',
  certificate_link_removed: '证照解除',
  management_fee_stamp_bound: '盖章件绑定',
};

const PAGE_SIZE = 50;

function formatOccurredAt(occurredAt: string): string {
  return (
    new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(
      new Date(/(?:Z|[+-]\d{2}:\d{2})$/.test(occurredAt) ? occurredAt : occurredAt + 'Z')
    ) + ' 北京时间'
  );
}

function eventChildren(event: BusinessChangeEvent): React.ReactNode {
  const actionLabel = ACTION_LABELS[event.action] ?? event.action;
  return (
    <div>
      <p style={{ margin: 0 }}>
        <strong>{actionLabel}</strong> · {formatOccurredAt(event.occurred_at)}
      </p>
      <p style={{ margin: 0 }}>{event.summary}</p>
      {event.reason != null && event.reason !== '' ? (
        <p style={{ margin: 0 }}>原因：{event.reason}</p>
      ) : null}
    </div>
  );
}

function isScopeForbidden(error: unknown): boolean {
  return (
    error instanceof AssetOperationsError && error.code.startsWith('PARTY_SCOPE_')
  );
}

export default function ChangeTimelinePanel({
  targetType,
  targetId,
}: {
  targetType: BusinessChangeTargetType;
  targetId: string;
}): React.ReactElement {
  const query = useQuery({
    queryKey: ['business-change-events', targetType, targetId],
    queryFn: () => businessChangeService.list(targetType, targetId),
    refetchOnMount: 'always',
    retry: false,
  });
  return (
    <section className={styles.panel} aria-label="变更时间线">
      <h3>变更时间线</h3>
      {query.isError ? (
        <>
          <Alert
            type={isScopeForbidden(query.error) ? 'warning' : 'error'}
            showIcon
            title={
              isScopeForbidden(query.error)
                ? '没有可访问的数据范围，请联系管理员配置数据范围。'
                : '变更记录加载失败，请重新加载。'
            }
          />
          <Button disabled={query.isFetching} onClick={() => void query.refetch()}>
            重新加载变更记录
          </Button>
        </>
      ) : query.isPending ? (
        <p role="status">变更记录加载中…</p>
      ) : (query.data?.items.length ?? 0) === 0 ? (
        <p>暂无变更记录。</p>
      ) : (
        <>
          <Timeline
            items={query.data?.items.map(event => ({
              key: event.id,
              content: eventChildren(event),
            }))}
          />
          {(query.data?.total ?? 0) > PAGE_SIZE ? (
            <p>共 {query.data?.total ?? 0} 条，仅展示最近 {PAGE_SIZE} 条。</p>
          ) : null}
        </>
      )}
    </section>
  );
}
