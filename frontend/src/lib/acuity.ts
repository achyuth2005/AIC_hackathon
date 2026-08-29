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

export const ACUITY_CONFIG: Record<number, AcuityConfig> = {
  1: {
    level: 1,
    name: 'Immediate / Resuscitation',
    shortName: 'Immediate',
    description: 'Threat to life or limb; requires immediate aggressive intervention.',
    bgClass: 'bg-red-600',
    textClass: 'text-red-400',
    borderClass: 'border-red-600',
    badgeBg: 'bg-red-600',
    badgeText: 'text-white',
    badgeBorder: 'border-red-700',
    dotColor: 'bg-red-500',
    lightBg: 'bg-red-950/40',
    hex: '#DC2626',
  },
  2: {
    level: 2,
    name: 'Emergent',
    shortName: 'Emergent',
    description: 'High risk situation, confused/lethargic/disoriented, or severe pain/distress.',
    bgClass: 'bg-orange-600',
    textClass: 'text-orange-400',
    borderClass: 'border-orange-600',
    badgeBg: 'bg-orange-600',
    badgeText: 'text-white',
    badgeBorder: 'border-orange-700',
    dotColor: 'bg-orange-500',
    lightBg: 'bg-orange-950/40',
    hex: '#EA580C',
  },
  3: {
    level: 3,
    name: 'Urgent',
    shortName: 'Urgent',
    description: 'Normal vitals, requires multiple hospital resources.',
    bgClass: 'bg-amber-600',
    textClass: 'text-amber-400',
    borderClass: 'border-amber-600',
    badgeBg: 'bg-amber-600',
    badgeText: 'text-white',
    badgeBorder: 'border-amber-700',
    dotColor: 'bg-amber-500',
    lightBg: 'bg-amber-950/40',
    hex: '#D97706',
  },
  4: {
    level: 4,
    name: 'Less Urgent',
    shortName: 'Less Urgent',
    description: 'Requires one diagnostic or therapeutic resource.',
    bgClass: 'bg-green-600',
    textClass: 'text-green-400',
    borderClass: 'border-green-600',
    badgeBg: 'bg-green-600',
    badgeText: 'text-white',
    badgeBorder: 'border-green-700',
    dotColor: 'bg-green-500',
    lightBg: 'bg-green-950/40',
    hex: '#16A34A',
  },
  5: {
    level: 5,
    name: 'Non-Urgent',
    shortName: 'Non-Urgent',
    description: 'No resources required (e.g. medication prescription only).',
    bgClass: 'bg-blue-600',
    textClass: 'text-blue-400',
    borderClass: 'border-blue-600',
    badgeBg: 'bg-blue-600',
    badgeText: 'text-white',
    badgeBorder: 'border-blue-700',
    dotColor: 'bg-blue-500',
    lightBg: 'bg-blue-950/40',
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
      bgClass: 'bg-slate-700',
      textClass: 'text-slate-400',
      borderClass: 'border-slate-700',
      badgeBg: 'bg-slate-800',
      badgeText: 'text-slate-300',
      badgeBorder: 'border-slate-700',
      dotColor: 'bg-slate-500',
      lightBg: 'bg-slate-900',
      hex: '#64748B',
    };
  }
  return ACUITY_CONFIG[level];
}
