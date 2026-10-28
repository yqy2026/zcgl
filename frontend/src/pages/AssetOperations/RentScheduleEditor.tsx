import { useFieldArray, useForm } from 'react-hook-form';
import { useState } from 'react';
import { Button, Alert } from 'antd';
import type { RentScheduleInput } from '@/services/assetLedgerService';
import styles from './LedgersPage.module.css';

export interface ScheduleFormRow {
  discountAmount?: string;
  stageStart: string;
  stageEnd: string;
  baseRent: string;
  actualRent: string;
  cycle: RentScheduleInput['payment_cycle'];
  dueDay: string;
  increaseRate: string;
  freeMonths: string;
  strategy: 'average' | 'upfront';
}
function iso(date: Date): string {
  return date.toISOString().slice(0, 10);
}
function shiftMonths(start: string, months: number): Date {
  const source = new Date(`${start}T00:00:00Z`);
  const day = source.getUTCDate();
  source.setUTCDate(1);
  source.setUTCMonth(source.getUTCMonth() + months);
  const lastDay = new Date(
    Date.UTC(source.getUTCFullYear(), source.getUTCMonth() + 1, 0)
  ).getUTCDate();
  source.setUTCDate(Math.min(day, lastDay));
  return source;
}
export function buildRentSchedule(row: ScheduleFormRow): RentScheduleInput[] {
  if (row.stageStart === '' || row.stageEnd === '' || row.stageEnd < row.stageStart)
    throw new Error('请填写有效的阶段起止日期');
  if (
    row.baseRent === '' ||
    row.actualRent === '' ||
    Number(row.baseRent) < 0 ||
    Number(row.actualRent) < 0 ||
    !Number.isFinite(Number(row.baseRent)) ||
    !Number.isFinite(Number(row.actualRent))
  )
    throw new Error('请填写非负的原定月租和实际月租');
  const due = Number(row.dueDay);
  if (!Number.isInteger(due) || due < 1 || due > 31) throw new Error('付款日应为 1 至 31 日');
  const freeMonths = Number(row.freeMonths);
  if (!Number.isFinite(freeMonths) || freeMonths < 0) throw new Error('免租月数必须为非负数');
  const common: RentScheduleInput = {
    stage_start: row.stageStart,
    stage_end: row.stageEnd,
    base_monthly_rent: Number(row.baseRent),
    actual_monthly_rent: Number(row.actualRent),
    increase_rate: Number(row.increaseRate),
    free_rent_months: freeMonths,
    discount_amount:
      row.discountAmount != null
        ? Number(row.discountAmount)
        : Math.max(0, Number(row.baseRent) - Number(row.actualRent)),
    payment_cycle: row.cycle,
    due_day: due,
  };
  if (row.strategy !== 'upfront' || freeMonths === 0) return [common];
  if (!Number.isInteger(freeMonths))
    throw new Error('前置免租请填写整数月；零散免租可拆成独立阶段核对');
  const paidStart = shiftMonths(row.stageStart, freeMonths);
  const freeEnd = new Date(paidStart.getTime() - 24 * 60 * 60 * 1000);
  if (iso(freeEnd) >= row.stageEnd) return [{ ...common, actual_monthly_rent: 0 }];
  return [
    { ...common, stage_end: iso(freeEnd), actual_monthly_rent: 0 },
    { ...common, stage_start: iso(paidStart), free_rent_months: 0 },
  ];
}

export default function RentScheduleEditor({
  onChange,
  onValidityChange,
  startDate,
  endDate,
  initialSchedules = [],
}: {
  onChange: (schedules: RentScheduleInput[]) => void;
  onValidityChange?: (valid: boolean) => void;
  startDate: string;
  endDate: string;
  initialSchedules?: RentScheduleInput[];
}): React.ReactElement {
  const form = useForm<{ stages: ScheduleFormRow[] }>({
    defaultValues: {
      stages: initialSchedules.map(stage => ({
        stageStart: stage.stage_start,
        stageEnd: stage.stage_end,
        baseRent: String(stage.base_monthly_rent),
        actualRent: String(stage.actual_monthly_rent),
        cycle: stage.payment_cycle,
        dueDay: String(stage.due_day),
        increaseRate: String(stage.increase_rate ?? 0),
        freeMonths: String(stage.free_rent_months ?? 0),
        strategy: 'average',
        discountAmount: String(stage.discount_amount ?? 0),
      })),
    },
  });
  const array = useFieldArray({ control: form.control, name: 'stages' });
  const [error, setError] = useState('');
  const watched = form.watch('stages');
  const emit = (): void => {
    try {
      const stages = form.getValues('stages').flatMap(buildRentSchedule);
      onChange(stages);
      onValidityChange?.(true);
      setError('');
    } catch (caught) {
      onValidityChange?.(false);
      setError(caught instanceof Error ? caught.message : '请核对租金阶段');
    }
  };
  return (
    <section aria-label="核对租金计划">
      <h3>核对租金计划</h3>
      <p className={styles.muted}>
        按已签条款核对实际月租。首年平均减免请填写减免后的实际月租；前置免租会生成独立的零租金期间，避免重复减免。未覆盖期间不出账。
      </p>
      {array.fields.map((stage, index) => (
        <fieldset key={stage.id} className={styles.stage}>
          <legend>租金阶段 {index + 1}</legend>
          <div className={styles.grid}>
            <label className={styles.field}>
              阶段开始
              <input
                type="date"
                {...form.register(`stages.${index}.stageStart`, { onChange: emit })}
              />
            </label>
            <label className={styles.field}>
              阶段结束
              <input
                type="date"
                {...form.register(`stages.${index}.stageEnd`, { onChange: emit })}
              />
            </label>
            <label className={styles.field}>
              原定月租
              <input
                type="number"
                min="0"
                step="0.01"
                {...form.register(`stages.${index}.baseRent`, { onChange: emit })}
              />
            </label>
            <label className={styles.field}>
              实际月租
              <input
                type="number"
                min="0"
                step="0.01"
                {...form.register(`stages.${index}.actualRent`, { onChange: emit })}
              />
            </label>
            <label className={styles.field}>
              每月减免金额
              <input
                type="number"
                min="0"
                step="0.01"
                {...form.register(`stages.${index}.discountAmount`, { onChange: emit })}
              />
            </label>
            <label className={styles.field}>
              免租减免方式
              <select {...form.register(`stages.${index}.strategy`, { onChange: emit })}>
                <option value="average">首年内按月平均减免</option>
                <option value="upfront">起租后前 N 个月全免</option>
              </select>
            </label>
            <label className={styles.field}>
              免租月数
              <input
                type="number"
                min="0"
                step="0.5"
                {...form.register(`stages.${index}.freeMonths`, { onChange: emit })}
              />
            </label>
            <label className={styles.field}>
              较上年递增比例
              <input
                type="number"
                min="0"
                step="0.01"
                {...form.register(`stages.${index}.increaseRate`, { onChange: emit })}
              />
            </label>
            <label className={styles.field}>
              阶段付款周期
              <select
                {...form.register(`stages.${index}.cycle`, {
                  onChange: event => {
                    const cycle = event.target.value;
                    form.setValue(`stages.${index}.dueDay`, cycle === 'quarterly' ? '15' : '25');
                    emit();
                  },
                })}
              >
                <option value="monthly">月付</option>
                <option value="quarterly">季付</option>
                <option value="yearly">年付</option>
                <option value="custom">自定义</option>
              </select>
            </label>
            <label className={styles.field}>
              阶段付款日
              <input
                type="number"
                min="1"
                max="31"
                {...form.register(`stages.${index}.dueDay`, { onChange: emit })}
              />
            </label>
          </div>
          <p className={styles.muted}>
            核对提示：实际月租 {watched[index]?.actualRent ?? '0'}{' '}
            元；递增仅供核对，实际出账以已核对月租为准。
          </p>
          <Button
            onClick={() => {
              array.remove(index);
              emit();
            }}
          >
            移除租金阶段 {index + 1}
          </Button>
        </fieldset>
      ))}
      {error !== '' ? <Alert type="error" title={error} /> : null}
      <Button
        onClick={() => {
          array.append({
            stageStart: startDate,
            stageEnd: endDate,
            baseRent: '0',
            actualRent: '0',
            cycle: 'monthly',
            dueDay: '25',
            increaseRate: '0',
            freeMonths: '0',
            strategy: 'average',
          });
          emit();
        }}
      >
        添加租金阶段
      </Button>
    </section>
  );
}
