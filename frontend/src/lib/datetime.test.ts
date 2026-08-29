import { describe, it, expect } from 'vitest';
import { parseBackendUtc, toBackendUtc, formatMinutes, formatRelative } from './datetime';

describe('datetime utilities', () => {
  it('parseBackendUtc parses naive UTC string to UTC date correctly', () => {
    const raw = '2026-08-28T18:48:46.312764';
    const parsed = parseBackendUtc(raw);
    expect(parsed).not.toBeNull();
    expect(parsed?.getUTCFullYear()).toBe(2026);
    expect(parsed?.getUTCMonth()).toBe(7); // 0-indexed August
    expect(parsed?.getUTCDate()).toBe(28);
    expect(parsed?.getUTCHours()).toBe(18);
    expect(parsed?.getUTCMinutes()).toBe(48);
    expect(parsed?.getUTCSeconds()).toBe(46);
  });

  it('parseBackendUtc handles strings already ending with Z or offset', () => {
    const raw = '2026-08-28T18:48:46Z';
    const parsed = parseBackendUtc(raw);
    expect(parsed?.getUTCHours()).toBe(18);
  });

  it('toBackendUtc serializes date to naive UTC string', () => {
    const d = new Date(Date.UTC(2026, 7, 28, 18, 48, 46));
    const s = toBackendUtc(d);
    expect(s).toBe('2026-08-28T18:48:46');
  });

  it('formatMinutes formats fractional and large minutes', () => {
    expect(formatMinutes(null)).toBe('--');
    expect(formatMinutes(0.00208)).toBe('<1m');
    expect(formatMinutes(18.4)).toBe('18m');
    expect(formatMinutes(60)).toBe('1h');
    expect(formatMinutes(95)).toBe('1h 35m');
  });

  it('formatRelative returns accurate relative descriptions', () => {
    const now = new Date(Date.UTC(2026, 7, 28, 18, 50, 0));
    const fiveSecAgo = new Date(Date.UTC(2026, 7, 28, 18, 49, 55));
    const twoMinAgo = new Date(Date.UTC(2026, 7, 28, 18, 48, 0));
    const threeHoursAgo = new Date(Date.UTC(2026, 7, 28, 15, 50, 0));

    expect(formatRelative(fiveSecAgo, now)).toBe('just now');
    expect(formatRelative(twoMinAgo, now)).toBe('2m ago');
    expect(formatRelative(threeHoursAgo, now)).toBe('3h ago');
  });
});
