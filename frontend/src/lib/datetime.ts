/**
 * DateTime utilities for PatientTriage.ai.
 * 
 * The FastAPI backend emits naive UTC timestamps without timezone offset (e.g. "2026-08-28T18:48:46.312764").
 * JavaScript's `new Date(...)` will parse naive ISO strings as local time, shifting all clocks.
 * All timestamp parsing must go through `parseBackendUtc`.
 */

/**
 * Parses a backend naive UTC timestamp string into a JavaScript Date object.
 */
export function parseBackendUtc(s: string | null | undefined): Date | null {
  if (!s) return null;
  // If string already has a timezone indicator (Z or +00:00 or -05:00), use as is.
  // Otherwise append 'Z' to treat it strictly as UTC.
  const isUtc = /[Zz]|[+-]\d{2}(?::?\d{2})?$/.test(s);
  const iso = isUtc ? s : `${s}Z`;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Formats a Date object to a naive UTC ISO string acceptable by the backend.
 */
export function toBackendUtc(d: Date = new Date()): string {
  return d.toISOString().replace(/\.\d{3}Z$/, '');
}

/**
 * Formats a timestamp into a 24-hour clock string (HH:mm:ss or HH:mm).
 */
export function formatClock(input: string | Date | null | undefined, includeSeconds = false): string {
  const d = typeof input === 'string' ? parseBackendUtc(input) : input;
  if (!d) return '--:--';
  return d.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: includeSeconds ? '2-digit' : undefined,
    hour12: false,
  });
}

/**
 * Formats a timestamp into a human-readable relative time ("just now", "3m ago", "2h ago").
 */
export function formatRelative(input: string | Date | null | undefined, now: Date = new Date()): string {
  const d = typeof input === 'string' ? parseBackendUtc(input) : input;
  if (!d) return '--';
  
  const diffMs = now.getTime() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  
  if (diffSec < 10) return 'just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

/**
 * Formats a fractional minute value into a human-readable duration.
 * e.g. 0.002 -> "<1m", 18.4 -> "18m", 95 -> "1h 35m"
 */
export function formatMinutes(minutes: number | null | undefined): string {
  if (minutes == null || isNaN(minutes)) return '--';
  if (minutes < 0.5 && minutes >= 0) return '<1m';
  
  const totalMins = Math.round(minutes);
  if (totalMins < 60) {
    return `${totalMins}m`;
  }
  
  const hours = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

/**
 * Formats a date string to YYYY-MM-DD or readable date.
 */
export function formatDate(input: string | Date | null | undefined): string {
  const d = typeof input === 'string' ? parseBackendUtc(input) : input;
  if (!d) return '--';
  return d.toLocaleDateString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}
