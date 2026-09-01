import { useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import PrototypeShell from './PrototypeShell';
import PrototypeSwitcher, { type PrototypeVariant } from './PrototypeSwitcher';
import VariantA from './variants/VariantA';
import VariantB from './variants/VariantB';
import VariantC from './variants/VariantC';
import { projects, workItems, type WorkId } from './prototypeData';

/**
 * PROTOTYPE — throwaway UI used to answer one question.
 * Three low-density ways to operate 50–100 distributed projects,
 * switchable through ?variant=A|B|C on /prototype/asset-operations.
 */
const validVariants = new Set<PrototypeVariant>(['A', 'B', 'C']);

function normalizeVariant(value: string | null): PrototypeVariant {
  return value != null && validVariants.has(value as PrototypeVariant)
    ? (value as PrototypeVariant)
    : 'A';
}

export default function AssetOperationsPrototypePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const variant = normalizeVariant(searchParams.get('variant'));
  const [selectedId, setSelectedId] = useState<WorkId>('collection-01');
  const [resolvedIds, setResolvedIds] = useState<Set<WorkId>>(() => new Set());
  const [selectedProject, setSelectedProject] = useState('东城产业园');
  const [issueOnly, setIssueOnly] = useState(false);
  const [activityMessage, setActivityMessage] = useState<string | null>(null);
  const selected = workItems.find(item => item.id === selectedId) ?? workItems[0];

  if (selected == null) {
    return null;
  }

  const changeVariant = useCallback(
    (nextVariant: PrototypeVariant) => {
      setSearchParams(
        previous => {
          const next = new URLSearchParams(previous);
          next.set('variant', nextVariant);
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const resolveWork = (id: WorkId) => {
    const item = workItems.find(workItem => workItem.id === id);
    if (item == null) {
      return;
    }

    setResolvedIds(previous => {
      const next = new Set(previous);
      next.add(id);
      return next;
    });
    setActivityMessage(`${item.project} · ${item.kind}处理已记录`);
  };

  return (
    <PrototypeShell
      activeNav={variant === 'C' ? '运营项目' : '工作台'}
      activityMessage={activityMessage}
    >
      {variant === 'A' ? (
        <VariantA
          items={workItems}
          selected={selected}
          resolvedIds={resolvedIds}
          onSelect={setSelectedId}
          onResolve={resolveWork}
        />
      ) : variant === 'B' ? (
        <VariantB
          items={workItems}
          selected={selected}
          resolvedIds={resolvedIds}
          onSelect={setSelectedId}
          onResolve={resolveWork}
        />
      ) : (
        <VariantC
          projects={projects}
          selectedProject={selectedProject}
          issueOnly={issueOnly}
          onProjectChange={setSelectedProject}
          onIssueOnlyChange={setIssueOnly}
        />
      )}
      <PrototypeSwitcher current={variant} onChange={changeVariant} />
    </PrototypeShell>
  );
}
