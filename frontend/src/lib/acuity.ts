export interface AcuityConfig {
  level: number;
  name: string;
  shortName: string;
  description: string;
  bgClass: string;
  textClass: string;
  borderClass: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  dotColor: string;
  lightBg: string;
  hex: string;
}

// Clinical acuity ramp (ESI 1-5). `bgClass`/`textClass`/`borderClass`/`lightBg` describe the
// soft tinted CONTAINER a badge or row sits inside; `badgeBg`/`badgeText`/`badgeBorder` describe
// the solid pill badge itself. Values match the WCAG AAA-targeted light clinical palette.
export const ACUITY_CONFIG: Record<number, AcuityConfig> = {
  1: {
    level: 1,
    name: 'Immediate / Resuscitation',
    shortName: 'Immediate',
    description: 'Threat to life or limb; requires immediate aggressive intervention.',
    bgClass: 'bg-rose-500/10',
    textClass: 'text-rose-900',
    borderClass: 'border-rose-300/30',
    badgeBg: 'bg-rose-500/15',
    badgeText: 'text-rose-800 font-bold',
    badgeBorder: 'border-rose-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
    dotColor: 'bg-rose-600',
    lightBg: 'bg-rose-500/10',
    hex: '#E11D48',
  },
  2: {
    level: 2,
    name: 'Emergent',
    shortName: 'Emergent',
    description: 'High risk situation, confused/lethargic/disoriented, or severe pain/distress.',
    bgClass: 'bg-amber-500/10',
    textClass: 'text-amber-900',
    borderClass: 'border-amber-300/30',
    badgeBg: 'bg-amber-500/15',
    badgeText: 'text-amber-800 font-bold',
    badgeBorder: 'border-amber-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
    dotColor: 'bg-amber-600',
    lightBg: 'bg-amber-500/10',
    hex: '#D97706',
  },
  3: {
    level: 3,
    name: 'Urgent',
    shortName: 'Urgent',
    description: 'Normal vitals, requires multiple hospital resources.',
    bgClass: 'bg-yellow-500/12',
    textClass: 'text-yellow-950',
    borderClass: 'border-yellow-300/30',
    badgeBg: 'bg-yellow-500/18',
    badgeText: 'text-yellow-900 font-bold',
    badgeBorder: 'border-yellow-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
    dotColor: 'bg-yellow-600',
    lightBg: 'bg-yellow-500/10',
    hex: '#CA8A04',
  },
  4: {
    level: 4,
    name: 'Less Urgent',
    shortName: 'Less Urgent',
    description: 'Requires one diagnostic or therapeutic resource.',
    bgClass: 'bg-emerald-500/10',
    textClass: 'text-emerald-900',
    borderClass: 'border-emerald-300/30',
    badgeBg: 'bg-emerald-500/15',
    badgeText: 'text-emerald-800 font-bold',
    badgeBorder: 'border-emerald-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
    dotColor: 'bg-emerald-600',
    lightBg: 'bg-emerald-500/10',
    hex: '#059669',
  },
  5: {
    level: 5,
    name: 'Non-Urgent',
    shortName: 'Non-Urgent',
    description: 'No resources required (e.g. medication prescription only).',
    bgClass: 'bg-blue-500/10',
    textClass: 'text-blue-900',
    borderClass: 'border-blue-300/30',
    badgeBg: 'bg-blue-500/15',
    badgeText: 'text-blue-800 font-bold',
    badgeBorder: 'border-blue-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
    dotColor: 'bg-blue-600',
    lightBg: 'bg-blue-500/10',
    hex: '#2563EB',
  },
};

export function getAcuityConfig(level: number | null | undefined): AcuityConfig {
  if (level == null || !(level in ACUITY_CONFIG)) {
    return {
      level: 0,
      name: 'Unassigned',
      shortName: 'Unassigned',
      description: 'No clinical acuity assigned yet.',
      bgClass: 'bg-slate-500/10',
      textClass: 'text-slate-700',
      borderClass: 'border-slate-300/30',
      badgeBg: 'bg-slate-500/10',
      badgeText: 'text-slate-700 font-medium',
      badgeBorder: 'border-slate-300/30 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]',
      dotColor: 'bg-slate-400',
      lightBg: 'bg-slate-500/10',
      hex: '#94A3B8',
    };
  }
  return ACUITY_CONFIG[level];
}
