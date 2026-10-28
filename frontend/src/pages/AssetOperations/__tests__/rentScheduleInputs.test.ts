import { expect, it } from 'vitest';
import { buildRentSchedule } from '../RentScheduleEditor';

it('represents upfront free rent as a zero stage without reducing the paid stage twice', () => {
  const result = buildRentSchedule({
    stageStart: '2026-01-01',
    stageEnd: '2026-12-31',
    baseRent: '1200',
    actualRent: '1200',
    cycle: 'quarterly',
    dueDay: '15',
    increaseRate: '0',
    freeMonths: '2',
    strategy: 'upfront',
  });
  expect(result).toMatchObject([
    {
      stage_start: '2026-01-01',
      stage_end: '2026-02-28',
      actual_monthly_rent: 0,
      payment_cycle: 'quarterly',
      due_day: 15,
    },
    { stage_start: '2026-03-01', stage_end: '2026-12-31', actual_monthly_rent: 1200 },
  ]);
});
it('keeps the reviewed actual monthly rent for average relief', () => {
  const result = buildRentSchedule({
    stageStart: '2026-01-01',
    stageEnd: '2026-12-31',
    baseRent: '1200',
    actualRent: '1000',
    cycle: 'monthly',
    dueDay: '25',
    increaseRate: '0',
    freeMonths: '2',
    strategy: 'average',
  });
  expect(result).toHaveLength(1);
  expect(result[0]?.actual_monthly_rent).toBe(1000);
});
