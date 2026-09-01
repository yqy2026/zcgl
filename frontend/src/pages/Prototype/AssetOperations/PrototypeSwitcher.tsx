import { useEffect } from 'react';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import styles from './AssetOperationsPrototype.module.css';

export type PrototypeVariant = 'A' | 'B' | 'C';

const variants: PrototypeVariant[] = ['A', 'B', 'C'];
const variantNames: Record<PrototypeVariant, string> = {
  A: '今日清单',
  B: '一步一事',
  C: '项目长尾',
};

interface PrototypeSwitcherProps {
  current: PrototypeVariant;
  onChange: (variant: PrototypeVariant) => void;
}

export default function PrototypeSwitcher({ current, onChange }: PrototypeSwitcherProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        (target instanceof HTMLElement && target.isContentEditable)
      ) {
        return;
      }

      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') {
        return;
      }

      const currentIndex = variants.indexOf(current);
      const offset = event.key === 'ArrowLeft' ? -1 : 1;
      const next = variants[(currentIndex + offset + variants.length) % variants.length];
      if (next != null) {
        onChange(next);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [current, onChange]);

  if (import.meta.env.DEV !== true) {
    return null;
  }

  const cycle = (offset: number) => {
    const currentIndex = variants.indexOf(current);
    const next = variants[(currentIndex + offset + variants.length) % variants.length];
    if (next != null) {
      onChange(next);
    }
  };

  return (
    <div className={styles.prototypeSwitcher} aria-label="原型方案切换器">
      <button type="button" onClick={() => cycle(-1)} aria-label="上一个方案">
        <LeftOutlined />
      </button>
      <span>
        {current} · {variantNames[current]}
      </span>
      <button type="button" onClick={() => cycle(1)} aria-label="下一个方案">
        <RightOutlined />
      </button>
    </div>
  );
}
