import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Alert, Button } from 'antd';
import { managementFeeService } from '@/services/managementFeeService';
import { isLedgerForbidden } from '@/services/assetLedgerService';
import styles from './LedgersPage.module.css';

const statusNames = {
  collecting: '收租中',
  pending_stamp: '待盖章',
  confirmed: '已确认',
  superseded: '已更正',
  upcoming: '未到',
  missing: '暂无对账单',
};
const money = (amount: number) =>
  `¥${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function ManagementFeeLedger({
  yearText,
}: {
  yearText: string;
}): React.ReactElement {
  const year = Number(yearText);
  const query = useQuery({
    queryKey: ['management-fee-matrix', year],
    queryFn: () => managementFeeService.matrix(year),
    enabled: /^[1-9][0-9]{3}$/.test(yearText) && year <= 9998,
  });
  return (
    <>
      <div>
        <Button
          onClick={() => void query.refetch()}
          disabled={!/^[1-9][0-9]{3}$/.test(yearText) || year > 9998}
        >
          刷新台账
        </Button>
      </div>
      {query.isLoading ? <p role="status">正在读取管理费台账…</p> : null}
      {query.isError ? (
        <Alert
          type="error"
          showIcon
          title={
            isLedgerForbidden(query.error) ? '暂无管理费台账访问权限' : '管理费台账读取失败，请重试'
          }
        />
      ) : null}
      {query.data != null && !query.isError ? (
        <>
          <div className={styles.summary}>
            <strong>全年已确认 {money(query.data.total_confirmed_amount)}</strong>
          </div>
          <p className={styles.muted}>
            按产权方汇总，全年合计仅计入已确认金额。待盖章与收租中金额为试算，选择月份查看对账单。
          </p>
          {query.data.rows.length === 0 ? (
            <section className={styles.panel}>
              <h2>本年暂无管理费对账单</h2>
              <p>核对委托管理协议与直签合同的绑定及租金阶段，登记合同账期后将自动生成对账单。</p>
              <Link to="/asset-operations/contracts/upstream">核对委托管理协议</Link>
            </section>
          ) : (
            <div
              className={styles.scroll}
              tabIndex={0}
              role="region"
              aria-label="全年委托管理费台账"
            >
              <table className={styles.matrix}>
                <thead>
                  <tr>
                    <th scope="col">产权方</th>
                    {Array.from({ length: 12 }, (_, i) => (
                      <th
                        scope="col"
                        key={i}
                        className={i + 1 === query.data.current_month ? styles.current : ''}
                      >
                        {i + 1}月
                      </th>
                    ))}
                    <th scope="col">全年已确认</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.rows.map(row => (
                    <tr key={row.owner_party_id}>
                      <th scope="row">{row.owner_name}</th>
                      {row.months.map(month => (
                        <td
                          key={month.month}
                          className={
                            month.month === query.data.current_month
                              ? styles.current
                              : month.status === 'upcoming'
                                ? styles.future
                                : ''
                          }
                        >
                          {month.statement_id != null ? (
                            <Link
                              to={`/asset-operations/management-fees/${encodeURIComponent(month.statement_id)}`}
                            >
                              {statusNames[month.status]}
                              {month.fee_amount != null ? (
                                <>
                                  <br />
                                  {month.status !== 'confirmed' ? '试算 ' : ''}
                                  {money(month.fee_amount)}
                                </>
                              ) : null}
                            </Link>
                          ) : (
                            statusNames[month.status]
                          )}
                        </td>
                      ))}
                      <td>{money(row.total_confirmed_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </>
  );
}
