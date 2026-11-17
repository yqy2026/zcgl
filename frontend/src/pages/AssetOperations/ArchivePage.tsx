import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Input, Table } from 'antd';
import CapabilityGuard from '@/components/System/CapabilityGuard';
import { Link, useSearchParams } from 'react-router-dom';
import BatchMatchPanel from '@/pages/AssetOperations/BatchMatchPanel';
import { businessToday } from '@/services/assetLedgerService';
import { archiveMatrixService } from '@/services/archiveMatrixService';
import type { ArchiveCategory, ArchiveMatrixRow } from '@/services/archiveMatrixService';
import { AssetOperationsError } from '@/services/assetOperationsService';
import { ASSET_OPERATIONS_V5_ROUTES } from '@/constants/routes';
import styles from './ArchivePage.module.css';
export function categoryValue(item: ArchiveCategory): string {
  if (!item.supported) return '登记清单待接入';
  if (item.required == null || item.existing == null) return '统计不可用';
  if (item.required === 0) return '不适用';
  return `${item.existing} / ${item.required}`;
}
function errorText(error: unknown): string {
  return error instanceof AssetOperationsError &&
    (error.code.startsWith('PARTY_SCOPE_') || error.code === 'ASSET_OPS_PERMISSION_DENIED')
    ? '访问范围或权限已变化，请联系管理员后重新加载。'
    : '档案统计加载失败，请重新加载。';
}
export default function ArchivePage(): React.ReactElement {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const projectId = params.get('project_id') ?? undefined;
  const asOf = params.get('as_of') ?? '';
  const requestedPage = Number(params.get('page') ?? '1');
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const [input, setInput] = useState(q);
  const setPage = (next: number): void => {
    const updated = new URLSearchParams(params);
    updated.set('page', String(next));
    setParams(updated);
  };
  const setAsOf = (value: string): void => {
    const updated = new URLSearchParams(params);
    if (value === '') updated.delete('as_of');
    else updated.set('as_of', value);
    updated.delete('page');
    setParams(updated);
  };
  const search = (): void => {
    const updated = new URLSearchParams(params);
    if (input.trim() === '') updated.delete('q');
    else updated.set('q', input.trim());
    updated.delete('page');
    setParams(updated);
  };
  const completion = useQuery({
    queryKey: ['archive-completion', projectId, q, asOf],
    queryFn: () =>
      archiveMatrixService.completion({
        project_id: projectId,
        q: q === '' ? undefined : q,
        as_of: asOf === '' ? undefined : asOf,
      }),
    refetchOnMount: 'always',
    retry: false,
  });
  const matrix = useQuery({
    queryKey: ['archive-matrix', projectId, q, page, asOf],
    queryFn: () =>
      archiveMatrixService.matrix({
        project_id: projectId,
        q: q === '' ? undefined : q,
        offset: (page - 1) * 20,
        limit: 20,
        as_of: asOf === '' ? undefined : asOf,
      }),
    refetchOnMount: 'always',
    retry: false,
  });
  const reload = (): void => {
    void completion.refetch();
    void matrix.refetch();
  };
  const error = completion.error ?? matrix.error;
  return (
    <div className={styles.page}>
      <header>
        <h1>档案</h1>
        <p>
          默认统计当前在管物业及当前有效合同；选择历史统计日期按该日时点重算完成率与矩阵。
          总览按业务对象去重；同一档案在相关物业展示相同状态。
        </p>
      </header>
      <CapabilityGuard action="archive" resource="asset_ops" fallback={<></>}>
        <BatchMatchPanel />
      </CapabilityGuard>
      <form
        className={styles.search}
        onSubmit={event => {
          event.preventDefault();
          search();
        }}
      >
        <label htmlFor="archive-search">搜索物业编号、名称或地址</label>
        <Input
          maxLength={100}
          id="archive-search"
          value={input}
          onChange={event => setInput(event.target.value)}
        />
        <Button htmlType="submit">查询档案</Button>
        <Button onClick={reload}>重新加载统计</Button>
        <label htmlFor="archive-as-of">统计日期</label>
        <input
          type="date"
          id="archive-as-of"
          value={asOf}
          max={businessToday()}
          onChange={event => setAsOf(event.target.value)}
        />
        {asOf !== '' ? <Button onClick={() => setAsOf('')}>回到今天</Button> : null}
      </form>
      {error != null ? (
        <Alert type="error" title={errorText(error)} />
      ) : completion.isPending || matrix.isPending ? (
        <p role="status">档案统计加载中…</p>
      ) : completion.data != null && matrix.data != null ? (
        <>
          <section aria-labelledby="archive-summary">
            <h2 id="archive-summary">档案完成情况</h2>
            <p>
              截至 {completion.data.as_of}
              {asOf === '' ? '（今天）' : '（历史时点）'}（北京时间）
            </p>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr)) 260px',
                gap: 1,
                background: 'var(--color-border, #e4e6ea)',
                border: '1px solid var(--color-border, #e4e6ea)',
                borderRadius: 8,
                overflow: 'hidden',
                marginBottom: 12,
              }}
            >
              {completion.data.categories
                .filter(item => item.supported && item.required != null && item.required > 0)
                .map(item => (
                  <div
                    key={`card-${item.document_type}`}
                    style={{ background: '#fff', padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 6 }}
                  >
                    <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                      {item.label}
                    </span>
                    <span style={{ fontSize: 20, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                      {item.existing ?? 0} / {item.required}
                      <span style={{ fontSize: 12, fontWeight: 400, marginLeft: 6 }}>
                        · {item.completion_rate != null ? `${(item.completion_rate * 100).toFixed(1)}%` : '—'}
                      </span>
                    </span>
                    <div style={{ height: 4, borderRadius: 2, background: '#eef0f2', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${item.completion_rate != null ? Math.round(item.completion_rate * 100) : 0}%`,
                          height: '100%',
                          background: 'var(--ant-color-primary, #0e63e5)',
                        }}
                      />
                    </div>
                  </div>
                ))}
              <div style={{ background: '#fff', padding: 12, display: 'flex', alignItems: 'center' }}>
                <div
                  role="button"
                  tabIndex={0}
                  aria-label="拖入或点击选择多份扫描件"
                  style={{
                    flex: 1,
                    height: '100%',
                    border: '1.5px dashed #c9cdd4',
                    borderRadius: 8,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 2,
                    textAlign: 'center',
                    padding: 8,
                    cursor: 'pointer',
                  }}
                  onClick={() => {
                    window.dispatchEvent(
                      new CustomEvent('archive-batch-pick'),
                    );
                  }}
                  onDragOver={event => {
                    event.preventDefault();
                  }}
                  onDrop={event => {
                    event.preventDefault();
                    const files = Array.from(event.dataTransfer.files ?? []);
                    if (files.length > 0) {
                      window.dispatchEvent(
                        new CustomEvent('archive-batch-drop', { detail: files }),
                      );
                    }
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 600 }}>拖入扫描件</span>
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
                    自动识别类型，再确认挂到哪个对象
                  </span>
                </div>
              </div>
            </div>
            <Table<ArchiveCategory>
              rowKey="document_type"
              dataSource={completion.data.categories}
              pagination={false}
              scroll={{ x: 540 }}
              columns={[
                { title: '档案类型', dataIndex: 'label' },
                { title: '已有 / 应有', render: (_, item) => categoryValue(item) },
                {
                  title: '缺件',
                  render: (_, item) =>
                    item.supported && item.required != null && item.required > 0
                      ? item.missing
                      : '—',
                },
                {
                  title: '完成率',
                  render: (_, item) =>
                    item.supported && item.completion_rate != null
                      ? `${(item.completion_rate * 100).toFixed(1)}%`
                      : '—',
                },
              ]}
            />
            <p>
              尚未关联产权证的物业：{completion.data.unlinked_unit_count}{' '}
              宗。请先核对证照关联，不将每宗物业自动算作缺一本证。
            </p>
          </section>
          <section aria-labelledby="archive-matrix">
            <h2 id="archive-matrix">按物业查看</h2>
            <Table<ArchiveMatrixRow>
              rowKey="unit_id"
              dataSource={matrix.data.items}
              scroll={{ x: 1100 }}
              locale={{ emptyText: '当前范围没有符合条件的在管物业。' }}
              pagination={{
                current: page,
                pageSize: 20,
                total: matrix.data.total,
                showSizeChanger: false,
                onChange: setPage,
              }}
              columns={[
                {
                  title: '物业',
                  render: (_, row) => (
                    <Link
                      to={`${ASSET_OPERATIONS_V5_ROUTES.UNITS}?unit_id=${encodeURIComponent(row.unit_id)}`}
                    >
                      {row.unit_code} · {row.unit_name}
                    </Link>
                  ),
                },
                ...completion.data.categories.map(category => ({
                  title: category.label,
                  key: category.document_type,
                  render: (_: unknown, row: ArchiveMatrixRow) => {
                    const item = row.categories.find(
                      value => value.document_type === category.document_type
                    );
                    return item == null ? '统计不可用' : categoryValue(item);
                  },
                })),
                {
                  title: '缺件对象',
                  render: (_, row) =>
                    row.missing_items.length === 0 ? (
                      '无已知缺件'
                    ) : (
                      <ul className={styles.missing}>
                        {row.missing_items.map(item => (
                          <li key={`${item.target_type}:${item.target_id}:${item.document_type}`}>
                            <Link to={item.href}>{item.label}</Link>
                          </li>
                        ))}
                      </ul>
                    ),
                },
              ]}
            />
          </section>
        </>
      ) : null}
    </div>
  );
}
