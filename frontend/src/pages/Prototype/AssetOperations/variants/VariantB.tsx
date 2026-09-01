import { CheckOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons';
import type { WorkId, WorkItem } from '../prototypeData';
import styles from '../AssetOperationsPrototype.module.css';

interface VariantBProps {
  items: WorkItem[];
  selected: WorkItem;
  resolvedIds: ReadonlySet<WorkId>;
  onSelect: (id: WorkId) => void;
  onResolve: (id: WorkId) => void;
}

export default function VariantB({
  items,
  selected,
  resolvedIds,
  onSelect,
  onResolve,
}: VariantBProps) {
  const selectedIndex = items.findIndex(item => item.id === selected.id);
  const isResolved = resolvedIds.has(selected.id);

  const move = (offset: number) => {
    const next = items[(selectedIndex + offset + items.length) % items.length];
    if (next != null) {
      onSelect(next.id);
    }
  };

  return (
    <div className={styles.focusPage}>
      <header className={styles.focusLead}>
        <h1>一次只处理一件事</h1>
        <p>当前显示跨项目队列中最紧急的事项。</p>
      </header>

      <section className={styles.focusSheet} aria-live="polite">
        <div className={styles.focusPosition}>
          <span>
            {selectedIndex + 1} / {items.length}
          </span>
          <div>
            <button type="button" onClick={() => move(-1)} aria-label="上一件任务">
              <LeftOutlined />
            </button>
            <button type="button" onClick={() => move(1)} aria-label="下一件任务">
              <RightOutlined />
            </button>
          </div>
        </div>

        <span className={`${styles.focusKind} ${styles[`text_${selected.tone}`]}`}>
          {selected.kind} · {selected.due}
        </span>
        <h2>{selected.title}</h2>
        <p className={styles.focusReason}>{selected.reason}</p>

        <dl className={styles.focusFacts}>
          <div>
            <dt>项目与位置</dt>
            <dd>
              {selected.project}
              <small>
                {selected.address} · {selected.space}
              </small>
            </dd>
          </div>
          <div>
            <dt>责任人</dt>
            <dd>
              {selected.owner}
              <small>{selected.due}</small>
            </dd>
          </div>
          <div>
            <dt>已有证据</dt>
            <dd>{selected.evidence}</dd>
          </div>
        </dl>

        <div className={styles.focusAction}>
          <span>
            <small>现在要做</small>
            <strong>{selected.nextAction}</strong>
          </span>
          <button
            type="button"
            className={isResolved ? styles.doneButton : styles.primaryButton}
            onClick={() => onResolve(selected.id)}
            disabled={isResolved}
          >
            {isResolved ? (
              <>
                <CheckOutlined /> 已记录
              </>
            ) : (
              '开始处理'
            )}
          </button>
        </div>
      </section>

      <section className={styles.nextQueue}>
        <h2>后面还有 {items.length - 1} 件</h2>
        {items
          .filter(item => item.id !== selected.id)
          .slice(0, 3)
          .map(item => (
            <button key={item.id} type="button" onClick={() => onSelect(item.id)}>
              <span>{item.kind}</span>
              <strong>{item.title}</strong>
              <small>
                {item.project} · {item.due}
              </small>
            </button>
          ))}
      </section>
    </div>
  );
}
