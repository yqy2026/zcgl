/**
 * 资产运营 · 月度出租率报送
 *
 * 三个区块（antd Tabs）：年度考核范围（含范围草稿抽屉，preview→commit 两步）、
 * 当月草稿报送（汇总 + 逐宗明细 + 变动说明 + 提交预览确认）、历史快照
 * （report_id 深链 + 撤回 + CSV 导出）。四态分离：pending / 403 / error / 空
 * 互不吞并；operator_party_id、period、report_id 同步到 URL 查询参数。
 *
 * 后端报送写端点鉴权为 asset_ops:report（见 backend require_authz action="report"），
 * CapabilityGuard.canPerform 接受 AuthzAction 全集（types/capability.ts 含 'report'），
 * 故写操作统一用 action="report" 而非既有页面的 action="write"。
 */

import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import {
  Alert,
  Button,
  DatePicker,
  Descriptions,
  Drawer,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';

import CapabilityGuard from '@/components/System/CapabilityGuard';
import {
  occupancyReportService,
  commandKey,
  isOccupancyForbidden,
  AssetOperationsError,
  AssessmentScopeDraftExistsError,
} from '@/services/occupancyReportService';
import type {
  AssessmentScopeItem,
  AssessmentScopePreview,
  OccupancyReportLine,
  OccupancyReportSubmissionPreview,
  OccupancyReportTotals,
  OccupancyReportUnitDiff,
  OccupancyReportWithdrawalPreview,
  OperatorParty,
} from '@/services/occupancyReportService';

import styles from './OccupancyReportsPage.module.css';

const PERIOD_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;
const YEAR_PATTERN = /^\d{4}$/;

type TabKey = 'scope' | 'draft' | 'snapshot';

const PENDING_REASON_LABELS: Record<string, string> = {
  new_takeover: '新接管',
  boundary_uncertain: '边界待确认',
};

const RENTAL_STATUS_LABELS: Record<OccupancyReportLine['rentalStatus'], string> = {
  rented: '已出租',
  vacant: '空置',
  non_rentable: '不可租',
};

const RENTAL_STATUS_COLORS: Record<OccupancyReportLine['rentalStatus'], string> = {
  rented: 'blue',
  vacant: 'default',
  non_rentable: 'default',
};

const DIFF_KIND_LABELS: Record<OccupancyReportUnitDiff['kind'], string> = {
  changed: '字段变化',
  unit_left_scope: '移出考核范围',
  unit_entered_scope: '新进入考核范围',
};

/** 后端业务错误码 → 页面恢复提示；未命中时回退后端 message。 */
const ERROR_HINTS: Record<string, string> = {
  PREVIEW_STALE: '预览已过期，请重新生成预览后再提交。',
  VERSION_CONFLICT: '数据已被他人修改，请刷新后重试。',
  OCCUPANCY_REPORT_ALREADY_SUBMITTED: '该统计月已报送，请到历史快照查看。',
  OCCUPANCY_REPORT_ALREADY_WITHDRAWN: '该报送已撤回，无需重复操作。',
  OCCUPANCY_REPORT_SCOPE_MISSING: '该统计月缺少生效的考核范围版本，请先完成考核范围报送。',
  OCCUPANCY_REPORT_PERIOD_INVALID: '统计月无效，请重新选择。',
};

function errorText(error: unknown): string {
  if (error instanceof AssetOperationsError) {
    return ERROR_HINTS[error.code] ?? error.message;
  }
  return error instanceof Error ? error.message : '操作失败，请重试';
}

function formatArea(value: number): string {
  return `${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })} ㎡`;
}

function formatRate(value: number | null): string {
  return value == null ? '—' : `${(value * 100).toFixed(1)}%`;
}

function formatDateTime(value: string | null): string {
  return value == null || value === '' ? '—' : dayjs(value).format('YYYY-MM-DD HH:mm');
}

/** 默认统计月：最近一个已结束的自然月（禁止未来月由日期选择器兜底）。 */
function latestEndedPeriod(): string {
  return dayjs().startOf('month').subtract(1, 'month').format('YYYY-MM');
}

type QueryLike = {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => void;
};

/**
 * 四态边界：pending → role="status"；403 → warning 无权提示（不吞成空表）；
 * 其他错误 → error + 重试；空 → 明确文案；其余渲染 children。
 */
function QueryBoundary(props: {
  query: QueryLike;
  loadingText: string;
  emptyText: string | null;
  isEmpty?: boolean;
  children: ReactNode;
}): React.ReactElement {
  if (props.query.isPending) {
    return (
      <p role="status" className={styles.stateText}>
        {props.loadingText}
      </p>
    );
  }
  if (props.query.isError) {
    const forbidden = isOccupancyForbidden(props.query.error);
    return (
      <div className={styles.errorRow}>
        <Alert
          type={forbidden ? 'warning' : 'error'}
          showIcon
          title={
            forbidden
              ? '当前账号没有相关数据范围或权限，请联系管理员。'
              : errorText(props.query.error)
          }
        />
        {forbidden ? null : <Button onClick={() => void props.query.refetch()}>重试</Button>}
      </div>
    );
  }
  if (props.isEmpty === true) {
    return <p className={styles.stateText}>{props.emptyText ?? '暂无数据。'}</p>;
  }
  return <>{props.children}</>;
}

function SummaryCard(props: { label: string; value: string }): React.ReactElement {
  return (
    <div className={styles.summaryCard}>
      <span className={styles.summaryLabel}>{props.label}</span>
      <span className={styles.summaryValue}>{props.value}</span>
    </div>
  );
}

function TotalsGrid(props: { totals: OccupancyReportTotals }): React.ReactElement {
  const { totals } = props;
  return (
    <div className={styles.summaryGrid}>
      <SummaryCard label="出租率" value={formatRate(totals.occupancyRate)} />
      <SummaryCard label="宗地数" value={String(totals.unitCount)} />
      <SummaryCard label="已租宗数" value={String(totals.rentedUnitCount)} />
      <SummaryCard label="土地面积" value={formatArea(totals.landArea)} />
      <SummaryCard label="建筑面积" value={formatArea(totals.buildingArea)} />
      <SummaryCard label="可租面积" value={formatArea(totals.rentableArea)} />
      <SummaryCard label="已租面积" value={formatArea(totals.rentedArea)} />
    </div>
  );
}

const LINE_COLUMNS: ColumnsType<OccupancyReportLine> = [
  { title: '地址', dataIndex: 'addressSnapshot', key: 'addressSnapshot', width: 200 },
  { title: '项目', dataIndex: 'projectNameSnapshot', key: 'projectNameSnapshot', width: 140 },
  { title: '用途', dataIndex: 'usageTypeSnapshot', key: 'usageTypeSnapshot', width: 100 },
  { title: '业主', dataIndex: 'ownerNameSnapshot', key: 'ownerNameSnapshot', width: 140 },
  {
    title: '土地面积',
    dataIndex: 'landArea',
    key: 'landArea',
    align: 'right',
    width: 110,
    render: (_: unknown, record) => (
      <span className={styles.numeric}>{formatArea(record.landArea)}</span>
    ),
  },
  {
    title: '建筑面积',
    dataIndex: 'buildingArea',
    key: 'buildingArea',
    align: 'right',
    width: 110,
    render: (_: unknown, record) => (
      <span className={styles.numeric}>{formatArea(record.buildingArea)}</span>
    ),
  },
  {
    title: '可租面积',
    dataIndex: 'rentableArea',
    key: 'rentableArea',
    align: 'right',
    width: 110,
    render: (_: unknown, record) => (
      <span className={styles.numeric}>{formatArea(record.rentableArea)}</span>
    ),
  },
  {
    title: '已租面积',
    dataIndex: 'rentedArea',
    key: 'rentedArea',
    align: 'right',
    width: 110,
    render: (_: unknown, record) => (
      <span className={styles.numeric}>{formatArea(record.rentedArea)}</span>
    ),
  },
  {
    title: '出租状态',
    dataIndex: 'rentalStatus',
    key: 'rentalStatus',
    width: 90,
    render: (_: unknown, record) => (
      <Tag color={RENTAL_STATUS_COLORS[record.rentalStatus]}>
        {RENTAL_STATUS_LABELS[record.rentalStatus]}
      </Tag>
    ),
  },
  {
    title: '终端合同',
    dataIndex: 'terminalContractIds',
    key: 'terminalContractIds',
    width: 160,
    render: (_: unknown, record) =>
      record.terminalContractIds.length === 0 ? '—' : record.terminalContractIds.join('、'),
  },
];

function LinesTable(props: { lines: OccupancyReportLine[]; caption: string }): React.ReactElement {
  return (
    <div role="region" aria-label={props.caption} tabIndex={0} className={styles.scrollRegion}>
      <Table<OccupancyReportLine>
        rowKey="assetUnitId"
        columns={LINE_COLUMNS}
        dataSource={props.lines}
        pagination={false}
        size="small"
        scroll={{ x: 1180 }}
      />
    </div>
  );
}

function ChangesTable(props: {
  changes: { fieldName: string; previous: string | null; current: string | null }[];
  caption: string;
}): React.ReactElement {
  return (
    <div role="region" aria-label={props.caption} tabIndex={0} className={styles.scrollRegion}>
      <Table
        rowKey={record => record.fieldName}
        columns={[
          { title: '字段', dataIndex: 'fieldName', key: 'fieldName' },
          {
            title: '前值',
            dataIndex: 'previous',
            key: 'previous',
            render: (value: string | null) => value ?? '—',
          },
          {
            title: '现值',
            dataIndex: 'current',
            key: 'current',
            render: (value: string | null) => value ?? '—',
          },
        ]}
        dataSource={props.changes}
        pagination={false}
        size="small"
      />
    </div>
  );
}

// ==================== 考核范围 ====================

const SCOPE_ITEM_COLUMNS: ColumnsType<AssessmentScopeItem> = [
  {
    title: '单元编号',
    key: 'unitCode',
    width: 120,
    render: (_: unknown, record) => record.unitSnapshot.unitCode,
  },
  {
    title: '名称',
    key: 'name',
    width: 140,
    render: (_: unknown, record) => record.unitSnapshot.name,
  },
  {
    title: '用途',
    key: 'usageType',
    width: 90,
    render: (_: unknown, record) => record.unitSnapshot.usageType,
  },
  {
    title: '可租面积',
    key: 'rentableArea',
    align: 'right',
    width: 110,
    render: (_: unknown, record) => (
      <span className={styles.numeric}>{formatArea(record.unitSnapshot.rentableArea)}</span>
    ),
  },
  {
    title: '决定',
    key: 'included',
    width: 80,
    render: (_: unknown, record) =>
      record.included ? <Tag color="blue">纳入</Tag> : <Tag>排除</Tag>,
  },
  {
    title: '排除原因',
    key: 'exclusionReason',
    render: (_: unknown, record) => record.exclusionReason ?? '—',
  },
];

function ScopeSection(props: { year: number; operatorId: string }): React.ReactElement {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [draftId, setDraftId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  const scopeQuery = useQuery({
    queryKey: ['assessment-scope', props.year, props.operatorId],
    queryFn: () => occupancyReportService.getAssessmentScope(props.year, props.operatorId),
  });

  const createDraftMutation = useMutation({
    mutationFn: (source: 'current' | 'previous_year') =>
      occupancyReportService.createAssessmentScopeDraft(props.year, {
        operatorPartyId: props.operatorId,
        source,
      }),
    onSuccess: draft => {
      setCreateError(null);
      setNotice(null);
      setDraftId(draft.draftId);
      setDrawerOpen(true);
    },
    onError: error => {
      // 409 ASSESSMENT_SCOPE_DRAFT_EXISTS：用后端回传的 draftId 直接转入编辑。
      if (error instanceof AssessmentScopeDraftExistsError && error.draftId !== '') {
        setCreateError(null);
        setNotice('该年度已存在未提交的范围草稿，已转入继续编辑。');
        setDraftId(error.draftId);
        setDrawerOpen(true);
        return;
      }
      setCreateError(errorText(error));
    },
  });

  const scope = scopeQuery.data ?? null;

  return (
    <div className={styles.section}>
      {notice != null ? <Alert type="success" showIcon title={notice} /> : null}
      {createError != null ? <Alert type="error" showIcon title={createError} /> : null}

      <QueryBoundary
        query={scopeQuery}
        loadingText="正在读取考核范围…"
        emptyText="该年度尚未生成考核范围版本，可创建草稿完成首次报送范围确认。"
        isEmpty={scope?.scope == null}
      >
        {scope != null ? (
          <>
            <Descriptions column={2} size="small" bordered className={styles.summaryDescriptions}>
              <Descriptions.Item label="当前版本">
                {scope.scope?.versionNumber != null ? `v${scope.scope.versionNumber}` : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="版本状态">{scope.scope?.status ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="生效起始月">
                {scope.scope?.effectiveFromPeriod || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="生效时间">
                {formatDateTime(scope.scope?.activatedAt ?? null)}
              </Descriptions.Item>
              <Descriptions.Item label={`最近出租率（${scope.occupancy?.period ?? '—'}）`}>
                <span className={styles.numeric}>
                  {formatRate(scope.occupancy?.occupancyRate ?? null)}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="纳入 / 排除宗地">
                <span className={styles.numeric}>
                  {scope.items.filter(item => item.included).length} /{' '}
                  {scope.items.filter(item => !item.included).length}
                </span>
              </Descriptions.Item>
            </Descriptions>

            <div
              role="region"
              aria-label="考核范围逐宗决定"
              tabIndex={0}
              className={styles.scrollRegion}
            >
              <Table<AssessmentScopeItem>
                rowKey="assetUnitId"
                columns={SCOPE_ITEM_COLUMNS}
                dataSource={scope.items}
                pagination={false}
                size="small"
                scroll={{ x: 760 }}
              />
            </div>

            {scope.pending.length > 0 ? (
              <Alert
                type="warning"
                showIcon
                title={`还有 ${scope.pending.length} 宗待确认：${scope.pending
                  .map(
                    item =>
                      `${item.unitSnapshot.unitCode}（${PENDING_REASON_LABELS[item.reason] ?? item.reason}）`
                  )
                  .join('、')}`}
              />
            ) : null}
          </>
        ) : null}
      </QueryBoundary>

      <CapabilityGuard action="report" resource="asset_ops" fallback={<></>}>
        <Space wrap>
          <Button
            type="primary"
            loading={createDraftMutation.isPending}
            onClick={() => createDraftMutation.mutate('current')}
          >
            按当前在管单元创建草稿
          </Button>
          <Button
            loading={createDraftMutation.isPending}
            onClick={() => createDraftMutation.mutate('previous_year')}
          >
            复制上年度范围创建草稿
          </Button>
        </Space>
      </CapabilityGuard>

      <AssessmentScopeDrawer
        open={drawerOpen}
        year={props.year}
        draftId={draftId}
        onClose={() => setDrawerOpen(false)}
        onCommitted={message => {
          setDrawerOpen(false);
          setNotice(message);
          void queryClient.invalidateQueries({
            queryKey: ['assessment-scope', props.year, props.operatorId],
          });
        }}
      />
    </div>
  );
}

interface ScopeDecisionState {
  included: boolean;
  exclusionReason: string;
}

function AssessmentScopeDrawer(props: {
  open: boolean;
  year: number;
  draftId: string | null;
  onClose: () => void;
  onCommitted: (message: string) => void;
}): React.ReactElement {
  const queryClient = useQueryClient();
  const [decisions, setDecisions] = useState<Record<string, ScopeDecisionState>>({});
  const [scopePreview, setScopePreview] = useState<AssessmentScopePreview | null>(null);
  const [draftVersion, setDraftVersion] = useState<number | null>(null);
  const [effectiveFromPeriod, setEffectiveFromPeriod] = useState<string>('');

  const draftQuery = useQuery({
    queryKey: ['assessment-scope-draft', props.draftId],
    queryFn: () => occupancyReportService.getAssessmentScopeDraft(props.draftId as string),
    enabled: props.open && props.draftId != null,
  });

  const draft = props.open ? (draftQuery.data ?? null) : null;

  // 每次打开抽屉或草稿数据更新时，用服务端草稿重建本地决定表，
  // 避免关闭后残留旧状态或同 draftId 重开时决定表为空。
  useEffect(() => {
    if (!props.open || draft == null) {
      return;
    }
    const next: Record<string, ScopeDecisionState> = {};
    for (const item of draft.items) {
      next[item.assetUnitId] = {
        included: item.included,
        exclusionReason: item.exclusionReason ?? '',
      };
    }
    setDecisions(next);
    setScopePreview(null);
    setDraftVersion(draft.version);
    setEffectiveFromPeriod(draft.effectiveFromPeriod);
  }, [props.open, draft]);

  const decisionEntries = Object.entries(decisions);
  const missingReason = decisionEntries.some(
    ([, state]) => !state.included && state.exclusionReason.trim() === ''
  );

  const prepareMutation = useMutation({
    mutationFn: async () => {
      if (draft == null) {
        throw new AssetOperationsError('范围草稿尚未加载', 'INVALID_RESPONSE_DATA');
      }
      const payload = decisionEntries.map(([assetUnitId, state]) => ({
        assetUnitId,
        included: state.included,
        exclusionReason: state.included ? null : state.exclusionReason.trim(),
      }));
      const updated = await occupancyReportService.updateAssessmentScopeDraft(
        draft.draftId,
        payload,
        draft.version
      );
      const preview = await occupancyReportService.previewAssessmentScopeDraft(updated.draftId);
      return { updated, preview };
    },
    onSuccess: ({ updated, preview }) => {
      setScopePreview(preview);
      setDraftVersion(updated.version);
      setEffectiveFromPeriod(updated.effectiveFromPeriod);
    },
  });

  const commitMutation = useMutation({
    mutationFn: (input: {
      previewToken: string;
      expectedVersion: number;
      effectiveFromPeriod: string;
    }) =>
      occupancyReportService.commitAssessmentScopeDraft(
        props.draftId as string,
        input,
        commandKey()
      ),
    onSuccess: result => {
      void queryClient.invalidateQueries({ queryKey: ['assessment-scope-draft', props.draftId] });
      props.onCommitted(
        `考核范围 v${result.versionNumber} 已自 ${result.effectiveFromPeriod} 起生效。`
      );
    },
    onError: error => {
      if (error instanceof AssetOperationsError && error.code === 'PREVIEW_STALE') {
        setScopePreview(null);
      }
    },
  });

  const closeDrawer = (): void => {
    setScopePreview(null);
    setDecisions({});
    props.onClose();
  };

  const renderDecisionsTable = (): React.ReactElement => (
    <div role="region" aria-label="范围草稿逐宗决定" tabIndex={0} className={styles.scrollRegion}>
      <Table<AssessmentScopeItem>
        rowKey="assetUnitId"
        columns={[
          {
            title: '单元编号',
            key: 'unitCode',
            width: 110,
            render: (_: unknown, record) => record.unitSnapshot.unitCode,
          },
          {
            title: '名称',
            key: 'name',
            width: 130,
            render: (_: unknown, record) => record.unitSnapshot.name,
          },
          {
            title: '决定',
            key: 'included',
            width: 100,
            render: (_: unknown, record) => {
              const state = decisions[record.assetUnitId];
              return (
                <Select<'included' | 'excluded'>
                  aria-label={`${record.unitSnapshot.unitCode} 决定`}
                  size="small"
                  style={{ width: 84 }}
                  value={state?.included === false ? 'excluded' : 'included'}
                  options={[
                    { value: 'included', label: '纳入' },
                    { value: 'excluded', label: '排除' },
                  ]}
                  onChange={value =>
                    setDecisions(previous => ({
                      ...previous,
                      [record.assetUnitId]: {
                        included: value === 'included',
                        exclusionReason:
                          value === 'included'
                            ? ''
                            : (previous[record.assetUnitId]?.exclusionReason ?? ''),
                      },
                    }))
                  }
                />
              );
            },
          },
          {
            title: '排除原因',
            key: 'exclusionReason',
            render: (_: unknown, record) => {
              const state = decisions[record.assetUnitId];
              return (
                <Input
                  aria-label={`${record.unitSnapshot.unitCode} 排除原因`}
                  size="small"
                  maxLength={500}
                  disabled={state?.included !== false}
                  value={state?.included === false ? state.exclusionReason : ''}
                  onChange={event =>
                    setDecisions(previous => ({
                      ...previous,
                      [record.assetUnitId]: {
                        included: false,
                        exclusionReason: event.target.value,
                      },
                    }))
                  }
                />
              );
            },
          },
        ]}
        dataSource={draft?.items ?? []}
        pagination={false}
        size="small"
        scroll={{ x: 620 }}
      />
    </div>
  );

  return (
    <Drawer
      title={`考核范围草稿（${props.year} 年度）`}
      placement="right"
      onClose={closeDrawer}
      open={props.open}
      size={860}
    >
      {draftQuery.isPending ? <p role="status">正在读取范围草稿…</p> : null}
      {draftQuery.isError ? (
        <Alert type="error" showIcon title={errorText(draftQuery.error)} />
      ) : null}

      {scopePreview != null ? (
        <Space orientation="vertical" size={16} className={styles.drawerStack}>
          <Alert type="info" showIcon title="请核对影响预览后提交生效。" />
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="当前版本">
              {scopePreview.currentVersionNumber != null
                ? `v${scopePreview.currentVersionNumber}`
                : '（首个版本）'}
            </Descriptions.Item>
            <Descriptions.Item label="当前纳入 / 排除">
              <span className={styles.numeric}>
                {scopePreview.currentIncludedCount} / {scopePreview.currentExcludedCount}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="新纳入 / 排除">
              <span className={styles.numeric}>
                {scopePreview.newIncludedCount} / {scopePreview.newExcludedCount}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="待确认宗地">
              <span className={styles.numeric}>{scopePreview.pendingCount}</span>
            </Descriptions.Item>
            <Descriptions.Item label={`出租率对照（${scopePreview.occupancyPeriod}）`}>
              <span className={styles.numeric}>
                {formatRate(scopePreview.occupancyRateCurrent)} →{' '}
                {formatRate(scopePreview.occupancyRateNew)}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="影响期间">
              {scopePreview.affectedPeriods.join('、')}
            </Descriptions.Item>
            <Descriptions.Item label="预览有效期">
              {formatDateTime(scopePreview.expiresAt)}
            </Descriptions.Item>
          </Descriptions>
          <div className={styles.toolbarItem}>
            <span className={styles.toolbarLabel}>生效起始月</span>
            <DatePicker
              picker="month"
              allowClear={false}
              value={effectiveFromPeriod !== '' ? dayjs(`${effectiveFromPeriod}-01`) : null}
              disabledDate={(value: Dayjs) => value.isAfter(dayjs(), 'month')}
              onChange={value => {
                if (value != null) {
                  setEffectiveFromPeriod(value.format('YYYY-MM'));
                }
              }}
            />
          </div>
          {commitMutation.isError ? (
            <Alert type="error" showIcon title={errorText(commitMutation.error)} />
          ) : null}
          <Space wrap>
            <Button onClick={() => setScopePreview(null)}>返回编辑</Button>
            <Button
              type="primary"
              loading={commitMutation.isPending}
              disabled={
                draftVersion == null ||
                effectiveFromPeriod === '' ||
                !PERIOD_PATTERN.test(effectiveFromPeriod)
              }
              onClick={() => {
                if (draftVersion != null && scopePreview != null) {
                  commitMutation.mutate({
                    previewToken: scopePreview.previewToken,
                    expectedVersion: draftVersion,
                    effectiveFromPeriod,
                  });
                }
              }}
            >
              提交生效
            </Button>
          </Space>
        </Space>
      ) : (
        <Space orientation="vertical" size={16} className={styles.drawerStack}>
          {draftQuery.isError || draft == null ? null : (
            <>
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="草稿编号">{draft.draftId}</Descriptions.Item>
                <Descriptions.Item label="草稿版本">
                  <span className={styles.numeric}>v{draft.version}</span>
                </Descriptions.Item>
              </Descriptions>
              {draft.pending.length > 0 ? (
                <Alert
                  type="warning"
                  showIcon
                  title={`待确认宗地 ${draft.pending.length} 宗（新接管或边界待确认），请一并给出纳入/排除决定。`}
                />
              ) : null}
              {renderDecisionsTable()}
              {missingReason ? (
                <Alert type="warning" showIcon title="排除决定必须填写原因。" />
              ) : null}
              {prepareMutation.isError ? (
                <Alert
                  type="error"
                  showIcon
                  title={errorText(prepareMutation.error)}
                  description={
                    prepareMutation.error instanceof AssetOperationsError &&
                    prepareMutation.error.code === 'VERSION_CONFLICT' ? (
                      <Button size="small" onClick={() => void draftQuery.refetch()}>
                        刷新草稿
                      </Button>
                    ) : undefined
                  }
                />
              ) : null}
              <Space wrap>
                <Button onClick={closeDrawer}>取消</Button>
                <Button
                  type="primary"
                  loading={prepareMutation.isPending}
                  disabled={decisionEntries.length === 0 || missingReason}
                  onClick={() => prepareMutation.mutate()}
                >
                  保存并生成影响预览
                </Button>
              </Space>
            </>
          )}
        </Space>
      )}
    </Drawer>
  );
}

// ==================== 当月草稿 ====================

function DraftSection(props: {
  period: string;
  operatorId: string;
  onSubmitted: (reportId: string) => void;
}): React.ReactElement {
  const queryClient = useQueryClient();
  const [noteText, setNoteText] = useState('');
  const [noteDirty, setNoteDirty] = useState(false);
  const [submissionPreview, setSubmissionPreview] =
    useState<OccupancyReportSubmissionPreview | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const draftQuery = useQuery({
    queryKey: ['occupancy-report-draft', props.period, props.operatorId],
    queryFn: () => occupancyReportService.getOccupancyReportDraft(props.period, props.operatorId),
  });

  const draft = draftQuery.data ?? null;

  // 仅在用户尚未编辑时用服务端值回填，避免后台刷新覆盖输入中的说明。
  useEffect(() => {
    if (!noteDirty) {
      setNoteText(draft?.changeNote ?? '');
    }
  }, [noteDirty, draft]);

  // 切换统计月或运营主体后丢弃未保存的本地编辑状态。
  useEffect(() => {
    setNoteDirty(false);
    setSubmissionPreview(null);
    setNotice(null);
  }, [props.period, props.operatorId]);

  const invalidateDraft = (): void => {
    void queryClient.invalidateQueries({
      queryKey: ['occupancy-report-draft', props.period, props.operatorId],
    });
  };

  const saveNoteMutation = useMutation({
    mutationFn: (changeNote: string | null) =>
      occupancyReportService.saveOccupancyReportNote(props.period, {
        operatorPartyId: props.operatorId,
        changeNote,
      }),
    onSuccess: () => {
      setNoteDirty(false);
      setNotice('变动说明已保存。');
      invalidateDraft();
    },
  });

  const previewSubmissionMutation = useMutation({
    mutationFn: () =>
      occupancyReportService.previewOccupancyReportSubmission(props.period, props.operatorId),
    onSuccess: preview => setSubmissionPreview(preview),
  });

  const submitMutation = useMutation({
    mutationFn: (preview: OccupancyReportSubmissionPreview) =>
      occupancyReportService.submitOccupancyReport(
        props.period,
        props.operatorId,
        {
          previewToken: preview.previewToken ?? '',
          expectedScopeVersionId: preview.scopeVersion.versionId,
          expectedScopeVersion: preview.scopeVersion.version,
        },
        commandKey()
      ),
    onSuccess: result => {
      setSubmissionPreview(null);
      invalidateDraft();
      props.onSubmitted(result.reportId);
    },
  });

  const isEmpty = draft != null && draft.lines.length === 0 && draft.pending.length === 0;

  return (
    <div className={styles.section}>
      {notice != null ? <Alert type="success" showIcon title={notice} /> : null}
      <QueryBoundary
        query={draftQuery}
        loadingText="正在读取当月报送草稿…"
        emptyText="当月暂无纳入考核范围的宗地明细。"
        isEmpty={isEmpty}
      >
        {draft != null ? (
          <Space orientation="vertical" size={16} className={styles.sectionStack}>
            <Space wrap size={8}>
              <Tag color="geekblue">{draft.period}</Tag>
              {draft.firstReport ? <Tag color="gold">首期报送</Tag> : null}
              {draft.scopeVersion != null ? (
                <Tag>
                  考核范围 v{draft.scopeVersion.versionNumber ?? '—'}（
                  {draft.scopeVersion.effectiveFromPeriod} 起）
                </Tag>
              ) : (
                <Tag color="red">缺少生效考核范围</Tag>
              )}
            </Space>

            <TotalsGrid totals={draft.totals} />

            {draft.pending.length > 0 ? (
              <Alert
                type="warning"
                showIcon
                title={`待确认宗地 ${draft.pending.length} 宗：${draft.pending
                  .map(
                    item =>
                      `${item.assetUnitId}（${PENDING_REASON_LABELS[item.reason] ?? item.reason}）`
                  )
                  .join('、')}`}
              />
            ) : null}
            {!draft.canSubmit && draft.gateReasons.length > 0 ? (
              <Alert
                type="warning"
                showIcon
                title={`暂不满足提交条件：${draft.gateReasons.join('；')}`}
              />
            ) : null}

            {!draft.firstReport && draft.changes.length > 0 ? (
              <div>
                <h3 className={styles.blockTitle}>较上月变化</h3>
                <ChangesTable changes={draft.changes} caption="较上月变化明细" />
              </div>
            ) : null}

            <div>
              <h3 className={styles.blockTitle}>逐宗明细</h3>
              <LinesTable lines={draft.lines} caption="当月报送逐宗明细" />
            </div>

            <CapabilityGuard action="report" resource="asset_ops" fallback={<></>}>
              <Space orientation="vertical" size={8} className={styles.sectionStack}>
                <div>
                  <h3 className={styles.blockTitle}>变动说明</h3>
                  <Input.TextArea
                    aria-label="变动说明"
                    rows={3}
                    maxLength={2000}
                    value={noteText}
                    onChange={event => {
                      setNoteDirty(true);
                      setNoteText(event.target.value);
                    }}
                  />
                </div>
                {saveNoteMutation.isError ? (
                  <Alert type="error" showIcon title={errorText(saveNoteMutation.error)} />
                ) : null}
                <Button
                  loading={saveNoteMutation.isPending}
                  onClick={() =>
                    saveNoteMutation.mutate(noteText.trim() === '' ? null : noteText.trim())
                  }
                >
                  保存变动说明
                </Button>

                <Space wrap>
                  <Button
                    type="primary"
                    disabled={!draft.canSubmit}
                    loading={previewSubmissionMutation.isPending}
                    onClick={() => previewSubmissionMutation.mutate()}
                  >
                    提交报送
                  </Button>
                  {previewSubmissionMutation.isError ? (
                    <Alert
                      type="error"
                      showIcon
                      title={errorText(previewSubmissionMutation.error)}
                    />
                  ) : null}
                </Space>
              </Space>
            </CapabilityGuard>
          </Space>
        ) : null}
      </QueryBoundary>

      <SubmissionPreviewModal
        preview={submissionPreview}
        pending={submitMutation.isPending}
        error={submitMutation.isError ? errorText(submitMutation.error) : null}
        onCancel={() => {
          setSubmissionPreview(null);
          submitMutation.reset();
        }}
        onConfirm={() => {
          if (submissionPreview != null) {
            submitMutation.mutate(submissionPreview);
          }
        }}
      />
    </div>
  );
}

function SubmissionPreviewModal(props: {
  preview: OccupancyReportSubmissionPreview | null;
  pending: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}): React.ReactElement {
  const preview = props.preview;
  return (
    <Modal
      title="提交预览"
      open={preview != null}
      onCancel={props.onCancel}
      footer={[
        <Button key="cancel" onClick={props.onCancel}>
          取消
        </Button>,
        <Button
          key="confirm"
          type="primary"
          loading={props.pending}
          disabled={preview?.canSubmit !== true || preview.previewToken == null}
          onClick={props.onConfirm}
        >
          确认提交
        </Button>,
      ]}
    >
      {preview != null ? (
        <Space orientation="vertical" size={12} className={styles.sectionStack}>
          {!preview.canSubmit ? (
            <Alert
              type="error"
              showIcon
              title={`不满足提交条件：${preview.gateReasons.join('；')}`}
            />
          ) : null}
          {preview.mustHandle.length > 0 ? (
            <Alert
              type="warning"
              showIcon
              title={`必须处理 ${preview.mustHandle.length} 宗：${preview.mustHandle
                .map(
                  item =>
                    `${item.assetUnitId}（${PENDING_REASON_LABELS[item.reason] ?? item.reason}）`
                )
                .join('、')}`}
            />
          ) : null}
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="统计月">{preview.period}</Descriptions.Item>
            <Descriptions.Item label="出租率">
              <span className={styles.numeric}>{formatRate(preview.totals.occupancyRate)}</span>
            </Descriptions.Item>
            <Descriptions.Item label="宗地数">
              <span className={styles.numeric}>{preview.totals.unitCount}</span>
            </Descriptions.Item>
            <Descriptions.Item label="归一后变动说明">
              {preview.normalizedNote ?? '—'}
            </Descriptions.Item>
          </Descriptions>
          {preview.changes.length > 0 ? (
            <ChangesTable changes={preview.changes} caption="提交预览变化明细" />
          ) : null}
          {props.error != null ? <Alert type="error" showIcon title={props.error} /> : null}
        </Space>
      ) : null}
    </Modal>
  );
}

// ==================== 历史快照 ====================

const DIFF_COLUMNS: ColumnsType<OccupancyReportUnitDiff> = [
  { title: '宗地', dataIndex: 'assetUnitId', key: 'assetUnitId', width: 200 },
  {
    title: '差异类型',
    dataIndex: 'kind',
    key: 'kind',
    width: 130,
    render: (_: unknown, record) => DIFF_KIND_LABELS[record.kind],
  },
  {
    title: '变更明细',
    key: 'changes',
    render: (_: unknown, record) => (
      <ul className={styles.diffList}>
        {record.changes.map(change => (
          <li key={`${record.assetUnitId}-${change.fieldName}`}>
            {change.fieldName}：{change.previous ?? '—'} → {change.current ?? '—'}
          </li>
        ))}
      </ul>
    ),
  },
];

function downloadCsvFile(fileName: string, contentBase64: string): void {
  const binary = atob(contentBase64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const blob = new Blob([bytes], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName !== '' ? fileName : 'occupancy-report.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function SnapshotSection(props: { reportId: string }): React.ReactElement {
  const queryClient = useQueryClient();
  const [withdrawPreview, setWithdrawPreview] = useState<OccupancyReportWithdrawalPreview | null>(
    null
  );
  const [withdrawReason, setWithdrawReason] = useState('');
  const [notice, setNotice] = useState<string | null>(null);

  const snapshotQuery = useQuery({
    queryKey: ['occupancy-report-snapshot', props.reportId],
    queryFn: () => occupancyReportService.getOccupancyReportSnapshot(props.reportId),
    enabled: props.reportId !== '',
  });

  const invalidateSnapshot = (): void => {
    void queryClient.invalidateQueries({
      queryKey: ['occupancy-report-snapshot', props.reportId],
    });
  };

  const withdrawPreviewMutation = useMutation({
    mutationFn: (reportId: string) =>
      occupancyReportService.previewOccupancyReportWithdrawal(reportId),
    onSuccess: preview => {
      setWithdrawReason('');
      setWithdrawPreview(preview);
    },
  });

  const withdrawMutation = useMutation({
    mutationFn: (preview: OccupancyReportWithdrawalPreview) =>
      occupancyReportService.withdrawOccupancyReport(
        preview.reportId,
        {
          previewToken: preview.previewToken,
          expectedVersion: preview.reportVersion,
          withdrawReason: withdrawReason.trim(),
        },
        commandKey()
      ),
    onSuccess: result => {
      setWithdrawPreview(null);
      setNotice(`报送已撤回，已生成可重新报送的草稿（${result.successorDraftId}）。`);
      invalidateSnapshot();
    },
  });

  const exportMutation = useMutation({
    mutationFn: async (reportId: string) => {
      const start = await occupancyReportService.exportOccupancyReport(reportId);
      return occupancyReportService.getExportTaskResult(start.taskId);
    },
    onSuccess: file => downloadCsvFile(file.fileName, file.contentBase64),
  });

  const snapshot = snapshotQuery.data ?? null;

  if (props.reportId === '') {
    return (
      <p className={styles.stateText}>
        从报送记录链接进入后可在此查看历史快照（URL 需携带 report_id 参数）。
      </p>
    );
  }

  return (
    <div className={styles.section}>
      {notice != null ? <Alert type="success" showIcon title={notice} /> : null}
      <QueryBoundary query={snapshotQuery} loadingText="正在读取报送快照…" emptyText={null}>
        {snapshot != null ? (
          <Space orientation="vertical" size={16} className={styles.sectionStack}>
            <Space wrap size={8}>
              <Tag color={snapshot.status === 'submitted' ? 'green' : 'default'}>
                {snapshot.status === 'submitted' ? '已报送' : '已撤回'}
              </Tag>
              <Tag color="geekblue">{snapshot.period}</Tag>
              <Tag>考核范围 v{snapshot.scopeVersion.versionNumber ?? '—'}</Tag>
              {snapshot.predecessorReportId != null ? <Tag>承接前次报送</Tag> : null}
            </Space>

            <TotalsGrid totals={snapshot.totals} />

            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="项目数">
                <span className={styles.numeric}>{snapshot.projectCounts.projectCount}</span>
              </Descriptions.Item>
              <Descriptions.Item label="经营性 / 非经营性项目">
                <span className={styles.numeric}>
                  {snapshot.projectCounts.operatingProjectCount} /{' '}
                  {snapshot.projectCounts.nonOperatingProjectCount}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="报送时间">
                {formatDateTime(snapshot.submittedAt)}
              </Descriptions.Item>
              {snapshot.status === 'withdrawn' ? (
                <>
                  <Descriptions.Item label="撤回时间">
                    {formatDateTime(snapshot.withdrawnAt)}
                  </Descriptions.Item>
                  <Descriptions.Item label="撤回原因" span={2}>
                    {snapshot.withdrawReason ?? '—'}
                  </Descriptions.Item>
                </>
              ) : (
                <Descriptions.Item label="变动说明">{snapshot.changeNote ?? '—'}</Descriptions.Item>
              )}
            </Descriptions>

            <div>
              <h3 className={styles.blockTitle}>逐宗明细</h3>
              <LinesTable lines={snapshot.lines} caption="快照逐宗明细" />
            </div>

            <div>
              <h3 className={styles.blockTitle}>与当前台账差异</h3>
              <div role="region" aria-label="台账差异" tabIndex={0} className={styles.scrollRegion}>
                <Table<OccupancyReportUnitDiff>
                  rowKey="assetUnitId"
                  columns={DIFF_COLUMNS}
                  dataSource={snapshot.differences}
                  pagination={false}
                  size="small"
                  locale={{ emptyText: '快照与当前台账无差异。' }}
                />
              </div>
            </div>

            {exportMutation.isError ? (
              <Alert type="error" showIcon title={errorText(exportMutation.error)} />
            ) : null}

            <Space wrap>
              {/* 导出端点仅需 asset_ops:read，与页面访问同权限，无需再加写守卫。 */}
              <Button
                loading={exportMutation.isPending}
                onClick={() => exportMutation.mutate(snapshot.reportId)}
              >
                导出 CSV
              </Button>
              <CapabilityGuard action="report" resource="asset_ops" fallback={<></>}>
                {snapshot.status === 'submitted' ? (
                  <Space wrap>
                    <Button
                      danger
                      loading={withdrawPreviewMutation.isPending}
                      onClick={() => withdrawPreviewMutation.mutate(snapshot.reportId)}
                    >
                      撤回报送
                    </Button>
                    {withdrawPreviewMutation.isError ? (
                      <Alert
                        type="error"
                        showIcon
                        title={errorText(withdrawPreviewMutation.error)}
                      />
                    ) : null}
                  </Space>
                ) : null}
              </CapabilityGuard>
            </Space>
          </Space>
        ) : null}
      </QueryBoundary>

      <Modal
        title="撤回报送"
        open={withdrawPreview != null}
        onCancel={() => {
          setWithdrawPreview(null);
          withdrawMutation.reset();
        }}
        footer={[
          <Button
            key="cancel"
            onClick={() => {
              setWithdrawPreview(null);
              withdrawMutation.reset();
            }}
          >
            取消
          </Button>,
          <Button
            key="confirm"
            danger
            type="primary"
            loading={withdrawMutation.isPending}
            disabled={withdrawReason.trim() === ''}
            onClick={() => {
              if (withdrawPreview != null) {
                withdrawMutation.mutate(withdrawPreview);
              }
            }}
          >
            确认撤回
          </Button>,
        ]}
      >
        {withdrawPreview != null ? (
          <Space orientation="vertical" size={12} className={styles.sectionStack}>
            <Alert
              type="info"
              showIcon
              title="撤回后原快照与审计记录保留，并生成可重新报送的草稿。"
              description={`报送时间：${formatDateTime(withdrawPreview.submittedAt)}`}
            />
            <Input.TextArea
              aria-label="撤回原因"
              rows={3}
              maxLength={500}
              placeholder="撤回原因（必填）"
              value={withdrawReason}
              onChange={event => setWithdrawReason(event.target.value)}
            />
            {withdrawMutation.isError ? (
              <Alert type="error" showIcon title={errorText(withdrawMutation.error)} />
            ) : null}
          </Space>
        ) : null}
      </Modal>
    </div>
  );
}

// ==================== 页面主体 ====================

function useUrlParams(): {
  year: number;
  operatorId: string;
  period: string;
  reportId: string;
  updateParams: (patch: Record<string, string | null>) => void;
} {
  const [searchParams, setSearchParams] = useSearchParams();
  const operatorParam =
    searchParams.get('operator_party_id') ?? searchParams.get('operatorPartyId') ?? '';
  const periodParam = searchParams.get('period') ?? '';
  const reportId = searchParams.get('report_id') ?? '';
  const yearParam = searchParams.get('year');

  const currentYear = dayjs().year();
  const year = yearParam != null && YEAR_PATTERN.test(yearParam) ? Number(yearParam) : currentYear;
  const period = PERIOD_PATTERN.test(periodParam) ? periodParam : latestEndedPeriod();

  const updateParams = (patch: Record<string, string | null>): void => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (value == null || value === '') {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }
    setSearchParams(next, { replace: true });
  };

  return { year, operatorId: operatorParam, period, reportId, updateParams };
}

export function OccupancyReportsPage(): React.ReactElement {
  const { year, operatorId, period, reportId, updateParams } = useUrlParams();
  const [activeTab, setActiveTab] = useState<TabKey>(reportId !== '' ? 'snapshot' : 'draft');

  const partiesQuery = useQuery({
    queryKey: ['occupancy-operator-parties'],
    queryFn: () => occupancyReportService.listOperatorParties(),
  });
  const parties: OperatorParty[] = partiesQuery.data ?? [];

  useEffect(() => {
    if (reportId !== '') {
      setActiveTab('snapshot');
    }
  }, [reportId]);

  // 未指定运营主体时默认选第一个可用主体，并同步到 URL。
  useEffect(() => {
    if (partiesQuery.isSuccess && operatorId === '' && parties.length > 0) {
      updateParams({ operator_party_id: parties[0]?.id ?? null });
    }
  }, [partiesQuery.isSuccess, parties, operatorId]);

  const yearOptions = useMemo(
    () =>
      Array.from({ length: 6 }, (_, offset) => {
        const optionYear = dayjs().year() - offset;
        return { value: optionYear, label: `${optionYear} 年` };
      }),
    []
  );

  const needsOperator = operatorId === '';

  return (
    <div className={styles.page}>
      <h1 style={{ margin: 0, fontSize: 20 }}>月度出租率报送</h1>

      <div className={styles.toolbar}>
        <div className={styles.toolbarItem}>
          <span className={styles.toolbarLabel}>年度</span>
          <Select<number>
            aria-label="考核范围年度"
            value={year}
            options={yearOptions}
            style={{ width: 120 }}
            onChange={value => updateParams({ year: String(value) })}
          />
        </div>
        <div className={styles.toolbarItem}>
          <span className={styles.toolbarLabel}>运营主体</span>
          <Select
            aria-label="运营主体"
            placeholder="选择运营主体"
            showSearch
            optionFilterProp="label"
            loading={partiesQuery.isPending}
            style={{ width: 240 }}
            value={operatorId === '' ? undefined : operatorId}
            options={parties.map(party => ({ value: party.id, label: party.name }))}
            onChange={value => updateParams({ operator_party_id: value })}
          />
        </div>
        <div className={styles.toolbarItem}>
          <span className={styles.toolbarLabel}>统计月</span>
          <DatePicker
            picker="month"
            allowClear={false}
            aria-label="统计月"
            value={dayjs(`${period}-01`)}
            disabledDate={(value: Dayjs) => value.isAfter(dayjs(), 'month')}
            onChange={value => {
              if (value != null) {
                updateParams({ period: value.format('YYYY-MM') });
              }
            }}
          />
        </div>
        {partiesQuery.isError ? (
          <Alert
            type={isOccupancyForbidden(partiesQuery.error) ? 'warning' : 'error'}
            showIcon
            title={
              isOccupancyForbidden(partiesQuery.error)
                ? '当前账号没有可用的运营主体范围，请联系管理员。'
                : errorText(partiesQuery.error)
            }
          />
        ) : null}
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={key => setActiveTab(key as TabKey)}
        items={[
          {
            key: 'scope',
            label: '考核范围',
            children: needsOperator ? (
              <p className={styles.stateText}>请先选择运营主体。</p>
            ) : (
              <ScopeSection year={year} operatorId={operatorId} />
            ),
          },
          {
            key: 'draft',
            label: '当月草稿',
            children: needsOperator ? (
              <p className={styles.stateText}>请先选择运营主体。</p>
            ) : (
              <DraftSection
                period={period}
                operatorId={operatorId}
                onSubmitted={submittedReportId => {
                  setActiveTab('snapshot');
                  updateParams({ report_id: submittedReportId });
                }}
              />
            ),
          },
          {
            key: 'snapshot',
            label: '历史快照',
            children: <SnapshotSection reportId={reportId} />,
          },
        ]}
      />
    </div>
  );
}

export default OccupancyReportsPage;
