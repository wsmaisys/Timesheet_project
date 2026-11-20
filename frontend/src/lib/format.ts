export function formatMinutesHHMM(minutes: number): string {
  const safe = Math.max(0, Math.round(minutes));
  const hrs = Math.floor(safe / 60);
  const mins = safe % 60;
  return `${hrs}:${mins.toString().padStart(2, '0')}`;
}

export function formatMinutesDecimal(minutes: number): string {
  return (minutes / 60).toFixed(2);
}

export function formatHoursPair(minutes: number): string {
  return `${formatMinutesHHMM(minutes)} (${formatMinutesDecimal(minutes)}h)`;
}

export function weekDayLabel(dayIndex: number): string {
  const names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  return names[dayIndex] ?? 'Monday';
}

export function triggerCsvDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
