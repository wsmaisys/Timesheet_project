import { beforeAll, describe, expect, it } from 'vitest';
import { formatHoursPair, formatMinutesDecimal, formatMinutesHHMM } from '../format';
import { addDays, ensureTemporal, getWeekDates, getWeekStart } from '../temporal';

beforeAll(async () => {
  await ensureTemporal();
});

describe('format utilities', () => {
  it('formats integer minutes into exact HH:MM and decimal hours', () => {
    expect(formatMinutesHHMM(90)).toBe('1:30');
    expect(formatMinutesDecimal(90)).toBe('1.50');
    expect(formatHoursPair(480)).toBe('8:00 (8.00h)');
  });
});

describe('Temporal PlainDate week calculations', () => {
  it('computes Monday-start week boundaries without timezone drift', () => {
    expect(getWeekStart('2026-11-20', 0)).toBe('2026-11-16');
    expect(getWeekStart('2026-11-16', 0)).toBe('2026-11-16');
    expect(getWeekStart('2026-11-22', 0)).toBe('2026-11-16');
    expect(addDays('2026-11-16', 6)).toBe('2026-11-22');
    expect(getWeekDates('2026-11-16')).toEqual([
      '2026-11-16',
      '2026-11-17',
      '2026-11-18',
      '2026-11-19',
      '2026-11-20',
      '2026-11-21',
      '2026-11-22',
    ]);
  });

  it('handles Sunday week start and DST boundary dates cleanly', () => {
    expect(getWeekStart('2026-03-08', 6)).toBe('2026-03-08');
    expect(addDays('2026-03-08', 7)).toBe('2026-03-15');
  });
});
