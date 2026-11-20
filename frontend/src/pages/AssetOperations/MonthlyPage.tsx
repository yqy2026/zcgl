/**
 * 本月（资产管理岗月度工作台）
 *
 * 对齐原型 asset-ops-v5「本月」页：四张截止日任务卡（承租租金支付 / 终端租金
 * 收取 / 委托管理费对账 / 出租率报送）+ 随时处理区（到期未处理上游、半年内
 * 到期、档案缺漏、押金待处理、年中新增确认）。任务清单由后端按当前事实
 * 无状态派生，往月未清项带逾期天数；登记动作经台账/对账单/报送页完成，
 * 本页只做汇总与直达（单一写路径）。
 */

import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Progress, Spin, Tag } from 'antd';
import type { TagProps } from 'antd';
import {
  monthlyWorkbenchService,
  type MonthlyMoneyCard,
  type MonthlyMoneyTask,
  type MonthlyWorkbenchView,
} from '@/services/monthlyWorkbenchService';
import { occupancyReportService, type OperatorParty } from '@/services/occupancyReportService';

import styles from './MonthlyPage.module.css';

const FORBIDDEN_CODES = new Set([
  'PARTY_SCOPE_MISSING',
  'PARTY_SCOPE_FORBIDDEN',
  'ASSET_OPS_PERMISSION_DENIED',
  'FORBIDDEN',
]);

const DEPOSIT_STATUS_LABELS: Record<string, string> = {
  receivable_uncollected: '应收未收',
  payable_unpaid: '应付未付',
  refundable_unreturned: '应退未退',
  recoverable_unreceived: '应收回',
  settled: '已结清',
};

const DEPOSIT_STATUS_COLORS: Record<string, TagProps['color']> = {
  receivable_uncollected: 'gold',
  payable_unpaid: 'gold',
  refundable_unreturned: 'red',
  recoverable_unreceived: 'blue',
};

function formatMoney(amount: number): string {
  const rounded = Math.round(amount);
  if (Math.abs(rounded - amount) < 0.005) {
    return `¥${rounded.toLocaleString('zh-CN')}`;
  }
  return `¥${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPercent(rate: number | null): string {
  if (rate == null) {
    return '—';
  }
  return `${(rate * 100).toFixed(1)}%`;
}

function monthNumber(period: string): number {
  return Number(period.slice(5, 7));
}

function isForbiddenError(error: unknown): boolean {
  return (
    error != null &&
    typeof error === 'object' &&
    'code' in error &&
    FORBIDDEN_CODES.has(String((error as { code: unknown }).code))
  );
}

function errorText(error: unknown): string {
  if (error instanceof Error && error.message !== '') {
    return error.message;
  }
  return '请求失败，请重试。';
}

function MoneyCard({
  title,
  card,
  onOpenEntry,
  footer,
}: {
  title: string;
  card: MonthlyMoneyCard;
  onOpenEntry: (task: MonthlyMoneyTask) => void;
  footer?: React.ReactNode;
}): React.ReactElement {
  const isCollection = card.subtitle.includes('本公司收取');
  const summary = `${card.pendingCount} 笔 · 共 ${formatMoney(card.pendingAmount)}${
    card.doneCount > 0 ? ` · 已${isCollection ? '到账' : '付'} ${formatMoney(card.doneAmount)}` : ''
  }`;
  return (
    <section className={styles.card} aria-label={title}>
      <div className={styles.cardHeader}>
        <div className={styles.cardTitleRow}>
          <b className={styles.cardTitle}>{title}</b>
          <span className={styles.cardNote}>{card.subtitle}</span>
        </div>
        <p className={styles.cardSummary}>{summary}</p>
      </div>
      {card.items.length === 0 ? (
        <p className={styles.emptyText}>
          {isCollection ? '本月终端租金已全部到账' : '本月承租租金已全部登记'}
        </p>
      ) : (
        <ul className={styles.rows}>
          {card.items.map(task => {
            const previousMonth = task.period !== card.period;
            const late = task.daysOverdue > 0;
            const partial = task.paidAmount > 0;
            const name = `${task.contractName}${previousMonth ? ` · ${monthNumber(task.period)} 月${isCollection ? '欠租' : '未付'}` : ''}`;
            const sub =
              (isCollection
                ? `${task.counterpartyName}${task.unitLabel != null ? ` · ${task.unitLabel}` : ''}`
                : `付 ${task.counterpartyName}`) +
              (late ? ` · 已逾期 ${task.daysOverdue} 天` : ` · ${task.dueDate.slice(5)} 前`) +
              (partial ? ` · 部分付款 · 欠 ${formatMoney(task.remainingAmount)}` : '');
            return (
              <li key={task.ledgerEntryId}>
                <button
                  type="button"
                  className={styles.taskRow}
                  onClick={() => {
                    onOpenEntry(task);
                  }}
                >
                  <span className={styles.taskMain}>
                    <span className={styles.taskName}>{name}</span>
                    <span className={late ? styles.taskSubLate : styles.taskSub}>{sub}</span>
                  </span>
                  <span className={styles.taskAmount}>{formatMoney(task.remainingAmount)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {card.doneCount > 0 ? (
        <div className={styles.doneRow}>
          已完成 {card.doneCount} 笔 · 共 {formatMoney(card.doneAmount)}（台账可查）
        </div>
      ) : null}
      {footer}
    </section>
  );
}

export default function MonthlyPage(): React.ReactElement {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const operatorParam = params.get('operator_party_id') ?? '';

  const partiesQuery = useQuery({
    queryKey: ['occupancy-operator-parties'],
    queryFn: () => occupancyReportService.listOperatorParties(),
  });
  const parties: OperatorParty[] = partiesQuery.data ?? [];

  useEffect(() => {
    if (partiesQuery.isSuccess && operatorParam === '' && parties.length > 0) {
      const next = new URLSearchParams(params);
      next.set('operator_party_id', parties[0]?.id ?? '');
      setParams(next, { replace: true });
    }
  }, [partiesQuery.isSuccess, parties, operatorParam, params, setParams]);

  const workbenchQuery = useQuery({
    queryKey: ['monthly-workbench', operatorParam],
    queryFn: () => monthlyWorkbenchService.overview({ operatorPartyId: operatorParam }),
    enabled: operatorParam !== '',
  });

  if (operatorParam === '') {
    if (partiesQuery.isLoading) {
      return (
        <div role="status" className={styles.page}>
          <Spin /> 本月工作台加载中
        </div>
      );
    }
    if (partiesQuery.isError) {
      return (
        <div className={styles.page}>
          <Alert
            type="error"
            showIcon
            message="运营主体加载失败"
            description={errorText(partiesQuery.error)}
          />
        </div>
      );
    }
    return (
      <div className={styles.page}>
        <Alert
          type="warning"
          showIcon
          message="尚无可用的运营主体，请先在主体管理中登记法人主体。"
        />
      </div>
    );
  }

  if (workbenchQuery.isLoading) {
    return (
      <div role="status" className={styles.page}>
        <Spin /> 本月工作台加载中
      </div>
    );
  }

  if (workbenchQuery.isError) {
    const error = workbenchQuery.error;
    if (isForbiddenError(error)) {
      return (
        <div className={styles.page}>
          <Alert
            type="warning"
            showIcon
            message="没有可访问的资产范围"
            description="当前账号没有资产运营数据范围，请联系管理员配置后刷新重试。"
          />
        </div>
      );
    }
    return (
      <div className={styles.page}>
        <Alert
          type="error"
          showIcon
          message="本月工作台加载失败"
          description={errorText(error)}
          action={
            <Button
              size="small"
              onClick={() => {
                void workbenchQuery.refetch();
              }}
            >
              重试
            </Button>
          }
        />
      </div>
    );
  }

  const view: MonthlyWorkbenchView | undefined = workbenchQuery.data;
  if (view == null) {
    return (
      <div className={styles.page}>
        <Alert type="error" showIcon title="本月工作台响应缺少数据，请重试。" />
      </div>
    );
  }

  const monthNo = monthNumber(view.month);
  const yearNo = Number(view.month.slice(0, 4));
  const report = view.occupancyReport;
  // 报送卡口径：后端回退到上一已结束自然月（报上月），标题与跳转都用统计月。
  const reportPeriod = report.period || view.month;
  const reportMonthNo = monthNumber(reportPeriod);
  const leftCount = Math.max(view.progress.total - view.progress.done, 0);
  const percent =
    view.progress.total > 0 ? Math.round((view.progress.done / view.progress.total) * 100) : 100;
  const reportTag =
    report.status === 'submitted' ? (
      <Tag color="success">已报送</Tag>
    ) : report.status === 'missing_scope' ? (
      <Tag color="error">缺考核范围</Tag>
    ) : (
      <Tag color="processing">未报送</Tag>
    );
  const gateText =
    report.status === 'missing_scope'
      ? (report.unavailableReason ?? '')
      : report.status === 'draft' && report.gateReasons.length > 0
        ? `报送门槛未满足：${report.gateReasons
            .map(reason =>
              reason === 'pending_units_unconfirmed'
                ? '有待确认宗地'
                : reason === 'change_note_required'
                  ? '较上月有变动，变动说明未填'
                  : reason
            )
            .join('；')}`
        : null;
  const archiveMissing = view.archiveGaps.reduce((sum, gap) => sum + gap.missing, 0);

  const openLedgerEntry = (task: MonthlyMoneyTask): void => {
    const ledgerType = task.contractKind === 'upstream' ? 'upstream_rent' : 'terminal_rent';
    navigate(
      `/asset-operations/ledgers?ledger_type=${ledgerType}&entry_id=${encodeURIComponent(task.ledgerEntryId)}&period=${task.period}`
    );
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <span className={styles.dateLine}>
            {yearNo} 年 {monthNo} 月
            {view.daysLeftInMonth > 0 ? ` · 还剩 ${view.daysLeftInMonth} 天` : ''}
          </span>
          <h1 className={styles.headline}>
            {leftCount > 0 ? `本月还有 ${leftCount} 件没做完` : '本月任务已全部完成'}
          </h1>
        </div>
        <div className={styles.progressBox}>
          <div className={styles.progressMeta}>
            <span>完成进度</span>
            <span>
              {view.progress.done} / {view.progress.total}
            </span>
          </div>
          <Progress percent={percent} showInfo={false} size="small" />
        </div>
      </div>

      <div className={styles.cardGrid}>
        <MoneyCard
          title={`支付 ${monthNo} 月承租租金`}
          card={view.rentPayments}
          onOpenEntry={openLedgerEntry}
        />

        <MoneyCard
          title={`收取 ${monthNo} 月终端租金`}
          card={view.rentCollections}
          onOpenEntry={openLedgerEntry}
          footer={
            <div className={styles.cardFooter}>
              <span>未到账的往月欠租会一直挂着，不随月份消失</span>
              <a
                href="/asset-operations/ledgers?ledger_type=terminal_rent"
                onClick={event => {
                  event.preventDefault();
                  navigate('/asset-operations/ledgers?ledger_type=terminal_rent');
                }}
              >
                终端租金台账 →
              </a>
            </div>
          }
        />

        <section className={styles.card} aria-label="委托管理费对账">
          <div className={styles.cardHeader}>
            <div className={styles.cardTitleRow}>
              <b className={styles.cardTitle}>
                {monthNumber(view.managementFees.period)} 月委托管理费对账
              </b>
              <span className={styles.cardNote}>双方盖章后确认</span>
            </div>
            <p className={styles.cardSummary}>产权方实收终端租金 × 协议比例</p>
          </div>
          {view.managementFees.items.length === 0 ? (
            <p className={styles.emptyText}>上月无委托管理物业</p>
          ) : (
            <ul className={styles.rows}>
              {view.managementFees.items.map(item => {
                const tag =
                  item.status === 'confirmed' ? (
                    <Tag color="success">已确认</Tag>
                  ) : item.status === 'pending_stamp' ? (
                    <Tag color="processing">待盖章</Tag>
                  ) : item.status === 'collecting' ? (
                    <Tag color="warning">收租中</Tag>
                  ) : (
                    <Tag>未出单</Tag>
                  );
                let formula: string;
                if (item.status === 'collecting') {
                  formula = `产权方已收 ${item.receivedLineCount}/${item.lineCount} 户 · 月底仍未收的顺延下月`;
                } else if (item.status === 'missing') {
                  formula = '上月有在管委托物业，尚未出对账单';
                } else if (
                  item.baseAmount != null &&
                  item.feeAmount != null &&
                  item.baseAmount > 0
                ) {
                  const ratePercent = Math.round((item.feeAmount / item.baseAmount) * 1000) / 10;
                  formula = `${item.lineCount}/${item.lineCount} 户已收齐 · ${formatMoney(item.baseAmount)} × ${ratePercent}% = ${formatMoney(item.feeAmount)}${item.status === 'confirmed' ? ' · 双方已盖章' : ''}`;
                } else {
                  formula = '对账单金额待定';
                }
                const target =
                  item.statementId != null
                    ? `/asset-operations/management-fees/${encodeURIComponent(item.statementId)}`
                    : '/asset-operations/ledgers?ledger_type=management_fee';
                return (
                  <li key={`${item.ownerPartyId}-${item.statementId ?? 'missing'}`}>
                    <button
                      type="button"
                      className={styles.taskRow}
                      onClick={() => {
                        navigate(target);
                      }}
                    >
                      <span className={styles.taskMain}>
                        <span className={styles.taskName}>{item.ownerPartyName}</span>
                        <span className={styles.taskSub}>{formula}</span>
                      </span>
                      {tag}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          <div className={styles.flowHint}>
            <span>登记产权方到账</span>
            <span className={styles.flowArrow}>→</span>
            <span>出对账单</span>
            <span className={styles.flowArrow}>→</span>
            <span>双方盖章对账单</span>
            <span className={styles.flowArrow}>→</span>
            <span>确认</span>
          </div>
        </section>

        <section className={styles.card} aria-label="报送存量经营性物业台账">
          <div className={styles.cardHeader}>
            <div className={styles.cardTitleRow}>
              <b className={styles.cardTitle}>报送 {reportMonthNo} 月存量经营性物业台账</b>
              {reportTag}
            </div>
            <p className={styles.cardSummary}>
              {report.status === 'missing_scope'
                ? '缺少生效考核范围，报送关闭'
                : report.status === 'submitted'
                  ? '已报送的数字锁定为快照'
                  : '草稿实时计算，标记报送后锁定快照'}
            </p>
          </div>
          <div className={styles.rateBlock}>
            <span className={styles.rateLabel}>按宗数</span>
            <span className={styles.rateValue}>{formatPercent(report.occupancyRate)}</span>
            <span className={styles.rateMeta}>
              {report.rentedUnitCount ?? '—'} / {report.unitCount ?? '—'}
              {report.rateDelta != null
                ? ` · 较上月 ${(report.rateDelta >= 0 ? '+' : '') + (report.rateDelta * 100).toFixed(1)} 个百分点`
                : ''}
            </span>
          </div>
          <div className={styles.reportActions}>
            <Button
              onClick={() => {
                navigate(
                  `/asset-operations/occupancy-reports?operator_party_id=${encodeURIComponent(operatorParam)}&period=${reportPeriod}`
                );
              }}
            >
              打开报送页
            </Button>
            {gateText != null ? <span className={styles.gateText}>{gateText}</span> : null}
          </div>
        </section>
      </div>

      <div className={styles.sectionLabel}>
        <b style={{ fontSize: '0.9375rem' }}>随时处理</b>
        <span className={styles.sectionLabelHint}>没有固定截止日，不计入本月进度</span>
      </div>

      <div className={styles.anytimeGrid}>
        {view.expiredUpstream.length > 0 ? (
          <section className={`${styles.card} ${styles.alertCard} ${styles.span2}`}>
            <div className={styles.cardHeader}>
              <div className={styles.cardTitleRow}>
                <b className={`${styles.cardTitle} ${styles.alertCardTitle}`}>
                  上游合同已到期，尚未续签或退出
                </b>
                <span className={styles.cardNote}>
                  期间单元仍按在管计宗；名下的终端合同暂无上游依据
                </span>
              </div>
            </div>
            <ul className={styles.rows}>
              {view.expiredUpstream.map(item => (
                <li key={item.contractId}>
                  <div className={styles.infoRow}>
                    <span className={styles.infoMain}>
                      <span className={styles.infoName}>
                        {item.name} · {item.contractNumber} ·{' '}
                        {item.contractType === 'lease' ? '承租合同' : '委托管理协议'}
                      </span>
                      <span className={styles.infoSub}>
                        到期 {item.endDate} · 已过 {item.daysPast} 天 · {item.unitCount} 个单元 ·
                        在租 {item.activeTerminalCount} 户
                        {item.hasPendingRenewal ? ' · 续签待生效' : ''}
                      </span>
                    </span>
                    <Button
                      size="small"
                      onClick={() => {
                        navigate(
                          `/asset-operations/contracts/upstream?contract_id=${encodeURIComponent(item.contractId)}`
                        );
                      }}
                    >
                      查看合同并处理
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className={styles.card} aria-label="半年内到期的上游合同">
          <div className={styles.cardHeader}>
            <div className={styles.cardTitleRow}>
              <b className={styles.cardTitle}>半年内到期的上游合同</b>
              <span className={styles.cardNote}>点开查看合同</span>
            </div>
          </div>
          {view.expiringUpstream.length === 0 ? (
            <p className={styles.emptyText}>半年内没有到期的上游合同</p>
          ) : (
            <ul className={styles.rows}>
              {view.expiringUpstream.map(item => (
                <li key={item.contractId}>
                  <button
                    type="button"
                    className={styles.taskRow}
                    onClick={() => {
                      navigate(
                        `/asset-operations/contracts/upstream?contract_id=${encodeURIComponent(item.contractId)}`
                      );
                    }}
                  >
                    <span className={styles.taskMain}>
                      <span className={styles.taskName}>
                        {item.name} · {item.contractType === 'lease' ? '承租合同' : '委托管理协议'}
                      </span>
                      <span className={styles.infoSub}>
                        {item.ownerPartyName}
                        {item.overrunTerminalCount > 0
                          ? ` · ${item.overrunTerminalCount} 份终端合同租期超出到期日`
                          : ''}
                      </span>
                    </span>
                    <span className={styles.taskSub}>{item.endDate}</span>
                    <Tag color={item.daysLeft <= 90 ? 'red' : 'gold'}>{item.daysLeft} 天</Tag>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className={styles.card} aria-label="档案缺漏">
          <div className={styles.cardHeader}>
            <div className={styles.cardTitleRow}>
              <b className={styles.cardTitle}>档案缺漏 · 共 {archiveMissing} 份</b>
              <a
                href="/asset-operations/archive"
                onClick={event => {
                  event.preventDefault();
                  navigate('/asset-operations/archive');
                }}
              >
                去档案补齐 →
              </a>
            </div>
          </div>
          {archiveMissing === 0 && view.unlinkedUnitCount === 0 ? (
            <p className={styles.emptyText}>档案齐全</p>
          ) : (
            <ul className={styles.rows}>
              {view.archiveGaps.map(gap => (
                <li key={gap.documentType}>
                  <button
                    type="button"
                    className={styles.taskRow}
                    onClick={() => {
                      navigate('/asset-operations/archive');
                    }}
                  >
                    <span className={styles.taskMain}>
                      <span className={styles.taskName}>{gap.label}</span>
                    </span>
                    <span
                      className={styles.taskAmount}
                      style={{ color: 'var(--color-error, #cf1322)' }}
                    >
                      缺 {gap.missing}
                    </span>
                  </button>
                </li>
              ))}
              {view.unlinkedUnitCount > 0 ? (
                <li>
                  <button
                    type="button"
                    className={styles.taskRow}
                    onClick={() => {
                      navigate('/asset-operations/units');
                    }}
                  >
                    <span className={styles.taskMain}>
                      <span className={styles.taskName}>未关联任何产权证的物业</span>
                    </span>
                    <span
                      className={styles.taskAmount}
                      style={{ color: 'var(--color-error, #cf1322)' }}
                    >
                      {view.unlinkedUnitCount} 宗
                    </span>
                  </button>
                </li>
              ) : null}
            </ul>
          )}
        </section>

        <section className={`${styles.card} ${styles.span2}`} aria-label="押金待处理">
          <div className={styles.cardHeader}>
            <div className={styles.cardTitleRow}>
              <b className={styles.cardTitle}>押金待处理</b>
              <span className={styles.cardNote}>应收未收 · 应付未付 · 应退未退 · 应收回</span>
            </div>
          </div>
          {view.depositsPending.length === 0 ? (
            <p className={styles.emptyText}>没有待处理的押金</p>
          ) : (
            <ul className={styles.rows}>
              {view.depositsPending.map(item => (
                <li key={item.depositId}>
                  <div className={styles.infoRow}>
                    <span className={styles.infoMain}>
                      <span className={styles.infoName}>
                        {item.contractNumber} · {item.counterpartyName}
                      </span>
                      <span className={styles.infoSub}>
                        {item.contractKind === 'upstream' ? '承租合同' : '终端合同'} ·{' '}
                        {item.collector === 'operator' ? '本公司收取' : '产权方收取'}
                      </span>
                    </span>
                    <span className={styles.infoAmount}>
                      欠 {formatMoney(item.outstandingAmount)} / 共 {formatMoney(item.agreedAmount)}
                    </span>
                    <Tag color={DEPOSIT_STATUS_COLORS[item.status] ?? 'default'}>
                      {DEPOSIT_STATUS_LABELS[item.status] ?? item.status}
                    </Tag>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {view.pendingScopeUnits.length > 0 ? (
          <div className={`${styles.pendingScope} ${styles.span2}`}>
            <b className={styles.pendingScopeTitle}>
              年中新增 {view.pendingScopeUnits.length} 宗经营性物业，是否纳入 {yearNo} 考核？
            </b>
            {view.pendingScopeUnits.map(unit => (
              <div key={unit.assetUnitId} className={styles.pendingScopeRow}>
                <span className={styles.pendingScopeText}>
                  {unit.unitName}（{unit.unitCode}）·{' '}
                  {unit.reason === 'new_takeover' ? '新接管' : '接管边界待确认'} ·
                  确认纳入后才计入本月报送
                </span>
                <Button
                  size="small"
                  onClick={() => {
                    navigate(
                      `/asset-operations/units?unit_id=${encodeURIComponent(unit.assetUnitId)}`
                    );
                  }}
                >
                  查看
                </Button>
                <Button
                  size="small"
                  type="primary"
                  onClick={() => {
                    navigate(
                      `/asset-operations/occupancy-reports?operator_party_id=${encodeURIComponent(operatorParam)}&period=${reportPeriod}`
                    );
                  }}
                >
                  去考核范围确认
                </Button>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
