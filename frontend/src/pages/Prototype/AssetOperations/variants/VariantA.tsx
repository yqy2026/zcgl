import { CheckOutlined, DownOutlined, RightOutlined } from '@ant-design/icons';
import type { WorkId, WorkItem } from '../prototypeData';
import styles from '../AssetOperationsPrototype.module.css';

interface VariantAProps {
  items: WorkItem[];
  selected: WorkItem;
  resolvedIds: ReadonlySet<WorkId>;
  onSelect: (id: WorkId) => void;
  onResolve: (id: WorkId) => void;
}

export default function VariantA({
  items,
  selected,
  resolvedIds,
  onSelect,
  onResolve,
}: VariantAProps) {
  return (
    <div className={styles.pageFrame}>
      <header className={styles.pageLead}>
        <div>
          <h1>今天先处理 5 件事</h1>
          <p>系统已从 86 个项目中排好顺序。处理完一件，再看下一件。</p>
        </div>
        <div className={styles.summaryLine} aria-label="今日任务概况">
          <span>
            <strong>1</strong> 已逾期
          </span>
          <span>
            <strong>2</strong> 今天到期
          </span>
          <span>
            <strong>4</strong> 个项目
          </span>
        </div>
      </header>

      <section className={styles.taskSurface}>
        <div className={styles.listToolbar}>
          <div className={styles.taskTabs} aria-label="任务范围">
            <button type="button" className={styles.tabActive}>
              待我处理
            </button>
            <button type="button">团队待办</button>
            <button type="button">已处理</button>
          </div>
          <button type="button" className={styles.quietButton}>
            全部区域 <DownOutlined aria-hidden="true" />
          </button>
        </div>

        <ol className={styles.taskList}>
          {items.map(item => {
            const isSelected = selected.id === item.id;
            const isResolved = resolvedIds.has(item.id);
            return (
              <li key={item.id} className={styles.taskEntry}>
                <button
                  type="button"
                  className={isSelected ? styles.taskRowSelected : styles.taskRow}
                  onClick={() => onSelect(item.id)}
                  aria-expanded={isSelected}
                >
                  <span className={`${styles.kindMark} ${styles[`tone_${item.tone}`]}`}>
                    {isResolved ? <CheckOutlined aria-hidden="true" /> : item.kind}
                  </span>
                  <span className={styles.taskTitle}>
                    <strong>{item.title}</strong>
                    <small>
                      {item.project} · {item.address} · {item.space}
                    </small>
                  </span>
                  <span className={styles.taskOwner}>{item.owner}</span>
                  <span className={`${styles.taskDue} ${styles[`text_${item.tone}`]}`}>
                    {isResolved ? '已记录' : item.due}
                  </span>
                  <RightOutlined className={styles.rowChevron} aria-hidden="true" />
                </button>

                {isSelected ? (
                  <div className={styles.taskDetail}>
                    <p>{item.reason}</p>
                    <dl>
                      <div>
                        <dt>下一步</dt>
                        <dd>{item.nextAction}</dd>
                      </div>
                      <div>
                        <dt>现有证据</dt>
                        <dd>{item.evidence}</dd>
                      </div>
                    </dl>
                    <button
                      type="button"
                      className={isResolved ? styles.doneButton : styles.primaryButton}
                      onClick={() => onResolve(item.id)}
                      disabled={isResolved}
                    >
                      {isResolved
                        ? '处理已记录'
                        : item.kind === '收款'
                          ? '确认流水匹配'
                          : '记录处理进度'}
                    </button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}
