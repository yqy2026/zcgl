/**
 * 资产运营 · 物业台账（资产单元列表）
 *
 * 对齐原型 asset-ops-v5「物业」页：分段筛选（带数量）/ 项目下拉 / 搜索
 * （地址、单元、租户、产权证号）/ 按项目分组表格 / 列（业态·产权方·面积·
 * 性质·考核·出租状态·产权证）/ 详情栏（空置原因+预计起租、租赁时间轴、
 * 拆分·合并单元、导出台账）。四态分离与 URL 选中态沿用既有模式；派生字段只读。
 */

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Button, Input, Modal, Segmented, Select, Table, Tabs, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { ASSET_OPERATIONS_V5_ROUTES } from '@/constants/routes';
import { assetOperationsService, AssetOperationsError } from '@/services/assetOperationsService';
import type { AssetUnitListItem } from '@/services/assetOperationsService';
import { occupancyReportService } from '@/services/occupancyReportService';

import CapabilityGuard from '@/components/System/CapabilityGuard';
import styles from './AssetUnitsPage.module.css';
import ChangeTimelinePanel from './ChangeTimelinePanel';
import OwnerPartySelect from './OwnerPartySelect';
import { CertificateLink, CertificateControls } from './CertificateActions';

const STATUS_LABELS: Record<AssetUnitListItem['rentalStatus'], string> = {
  rented: '已出租',
  vacant: '空置可租',
  non_rentable: '不可租',
};

const STATUS_COLORS: Record<AssetUnitListItem['rentalStatus'], string> = {
  rented: 'blue',
  vacant: 'green',
  non_rentable: 'default',
};

const VACANCY_LABELS: Record<string, string> = {
  renovation: '装修中',
  marketing: '招商中',
  repossession: '待收回',
  pending_contract: '有意向未签',
  other: '其他',
};

const ASSESSMENT_LABELS: Record<NonNullable<AssetUnitListItem['assessment']>, string> = {
  included: '纳入',
  excluded: '不纳入',
  pending: '待确认',
};

const ASSESSMENT_COLORS: Record<NonNullable<AssetUnitListItem['assessment']>, string> = {
  included: 'blue',
  excluded: 'default',
  pending: 'gold',
};

type UnitFilter = 'all' | 'in_assessment' | 'vacant' | 'non_rentable' | 'missing_certificate';

const PAGE_SIZE = 20;
const CURRENT_YEAR = new Date().getFullYear();
const EMPTY_UNITS: AssetUnitListItem[] = [];

function formatArea(value: number): string {
  return `${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })} ㎡`;
}

function isScopeForbidden(error: unknown): boolean {
  return (
    error instanceof AssetOperationsError &&
    (error.code === 'PARTY_SCOPE_MISSING' ||
      error.code === 'PARTY_SCOPE_INVALID_ORGANIZATION' ||
      error.code === 'PARTY_SCOPE_INVALID_PARTY' ||
      error.code === 'PARTY_SCOPE_INVALID_BINDING' ||
      error.code === 'ASSET_OPS_PERMISSION_DENIED')
  );
}

export function AssetUnitsPage(): React.ReactElement {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [ownerPartyId, setOwnerPartyId] = useState<string | undefined>();
  const [projectId, setProjectId] = useState<string | undefined>();
  const [usageType, setUsageType] = useState<string | undefined>();
  const [unitFilter, setUnitFilter] = useState<UnitFilter>('all');
  const [pagination, setPagination] = useState({ current: 1, pageSize: PAGE_SIZE });
  const [searchParams, setSearchParams] = useSearchParams();
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const selectedUnitId = searchParams.get('unit_id') ?? '';

  // 考核范围按运营主体+年度解析（与报送页同源），未就绪时考核列显示 —。
  const operatorQuery = useQuery({
    queryKey: ['occupancy-operator-parties'],
    queryFn: () => occupancyReportService.listOperatorParties(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const operatorPartyId = operatorQuery.data?.[0]?.id;

  const projectsQuery = useQuery({
    queryKey: ['asset-operations-unit-project-options'],
    queryFn: () => assetOperationsService.listAssetUnitProjectOptions(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const unitsQuery = useQuery({
    queryKey: [
      'asset-operations-units',
      appliedSearch,
      ownerPartyId ?? '',
      projectId ?? '',
      usageType ?? '',
      unitFilter,
      operatorPartyId ?? '',
      pagination.current,
    ],
    queryFn: () =>
      assetOperationsService.listAssetUnits({
        q: appliedSearch.trim() === '' ? undefined : appliedSearch.trim(),
        ownerPartyId,
        projectId,
        usageType,
        filter: unitFilter === 'all' ? undefined : unitFilter,
        assessmentOperatorPartyId: operatorPartyId,
        assessmentYear: CURRENT_YEAR,
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
      }),
  });

  const usageTypesQuery = useQuery({
    queryKey: ['asset-operations-unit-usage-types'],
    queryFn: () => assetOperationsService.listAssetUnitUsageTypes(),
    staleTime: 5 * 60 * 1000,
    retry: false,
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

  // ---- 项目分组行类型（组头跨整行，不可选、可折叠）----
  interface GroupRow {
    key: string;
    isGroup: true;
    projectName: string;
    count: number;
    children: AssetUnitListItem[];
  }
  type ListRow = GroupRow | (AssetUnitListItem & { isGroup?: false });
  const isGroupRow = (record: ListRow): record is GroupRow => (record as GroupRow).isGroup === true;
  const groupCell = { onCell: (record: ListRow) => (isGroupRow(record) ? { colSpan: 0 } : {}) };

  const columns: ColumnsType<ListRow> = useMemo(
    () => [
      {
        title: '资产单元',
        key: 'unit',
        onCell: (record: ListRow) => (isGroupRow(record) ? { colSpan: 9 } : ({} as object)),
        render: (_: unknown, record: ListRow) =>
          isGroupRow(record) ? (
            <b style={{ fontSize: 13 }}>
              {record.projectName}
              <span
                style={{
                  marginLeft: 8,
                  fontSize: 12,
                  fontWeight: 400,
                  color: 'var(--color-text-secondary)',
                }}
              >
                {record.count} 个单元
              </span>
            </b>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
              <span style={{ fontWeight: 500 }}>{record.name}</span>
              <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                {record.unitCode}
                {record.projectName !== '' ? ` · ${record.projectName}` : ''}
              </span>
            </div>
          ),
      },
      {
        title: '业态',
        dataIndex: 'usageType',
        key: 'usageType',
        width: 90,
        ...groupCell,
        render: (value: string) => value || '—',
      },
      {
        title: '产权方',
        key: 'owner',
        width: 150,
        ellipsis: true,
        ...groupCell,
        render: (_: unknown, record: ListRow) =>
          isGroupRow(record) ? null : record.ownerPartyName || '—',
      },
      {
        title: '建筑面积㎡',
        key: 'buildingArea',
        align: 'right',
        width: 110,
        ...groupCell,
        render: (_: unknown, record: ListRow) =>
          isGroupRow(record) ? null : formatArea(record.buildingArea),
      },
      {
        title: '可租面积㎡',
        key: 'rentableArea',
        align: 'right',
        width: 110,
        ...groupCell,
        render: (_: unknown, record: ListRow) =>
          isGroupRow(record) ? null : formatArea(record.rentableArea),
      },
      {
        title: '性质',
        key: 'nature',
        width: 90,
        ...groupCell,
        render: (_: unknown, record: ListRow) =>
          isGroupRow(record) ? null : record.isOperating ? '经营性' : '非经营',
      },
      {
        title: `${CURRENT_YEAR} 考核`,
        key: 'assessment',
        width: 90,
        ...groupCell,
        render: (_: unknown, record: ListRow) =>
          isGroupRow(record) || record.assessment == null ? (
            '—'
          ) : (
            <Tag color={ASSESSMENT_COLORS[record.assessment]}>
              {ASSESSMENT_LABELS[record.assessment]}
            </Tag>
          ),
      },
      {
        title: '出租状态',
        key: 'rentalStatus',
        width: 170,
        ...groupCell,
        render: (_: unknown, record: ListRow) =>
          isGroupRow(record) ? null : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Tag color={STATUS_COLORS[record.rentalStatus]}>
                {STATUS_LABELS[record.rentalStatus]}
              </Tag>
              {record.rentalStatus === 'rented' && record.currentTenantName != null ? (
                <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                  {record.currentTenantName} · 至 {record.currentContractEndDate ?? '—'}
                </span>
              ) : null}
              {record.rentalStatus === 'vacant' && record.vacancyReason != null ? (
                <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                  {VACANCY_LABELS[record.vacancyReason] ?? record.vacancyReason}
                  {record.expectedLeaseStart != null
                    ? ` · 预计 ${record.expectedLeaseStart} 起`
                    : ''}
                </span>
              ) : null}
            </div>
          ),
      },
      {
        title: '产权证',
        key: 'certificates',
        width: 80,
        align: 'center',
        ...groupCell,
        render: (_: unknown, record: ListRow) =>
          isGroupRow(record) ? null : record.certificateCount > 0 ? (
            `${record.certificateCount} 本`
          ) : (
            <span style={{ color: 'var(--color-error, #cf1322)' }}>缺</span>
          ),
      },
    ],
    []
  );

  const units = unitsQuery.data?.items ?? EMPTY_UNITS;
  const total = unitsQuery.data?.total ?? 0;
  const counts = unitsQuery.data?.counts ?? null;
  const detail = detailQuery.data ?? null;
  const detailForbidden = isScopeForbidden(detailQuery.error);
  const listForbidden = isScopeForbidden(unitsQuery.error);

  // 分页内按项目聚成组头行（组头不可选，展开显示单元）。
  const tableRows: ListRow[] = useMemo(() => {
    const groups = new Map<string, { projectName: string; children: AssetUnitListItem[] }>();
    for (const unit of units) {
      const key = unit.projectId || '未分组';
      let group = groups.get(key);
      if (group == null) {
        group = {
          projectName: unit.projectName !== '' ? unit.projectName : key,
          children: [],
        };
        groups.set(key, group);
      }
      group.children.push(unit);
    }
    return Array.from(groups.entries()).map(([key, group]) => ({
      key: `group-${key}`,
      isGroup: true as const,
      projectName: group.projectName,
      count: group.children.length,
      children: group.children,
    }));
  }, [units]);

  // 组头默认展开（数据异步到达，defaultExpandAllRows 不会重放，需受控）。
  const [expandedKeys, setExpandedKeys] = useState<readonly React.Key[]>([]);
  useEffect(() => {
    setExpandedKeys(tableRows.map(row => (isGroupRow(row) ? row.key : row.id)));
  }, [tableRows]);

  const handleSelect = (unitId: string): void => {
    const next = new URLSearchParams(searchParams);
    next.set('unit_id', unitId);
    setSearchParams(next, { replace: true });
  };

  const exportLedger = (): void => {
    setExportError(null);
    setExporting(true);
    assetOperationsService
      .exportAssetUnits({
        q: appliedSearch.trim() === '' ? undefined : appliedSearch.trim(),
        ownerPartyId,
        projectId,
        usageType,
        filter: unitFilter === 'all' ? undefined : unitFilter,
        assessmentOperatorPartyId: operatorPartyId,
        assessmentYear: CURRENT_YEAR,
      })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `asset-units-${CURRENT_YEAR}.xlsx`;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
      })
      .catch((error: unknown) => {
        setExportError(error instanceof Error ? error.message : '物业台账导出失败。');
      })
      .finally(() => {
        setExporting(false);
      });
  };

  const filterOptions: { value: UnitFilter; label: string; count: number | null }[] = [
    { value: 'all', label: '全部', count: counts?.all ?? null },
    { value: 'in_assessment', label: '纳入报送', count: counts?.inAssessment ?? null },
    { value: 'vacant', label: '空置可租', count: counts?.vacant ?? null },
    { value: 'non_rentable', label: '不可租·非经营', count: counts?.nonRentable ?? null },
    {
      value: 'missing_certificate',
      label: '缺产权证',
      count: counts?.missingCertificate ?? null,
    },
  ];

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>物业</h1>

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

      <div className={styles.toolbarColumn}>
        <Segmented
          aria-label="视图筛选"
          value={unitFilter}
          onChange={value => {
            setUnitFilter(value as UnitFilter);
            setPagination(previous => ({ ...previous, current: 1 }));
          }}
          options={filterOptions.map(option => ({
            value: option.value,
            label: `${option.label}${option.count != null ? ` ${option.count}` : ''}`,
          }))}
        />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <Input.Search
            aria-label="搜地址、单元、租户、产权证号"
            placeholder="搜地址、单元、租户、产权证号"
            value={searchText}
            onChange={event => setSearchText(event.target.value)}
            onSearch={value => {
              setAppliedSearch(value);
              setPagination(previous => ({ ...previous, current: 1 }));
            }}
            allowClear
            style={{ maxWidth: 300 }}
          />
          <Select
            aria-label="按项目筛选"
            placeholder="全部项目"
            allowClear
            style={{ minWidth: 160 }}
            value={projectId}
            loading={projectsQuery.isLoading}
            onChange={value => {
              setProjectId(value);
              setPagination(previous => ({ ...previous, current: 1 }));
            }}
            options={(projectsQuery.data ?? []).map(project => ({
              value: project.projectId,
              label: project.projectName,
            }))}
          />
          <OwnerPartySelect
            value={ownerPartyId}
            onChange={value => {
              setOwnerPartyId(value);
              setPagination(previous => ({ ...previous, current: 1 }));
            }}
          />
          <Select
            aria-label="按业态筛选"
            placeholder="全部业态"
            allowClear
            style={{ minWidth: 140 }}
            value={usageType}
            loading={usageTypesQuery.isLoading}
            onChange={value => {
              setUsageType(value);
              setPagination(previous => ({ ...previous, current: 1 }));
            }}
            options={(usageTypesQuery.data ?? []).map(type => ({
              value: type,
              label: type,
            }))}
          />
          <Button loading={exporting} onClick={exportLedger}>
            导出台账
          </Button>
          <Button onClick={() => navigate(ASSET_OPERATIONS_V5_ROUTES.IMPORTS)}>批量导入单元</Button>
        </div>
        {exportError != null ? <Alert type="error" showIcon title={exportError} /> : null}
      </div>

      <div className={styles.layout}>
        <Table<ListRow>
          rowKey={record => (isGroupRow(record) ? record.key : record.id)}
          columns={columns}
          scroll={{ x: 980 }}
          dataSource={tableRows}
          loading={unitsQuery.isLoading}
          expandable={{
            expandedRowKeys: expandedKeys,
            onExpandedRowsChange: setExpandedKeys,
          }}
          rowClassName={record =>
            !isGroupRow(record) && record.id === selectedId ? 'ant-table-row-selected' : ''
          }
          onRow={record => ({
            onClick: () => {
              if (!isGroupRow(record)) {
                handleSelect(record.id);
              }
            },
          })}
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
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <Tag color={STATUS_COLORS[detail.rentalStatus]}>
                  {STATUS_LABELS[detail.rentalStatus]}
                </Tag>
                {detail.assessment != null ? (
                  <Tag color={ASSESSMENT_COLORS[detail.assessment]}>
                    {CURRENT_YEAR} 考核 · {ASSESSMENT_LABELS[detail.assessment]}
                  </Tag>
                ) : null}
                {detail.certificateCount === 0 ? <Tag color="red">缺产权证</Tag> : null}
              </div>
              <div style={{ marginTop: 8 }}>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>地址</span>
                  <span className={styles.fieldValue}>{detail.address}</span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>项目</span>
                  <span className={styles.fieldValue}>{detail.projectName || '—'}</span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>产权方</span>
                  <span className={styles.fieldValue}>
                    {detail.ownerPartyName || detail.ownerPartyId}
                  </span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>业态</span>
                  <span className={styles.fieldValue}>{detail.usageType || '—'}</span>
                </div>
                <div className={styles.fieldRow}>
                  <span className={styles.fieldLabel}>性质</span>
                  <span className={styles.fieldValue}>
                    {detail.isOperating ? '经营性' : '非经营'}
                  </span>
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
                    {detail.currentContractNumber != null
                      ? `${detail.currentContractNumber}${
                          detail.currentTenantName != null ? ` · ${detail.currentTenantName}` : ''
                        }`
                      : detail.terminalContractIds.length === 0
                        ? '暂无'
                        : detail.terminalContractIds.join('、')}
                  </span>
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <Link
                  aria-label="查看考核范围"
                  to={`${ASSET_OPERATIONS_V5_ROUTES.OCCUPANCY_REPORTS}?year=${CURRENT_YEAR}`}
                >
                  考核范围
                </Link>
              </div>
              {detail.rentalStatus === 'vacant' ? (
                <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
                  <VacancyNoteEditor
                    unit={detail}
                    onSaved={() => {
                      void queryClient.invalidateQueries({
                        queryKey: ['asset-operations-units'],
                      });
                      void queryClient.invalidateQueries({
                        queryKey: ['asset-operations-unit', detail.id],
                      });
                    }}
                  />
                </CapabilityGuard>
              ) : null}
              <LeaseTimeline unitId={detail.id} />
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
              <UnitCertificates key={detail.id} unitId={detail.id} />
              <CapabilityGuard action="write" resource="asset_ops" fallback={<></>}>
                <BoundaryActionsModal
                  unit={detail}
                  onDone={() => {
                    void queryClient.invalidateQueries({
                      queryKey: ['asset-operations-units'],
                    });
                    void queryClient.invalidateQueries({
                      queryKey: ['asset-operations-unit', detail.id],
                    });
                  }}
                />
              </CapabilityGuard>
              <ChangeTimelinePanel targetType="asset_unit" targetId={detail.id} />
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function VacancyNoteEditor(props: {
  unit: AssetUnitListItem;
  onSaved: () => void;
}): React.ReactElement {
  const [reason, setReason] = useState<string | null>(props.unit.vacancyReason);
  const [expectedStart, setExpectedStart] = useState(props.unit.expectedLeaseStart ?? '');
  const mutation = useMutation({
    mutationFn: () =>
      assetOperationsService.updateVacancyNote(props.unit.id, {
        expectedVersion: props.unit.version,
        ...(reason != null ? { vacancyReason: reason } : {}),
        ...(expectedStart.trim() !== ''
          ? { expectedLeaseStart: `${expectedStart.trim()}-01` }
          : {}),
      }),
    onSuccess: () => props.onSaved(),
  });
  return (
    <section className={styles.vacancyBlock} aria-label="空置原因">
      <b style={{ fontSize: 13 }}>空置原因</b>
      <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>备注，不影响计宗</span>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {Object.entries(VACANCY_LABELS).map(([value, label]) => (
          <Button
            key={value}
            size="small"
            type={reason === value ? 'primary' : 'default'}
            onClick={() => {
              setReason(reason === value ? null : value);
            }}
          >
            {label}
          </Button>
        ))}
      </div>
      <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        预计起租
        <input
          type="month"
          aria-label="预计起租月份"
          value={expectedStart}
          onChange={event => setExpectedStart(event.target.value)}
          style={{
            paddingTop: 2,
            paddingLeft: 8,
            paddingRight: 8,
            borderRadius: 4,
            borderWidth: 1,
            borderStyle: 'solid',
            borderColor: '#d9d9d9',
          }}
        />
      </label>
      {mutation.isError ? (
        <Alert
          type="error"
          showIcon
          title={mutation.error instanceof Error ? mutation.error.message : '保存失败'}
        />
      ) : null}
      <Button size="small" loading={mutation.isPending} onClick={() => mutation.mutate()}>
        保存空置备注
      </Button>
    </section>
  );
}

interface CoverageInterval {
  contractKind: 'terminal' | 'upstream';
  contractId: string;
  contractNumber: string;
  startDate: string;
  endDate: string;
}

function LeaseTimeline({ unitId }: { unitId: string }): React.ReactElement {
  const navigate = useNavigate();
  const query = useQuery({
    queryKey: ['asset-unit-coverage-history', unitId],
    queryFn: async (): Promise<CoverageInterval[]> => {
      const result = await assetOperationsService.getCoverageHistory(unitId);
      return result;
    },
  });
  const today = new Date().toISOString().slice(0, 10);
  const items = query.data ?? [];
  const domainStart = useMemo(() => {
    const starts = items.map(item => item.startDate).filter(value => value !== '');
    const anchor = new Date(today);
    anchor.setMonth(anchor.getMonth() - 18);
    const anchorText = anchor.toISOString().slice(0, 10);
    return starts.reduce((min, value) => (value < min ? value : min), anchorText);
  }, [items, today]);
  const domainEnd = useMemo(() => {
    const ends = items.map(item => item.endDate).filter(value => value !== '');
    const anchor = new Date(today);
    anchor.setMonth(anchor.getMonth() + 6);
    const anchorText = anchor.toISOString().slice(0, 10);
    return ends.reduce((max, value) => (value > max ? value : max), anchorText);
  }, [items, today]);

  const position = (value: string): number => {
    const start = new Date(domainStart).getTime();
    const end = new Date(domainEnd).getTime();
    const current = new Date(value).getTime();
    if (end <= start) {
      return 0;
    }
    return Math.min(Math.max(((current - start) / (end - start)) * 100, 0), 100);
  };

  const lanes: { kind: 'terminal' | 'upstream'; label: string }[] = [
    { kind: 'terminal', label: '终端合同' },
    { kind: 'upstream', label: '上游合同' },
  ];

  return (
    <section aria-label="租赁时间轴" style={{ marginTop: 12 }}>
      <b style={{ fontSize: 13 }}>租赁时间轴</b>
      {query.isLoading ? (
        <p role="status">时间轴加载中…</p>
      ) : query.isError ? (
        <p style={{ color: 'var(--color-text-secondary)' }}>时间轴暂不可用。</p>
      ) : items.length === 0 ? (
        <p style={{ color: 'var(--color-text-secondary)' }}>暂无合同覆盖记录。</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {lanes.map(lane => (
            <div key={lane.kind} style={{ position: 'relative', height: 22 }}>
              <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
                {lane.label}
              </span>
              <div
                style={{
                  position: 'relative',
                  height: 14,
                  borderRadius: 4,
                  background:
                    'repeating-linear-gradient(135deg, #fafbfc 0 0.25rem, #e9ecef 0.25rem 0.5rem)',
                  marginTop: 2,
                }}
              >
                {items
                  .filter(item => item.contractKind === lane.kind)
                  .map(item => (
                    <button
                      key={`${item.contractKind}-${item.contractId}`}
                      type="button"
                      title={`${item.contractNumber} ${item.startDate} ~ ${item.endDate}`}
                      onClick={() => {
                        navigate(
                          item.contractKind === 'terminal'
                            ? `/asset-operations/contracts/terminal?contract_id=${encodeURIComponent(item.contractId)}`
                            : `/asset-operations/contracts/upstream?contract_id=${encodeURIComponent(item.contractId)}`
                        );
                      }}
                      style={{
                        position: 'absolute',
                        left: `${position(item.startDate)}%`,
                        width: `${Math.max(position(item.endDate) - position(item.startDate), 1)}%`,
                        top: 0,
                        bottom: 0,
                        borderRadius: 4,
                        border: 0,
                        background:
                          item.contractKind === 'terminal'
                            ? 'var(--ant-color-primary, #0e63e5)'
                            : 'var(--color-text-secondary, #646a73)',
                        opacity: 0.85,
                        cursor: 'pointer',
                      }}
                    />
                  ))}
              </div>
            </div>
          ))}
          <div
            style={{
              position: 'relative',
              height: 6,
              background: '#f2f3f5',
              borderRadius: 3,
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: `${position(today)}%`,
                top: -2,
                width: 2,
                height: 10,
                background: 'var(--color-error, #cf1322)',
              }}
              title="今天"
            />
          </div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 11,
              color: 'var(--color-text-tertiary)',
            }}
          >
            <span>{domainStart}</span>
            <span style={{ color: 'var(--color-error, #cf1322)' }}>｜今天</span>
            <span>{domainEnd}</span>
          </div>
          <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
            上层终端合同 · 下层上游合同 · 斜纹为空置
          </span>
        </div>
      )}
    </section>
  );
}

function BoundaryActionsModal(props: {
  unit: AssetUnitListItem;
  onDone: () => void;
}): React.ReactElement {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
      <Button onClick={() => setOpen(true)}>拆分 / 合并单元</Button>
      {open ? (
        <BoundaryActionsModalInner
          unit={props.unit}
          onClose={() => setOpen(false)}
          onDone={props.onDone}
        />
      ) : null}
    </div>
  );
}

function BoundaryActionsModalInner(props: {
  unit: AssetUnitListItem;
  onClose: () => void;
  onDone: () => void;
}): React.ReactElement {
  const [tab, setTab] = useState<'split' | 'merge'>('split');
  return (
    <Modal
      open
      title="调整资产单元"
      width={580}
      onCancel={props.onClose}
      footer={null}
      destroyOnHidden
    >
      <Tabs
        activeKey={tab}
        onChange={key => setTab(key as 'split' | 'merge')}
        items={[
          {
            key: 'split',
            label: '拆分',
            children: <SplitForm unit={props.unit} onClose={props.onClose} onDone={props.onDone} />,
          },
          {
            key: 'merge',
            label: '合并',
            children: <MergeForm unit={props.unit} onClose={props.onClose} onDone={props.onDone} />,
          },
        ]}
      />
    </Modal>
  );
}

function PreviewImpact({ preview }: { preview: Record<string, unknown> }): React.ReactElement {
  const impact = preview['impact'] as Record<string, unknown> | undefined;
  const warnings = (preview['warnings'] as string[] | undefined) ?? [];
  return (
    <div
      style={{
        background: '#eef4fe',
        borderRadius: 8,
        paddingTop: 10,
        paddingLeft: 12,
        paddingRight: 12,
        paddingBottom: 10,
        fontSize: 13,
      }}
    >
      {impact != null ? (
        <div>
          原单元停止计宗：{String(impact['source_units_stop_on'] ?? '—')}；新单元起计：
          {String(impact['result_units_start_on'] ?? '—')}；宗数变化：
          {String(impact['unit_count_delta'] ?? '—')}。历史月份不变。
        </div>
      ) : (
        <div>预览已生成，确认后生效。</div>
      )}
      {warnings.length > 0 ? (
        <div style={{ color: 'var(--color-error, #cf1322)', marginTop: 4 }}>
          {warnings.join('；')}
        </div>
      ) : null}
    </div>
  );
}

function SplitForm(props: {
  unit: AssetUnitListItem;
  onClose: () => void;
  onDone: () => void;
}): React.ReactElement {
  const [effectiveDate, setEffectiveDate] = useState('');
  const [parts, setParts] = useState([
    { unitCode: '', name: '', buildingArea: '', rentableArea: '' },
    { unitCode: '', name: '', buildingArea: '', rentableArea: '' },
  ]);
  const [reason, setReason] = useState('');
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const filled = parts.every(
    part =>
      part.unitCode.trim() !== '' &&
      part.name.trim() !== '' &&
      part.buildingArea.trim() !== '' &&
      part.rentableArea.trim() !== ''
  );
  const rentableSum = parts.reduce((sum, part) => sum + (Number(part.rentableArea) || 0), 0);
  const buildingSum = parts.reduce((sum, part) => sum + (Number(part.buildingArea) || 0), 0);
  const sumOk =
    Math.abs(rentableSum - props.unit.rentableArea) < 0.01 &&
    Math.abs(buildingSum - props.unit.buildingArea) < 0.01;

  const run = async (action: 'preview' | 'commit'): Promise<void> => {
    setError(null);
    setPending(true);
    try {
      if (action === 'preview') {
        const result = await assetOperationsService.previewAssetUnitSplit(props.unit.id, {
          effectiveDate,
          parts: parts.map(part => ({
            unitCode: part.unitCode.trim(),
            name: part.name.trim(),
            landArea: 0,
            buildingArea: Number(part.buildingArea),
            rentableArea: Number(part.rentableArea),
          })),
        });
        setPreview(result);
      } else if (preview != null) {
        await assetOperationsService.commitAssetUnitSplit(props.unit.id, {
          previewToken: String(preview['preview_token'] ?? ''),
          reason,
          expectedVersion: props.unit.version,
        });
        props.onDone();
        props.onClose();
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '操作失败');
    } finally {
      setPending(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
        生效日期
        <input
          type="date"
          aria-label="拆分生效日期"
          value={effectiveDate}
          onChange={event => setEffectiveDate(event.target.value)}
        />
      </label>
      <b style={{ fontSize: 13 }}>拆成以下单元</b>
      {parts.map((part, index) => (
        <div
          key={index}
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 6.875rem 6.875rem 1.75rem',
            gap: 8,
          }}
        >
          <input
            aria-label={`新单元编号 ${index + 1}`}
            placeholder="单元编号"
            value={part.unitCode}
            onChange={event => {
              const next = [...parts];
              next[index] = { ...part, unitCode: event.target.value };
              setParts(next);
            }}
          />
          <input
            aria-label={`新单元名称 ${index + 1}`}
            placeholder="名称"
            value={part.name}
            onChange={event => {
              const next = [...parts];
              next[index] = { ...part, name: event.target.value };
              setParts(next);
            }}
          />
          <input
            aria-label={`新单元建筑面积 ${index + 1}`}
            placeholder="建筑面积㎡"
            value={part.buildingArea}
            onChange={event => {
              const next = [...parts];
              next[index] = { ...part, buildingArea: event.target.value };
              setParts(next);
            }}
          />
          <input
            aria-label={`新单元可租面积 ${index + 1}`}
            placeholder="可租面积㎡"
            value={part.rentableArea}
            onChange={event => {
              const next = [...parts];
              next[index] = { ...part, rentableArea: event.target.value };
              setParts(next);
            }}
          />
          {parts.length > 2 ? (
            <button
              type="button"
              aria-label={`移除新单元 ${index + 1}`}
              onClick={() => setParts(parts.filter((_, i) => i !== index))}
            >
              ×
            </button>
          ) : (
            <span />
          )}
        </div>
      ))}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          type="button"
          style={{ color: 'var(--ant-color-primary, #0e63e5)' }}
          onClick={() =>
            setParts([...parts, { unitCode: '', name: '', buildingArea: '', rentableArea: '' }])
          }
        >
          ＋ 再加一个
        </button>
        <span
          style={{
            fontSize: 12,
            color: sumOk ? 'var(--color-success, #237804)' : 'var(--color-error, #cf1322)',
          }}
        >
          面积合计 {buildingSum.toLocaleString('zh-CN')} / 原{' '}
          {props.unit.buildingArea.toLocaleString('zh-CN')} ㎡ · {sumOk ? '一致' : '不一致'}
        </span>
      </div>
      {error != null ? <Alert type="error" showIcon title={error} /> : null}
      {preview != null ? <PreviewImpact preview={preview} /> : null}
      {preview != null ? (
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
          原因（必填，写入变更记录）
          <Input.TextArea
            aria-label="拆分原因"
            value={reason}
            onChange={event => setReason(event.target.value)}
            rows={2}
          />
        </label>
      ) : null}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        <Button onClick={props.onClose}>取消</Button>
        {preview == null ? (
          <Button
            type="primary"
            loading={pending}
            disabled={!filled || effectiveDate === '' || !sumOk}
            onClick={() => {
              void run('preview');
            }}
          >
            预览拆分影响
          </Button>
        ) : (
          <Button
            type="primary"
            loading={pending}
            disabled={reason.trim() === ''}
            onClick={() => {
              void run('commit');
            }}
          >
            确认拆分
          </Button>
        )}
      </div>
    </div>
  );
}

function MergeForm(props: {
  unit: AssetUnitListItem;
  onClose: () => void;
  onDone: () => void;
}): React.ReactElement {
  const [sourceIds, setSourceIds] = useState<string[]>([props.unit.id]);
  const [effectiveDate, setEffectiveDate] = useState('');
  const [unitCode, setUnitCode] = useState('');
  const [name, setName] = useState('');
  const [reason, setReason] = useState('');
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const candidatesQuery = useQuery({
    queryKey: ['asset-operations-units-merge-candidates'],
    queryFn: () => assetOperationsService.listAssetUnits({ limit: 200, offset: 0 }),
    staleTime: 60 * 1000,
    retry: false,
  });

  const run = async (action: 'preview' | 'commit'): Promise<void> => {
    setError(null);
    setPending(true);
    try {
      if (action === 'preview') {
        const result = await assetOperationsService.previewAssetUnitMerge({
          sourceUnitIds: sourceIds,
          effectiveDate,
          resultUnitCode: unitCode.trim(),
          resultName: name.trim(),
        });
        setPreview(result);
      } else if (preview != null) {
        const versions: Record<string, number> = {};
        for (const candidate of candidatesQuery.data?.items ?? []) {
          if (sourceIds.includes(candidate.id)) {
            versions[candidate.id] = candidate.version;
          }
        }
        await assetOperationsService.commitAssetUnitMerge({
          previewToken: String(preview['preview_token'] ?? ''),
          reason,
          expectedVersions: versions,
        });
        props.onDone();
        props.onClose();
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '操作失败');
    } finally {
      setPending(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
        生效日期
        <input
          type="date"
          aria-label="合并生效日期"
          value={effectiveDate}
          onChange={event => setEffectiveDate(event.target.value)}
        />
      </label>
      <label style={{ fontSize: 13 }}>
        和哪些单元合并 · 同一份上游合同内
        <Select
          aria-label="选择合并单元"
          mode="multiple"
          style={{ width: '100%' }}
          value={sourceIds}
          onChange={setSourceIds}
          options={(candidatesQuery.data?.items ?? []).map(unit => ({
            value: unit.id,
            label: `${unit.name}（${unit.unitCode}）`,
          }))}
        />
      </label>
      <label style={{ fontSize: 13 }}>
        新单元编号
        <Input
          aria-label="合并后单元编号"
          value={unitCode}
          onChange={event => setUnitCode(event.target.value)}
        />
      </label>
      <label style={{ fontSize: 13 }}>
        新单元名称
        <Input
          aria-label="合并后单元名称"
          value={name}
          onChange={event => setName(event.target.value)}
        />
      </label>
      {error != null ? <Alert type="error" showIcon title={error} /> : null}
      {preview != null ? <PreviewImpact preview={preview} /> : null}
      {preview != null ? (
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
          原因（必填，写入变更记录）
          <Input.TextArea
            aria-label="合并原因"
            value={reason}
            onChange={event => setReason(event.target.value)}
            rows={2}
          />
        </label>
      ) : null}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        <Button onClick={props.onClose}>取消</Button>
        {preview == null ? (
          <Button
            type="primary"
            loading={pending}
            disabled={
              sourceIds.length < 2 ||
              effectiveDate === '' ||
              unitCode.trim() === '' ||
              name.trim() === ''
            }
            onClick={() => {
              void run('preview');
            }}
          >
            预览合并影响
          </Button>
        ) : (
          <Button
            type="primary"
            loading={pending}
            disabled={reason.trim() === ''}
            onClick={() => {
              void run('commit');
            }}
          >
            确认合并
          </Button>
        )}
      </div>
    </div>
  );
}

function UnitCertificates({ unitId }: { unitId: string }): React.ReactElement {
  const query = useQuery({
    queryKey: ['asset-operations-unit-certificates', unitId],
    queryFn: () => assetOperationsService.listAssetUnitCertificates(unitId),
  });
  return (
    <section className={styles.certificates} aria-label="关联产权证">
      <h3>关联产权证</h3>
      <CertificateLink unitId={unitId} />
      {query.isError ? (
        <>
          <Alert
            type={isScopeForbidden(query.error) ? 'warning' : 'error'}
            showIcon
            title={
              isScopeForbidden(query.error)
                ? '没有可访问的产权证范围，请联系管理员。'
                : '产权证加载失败，请重新加载。'
            }
          />
          <Button onClick={() => void query.refetch()}>重新加载产权证</Button>
        </>
      ) : query.isLoading ? (
        <p role="status">产权证加载中…</p>
      ) : (query.data?.length ?? 0) === 0 ? (
        <p>当前单元尚未关联产权证。</p>
      ) : (
        query.data?.map(certificate => (
          <div key={certificate.id}>
            <h4>{certificate.certificate_number}</h4>
            <CertificateControls unitId={unitId} certificate={certificate} />
            <dl>
              <dt>证载坐落</dt>
              <dd>{certificate.property_address ?? '未登记'}</dd>
              <dt>证载建筑面积</dt>
              <dd>{certificate.building_area ?? '未登记'}</dd>
              <dt>证载土地面积</dt>
              <dd>{certificate.land_area ?? '未登记'}</dd>
            </dl>
          </div>
        ))
      )}
    </section>
  );
}

function RenameForm(props: {
  unit: AssetUnitListItem;
  pending: boolean;
  errorMessage: string | null;
  onSubmit: (name: string) => void;
}): React.ReactElement {
  const { control, handleSubmit, reset, watch } = useForm<{ name: string }>({
    defaultValues: { name: props.unit.name },
  });
  useEffect(() => {
    reset({ name: props.unit.name });
  }, [props.unit.id, props.unit.name, reset]);

  const name = watch('name');
  const trimmed = name.trim();
  const changed = trimmed !== props.unit.name && trimmed !== '';

  return (
    <form
      style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}
      onSubmit={handleSubmit(values => {
        const submittedName = values.name.trim();
        if (submittedName !== '' && submittedName !== props.unit.name) {
          props.onSubmit(submittedName);
        }
      })}
    >
      <label htmlFor="unit-rename-input" style={{ fontSize: 13 }}>
        单元名称
      </label>
      <Controller
        control={control}
        name="name"
        render={({ field }) => <Input id="unit-rename-input" {...field} />}
      />
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
