import ArchiveDocumentsPanel from './ArchiveDocumentsPanel';
import styles from './HandoverDocumentsPanel.module.css';

export default function ContractScanPanel({
  kind,
  contractId,
}: {
  kind: 'upstream' | 'terminal';
  contractId: string;
}): React.ReactElement {
  return (
    <section className={styles.panel}>
      <h3>合同扫描件档案</h3>
      <p>维护已签扫描件，替换保留历史版本，不改动合同原有的扫描件引用。</p>
      <ArchiveDocumentsPanel
        targetId={contractId}
        targetType={kind === 'upstream' ? 'upstream_contract' : 'terminal_contract'}
      />
    </section>
  );
}
