/* Temporal loader & location-agnostic calendar helpers (modern-web-guidance: capture-location-agnostic-data) */

let temporalReadyPromise: Promise<void> | null = null;

export function ensureTemporal(): Promise<void> {
  if (typeof globalThis.Temporal !== 'undefined') {
    return Promise.resolve();
  }
  if (!temporalReadyPromise) {
    temporalReadyPromise = import('temporal-polyfill').then((mod) => {
      if (typeof globalThis.Temporal === 'undefined') {
        Object.assign(globalThis, { Temporal: mod.Temporal });
      }
      if (mod.toTemporalInstant && !('toTemporalInstant' in Date.prototype)) {
        (Date.prototype as unknown as { toTemporalInstant: typeof mod.toTemporalInstant }).toTemporalInstant =
          mod.toTemporalInstant;
      }
    });
  }
  return temporalReadyPromise;
}

export function todayPlainDate(timeZone?: string): string {
  if (timeZone) {
    try {
      return Temporal.Now.plainDateISO(timeZone).toString();
    } catch {
      // Fall back to system zone if user timezone is invalid
    }
  }
  return Temporal.Now.plainDateISO().toString();
}

export function addDays(isoDate: string, days: number): string {
  const pd = Temporal.PlainDate.from(isoDate);
  return pd.add({ days }).toString();
}

export function comparePlainDates(a: string, b: string): number {
  return Temporal.PlainDate.compare(Temporal.PlainDate.from(a), Temporal.PlainDate.from(b));
}

/**
 * Returns the canonical period_start (ISO YYYY-MM-DD) containing `isoDate`.
 * Temporal dayOfWeek uses 1=Monday..7=Sunday; settings weekStartDay uses 0=Monday..6=Sunday.
 */
export function getWeekStart(isoDate: string, weekStartDay = 0): string {
  const pd = Temporal.PlainDate.from(isoDate);
  const currentZeroBased = pd.dayOfWeek - 1; // 0..6
  const delta = (currentZeroBased - weekStartDay + 7) % 7;
  return pd.subtract({ days: delta }).toString();
}

export function getWeekDates(periodStart: string): string[] {
  const start = Temporal.PlainDate.from(periodStart);
  return Array.from({ length: 7 }, (_, i) => start.add({ days: i }).toString());
}

export function getMonthStart(isoDate: string): string {
  const pd = Temporal.PlainDate.from(isoDate);
  return pd.with({ day: 1 }).toString();
}

export function formatCalendarDate(isoDate: string, locale = 'en-US'): string {
  const pd = Temporal.PlainDate.from(isoDate);
  return pd.toLocaleString(locale, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

export function formatCalendarFull(isoDate: string, locale = 'en-US'): string {
  const pd = Temporal.PlainDate.from(isoDate);
  return pd.toLocaleString(locale, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatUtcTimestamp(isoTimestamp: string | null | undefined, timeZone = 'UTC'): string {
  if (!isoTimestamp) return '—';
  try {
    const instant = Temporal.Instant.from(isoTimestamp);
    const zdt = instant.toZonedDateTimeISO(timeZone);
    return new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone,
    }).format(new Date(zdt.epochMilliseconds));
  } catch {
    return isoTimestamp;
  }
}
