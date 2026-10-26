/**
 * 资产运营 · 资产单元列表
 *
 * 四态分离：loading / empty / 403 / error 互不吞并；选中行同步到 URL
 * 查询参数，刷新后恢复同一对象。数据走 React Query，编辑走 React Hook Form
 * 的最小替代（单字段表单直接受控），派生字段（出租状态/面积/出租率）只读。
 */

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Alert, Table, Tag, Input, Button } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type { AssetUnitListItem } from '@/services/assetOperationsService';

import styles from './AssetUnitsPage.module.css';

const STATUS_LABELS: Record<AssetUnitListItem['rentalStatus'], string> = {
  rented: '已出租',
  vacant: '空置',
  non_rentable: '不可租',
};

const STATUS_COLORS: Record<AssetUnitListItem['rentalStatus'], string> = {
  rented: 'blue',
  vacant: 'default',
  non_rentable: 'default',
};

const PAGE_SIZE = 20;

function formatArea(value: number): string {
  return `${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })} ㎡`;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function isScopeForbidden(error: unknown): boolean {
  return (
    error instanceof AssetOperationsError &&
    (error.code === 'PARTY_SCOPE_MISSING' || error.code === 'ASSET_OPS_PERMISSION_DENIED')
  );
}

export function AssetUnitsPage(): React.ReactElement {
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [pagination, setPagination] = useState({ current: 1, pageSize: PAGE_SIZE });
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedUnitId = searchParams.get('unit_id') ?? '';

  const unitsQuery = useQuery({
    queryKey: ['asset-operations-units', appliedSearch, pagination.current],
    queryFn: () =>
      assetOperationsService.listAssetUnits({
        q: appliedSearch.trim() === '' ? undefined : appliedSearch.trim(),
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      }),
  });

  const selectedId = selectedUnitId !== '' ? selectedUnitId : (unitsQuery.data?.items[0]?.id ?? '');
  const detailQuery = useQuery({
    queryKey: ['asset-operations-unit', selectedId],
    queryFn: () => assetOperationsService.getAssetUnit(selectedId),
    enabled: selectedId !== '',
  });

  const invalidate = (): void => {
    void queryClient.invalidateQueries({ queryKey: ['asset-operations-units'] });
    void queryClient.invalidateQueries({
      queryKey: ['asset-operations-unit', selectedId],
    });
  };

  const renameMutation = useMutation({
    mutationFn: (input: { unitId: string; expectedVersion: number; name: string }) =>
      assetOperationsService.updateAssetUnit(input.unitId, {
        expectedVersion: input.expectedVersion,
        name: input.name,
      }),
    onSuccess: invalidate,
  });

  const columns: ColumnsType<AssetUnitListItem> = useMemo(
    () => [
      {
        title: '单元编号',
        dataIndex: 'unitCode',
        key: 'unitCode',
        render: (_: unknown, record: AssetUnitListItem) => record.unitCode,
      },
      { title: '名称', dataIndex: 'name', key: 'name' },
      {
        title: '出租状态',
        key: 'rentalStatus',
        render: (_: unknown, record: AssetUnitListItem) => (
          <Tag color={STATUS_COLORS[record.rentalStatus]}>{STATUS_LABELS[record.rentalStatus]}</Tag>
        ),
      },
      {
        title: '可租面积',
        key: 'rentableArea',
        align: 'right',
        render: (_: unknown, record: AssetUnitListItem) => formatArea(record.rentableArea),
      },
      {
        title: '出租率',
        key: 'occupancyRate',
        align: 'right',
        render: (_: unknown, record: AssetUnitListItem) => formatPercent(record.occupancyRate),
      },
    ],
    []
  );

  const units = unitsQuery.data?.items ?? [];
  const total = unitsQuery.data?.total ?? 0;
  const detail = detailQuery.data ?? null;
  const detailForbidden = isScopeForbidden(detailQuery.error);
  const listForbidden = isScopeForbidden(unitsQuery.error);

  const handleSelect = (unitId: string): void => {
    const next = new URLSearchParams(searchParams);
    next.set('unit_id', unitId);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>资产单元</h1>

      {unitsQuery.isError ? (
        <Alert
          type={listForbidden ? 'warning' : 'error'}
          showIcon
          title={
            listForbidden
              ? '没有可访问的资产范围，请联系管理员配置数据范围。'
              : unitsQuery.error instanceof Error
                ? unitsQuery.error.message
                : '资产单元加载失败'
          }
        />
      ) : null}

      <Input.Search
        aria-label="搜索单元编号、名称或地址"
        placeholder="搜索单元编号、名称或地址"
        value={searchText}
        onChange={event => setSearchText(event.target.value)}
        onSearch={value => {
          setAppliedSearch(value);
          setPagination(previous => ({ ...previous, current: 1 }));
        }}
        allowClear
        style={{ maxWidth: 360 }}
      />

      <div className={styles.layout}>
        <Table<AssetUnitListItem>
          rowKey="id"
          columns={columns}
          scroll={{ x: 640 }}
          dataSource={units}
          loading={unitsQuery.isLoading}
          rowClassName={record => (record.id === selectedId ? 'ant-table-row-selected' : '')}
          onRow={record => ({ onClick: () => handleSelect(record.id) })}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total,
            showSizeChanger: false,
            onChange: (page, pageSize) => setPagination({ current: page, pageSize }),
          }}
          locale={{
            emptyText: unitsQuery.isError ? ' ' : '暂无资产单元，请先完成录入或导入。',
          }}
        />

        <aside className={styles.detailCard} aria-label="资产单元详情">
          {detailQuery.isError ? (
            <Alert
              type={detailForbidden ? 'warning' : 'error'}
              showIcon
              title={
                detailForbidden
                  ? '当前单元不在你的数据范围内。'
                  : detailQuery.error instanceof Error
                    ? detailQuery.error.message
                    : '详情加载失败'
              }
            />
          ) : detailQuery.isLoading ? (
            <p>详情加载中…</p>
          ) : detail == null ? (
            <p>在左侧选择一个资产单元查看详情。</p>
          ) : (
            <div>
              <h2 style={{ fontSize: 16, marginTop: 0 }}>
                {detail.unitCode} · {detail.name}
              </h2>
              <Tag color={STATUS_COLORS[detail.rentalStatus]}>
                {STATUS_LABELS[detail.rentalStatus]}
              </Tag>
              <div style={{ marginTop: 8 }}>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>地址</span>
                  <span className={styles.fieldValue}>{detail.address}</span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>建筑面积</span>
                  <span className={styles.fieldValue}>{formatArea(detail.buildingArea)}</span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>可租面积</span>
                  <span className={styles.fieldValue}>{formatArea(detail.rentableArea)}</span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>已租面积</span>
                  <span className={styles.fieldValue}>{formatArea(detail.rentedArea)}</span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>在管起始</span>
                  <span className={styles.fieldValue}>{detail.managedFrom}</span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>当前终端合同</span>
                  <span className={styles.fieldValue}>
                    {detail.terminalContractIds.length === 0
                      ? '暂无'
                      : detail.terminalContractIds.join('、')}
                  </span>
                </div>
              </div>
              <RenameForm
                unit={detail}
                pending={renameMutation.isPending}
                errorMessage={
                  renameMutation.isError && renameMutation.error instanceof Error
                    ? renameMutation.error.message
                    : null
                }
                onSubmit={name =>
                  renameMutation.mutate({
                    unitId: detail.id,
                    expectedVersion: detail.version,
                    name,
                  })
                }
              />
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function RenameForm(props: {
  unit: AssetUnitListItem;
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (name: string) => void;
}): React.ReactElement {
  const [name, setName] = useState(props.unit.name);
  const trimmed = name.trim();
  const changed = trimmed !== props.unit.name && trimmed !== '';

  return (
    <form
      style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}
      onSubmit={event => {
        event.preventDefault();
        if (changed) {
          props.onSubmit(trimmed);
        }
      }}
    >
      <label htmlFor="unit-rename-input" style={{ fontSize: 13 }}>
        单元名称
      </label>
      <Input id="unit-rename-input" value={name} onChange={event => setName(event.target.value)} />
      {props.errorMessage != null ? (
        <Alert type="error" showIcon title={props.errorMessage} />
      ) : null}
      <Button
        type="primary"
        htmlType="submit"
        disabled={!changed || props.pending}
        loading={props.pending}
        style={{ alignSelf: 'flex-start' }}
      >
        保存名称
      </Button>
    </form>
  );
}

export default AssetUnitsPage;
