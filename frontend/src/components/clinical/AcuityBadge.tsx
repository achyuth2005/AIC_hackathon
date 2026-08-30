import React from 'react';
import { getAcuityConfig } from '../../lib/acuity';
import { cn } from '../../lib/cn';
import { ShieldAlert, Zap } from 'lucide-react';

export interface AcuityBadgeProps {
  acuity: number | null | undefined;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'hero';
  showLabel?: boolean;
  isBypass?: boolean;
  className?: string;
}

export const AcuityBadge: React.FC<AcuityBadgeProps> = ({
  acuity,
  size = 'md',
  showLabel = true,
  isBypass = false,
  className,
}) => {
  const config = getAcuityConfig(acuity);

  const sizeClasses = {
    xs: 'px-2 py-0.5 text-[10px] gap-1 rounded-full',
    sm: 'px-2.5 py-0.5 text-xs font-semibold gap-1.5 rounded-full',
    md: 'px-3 py-1 text-xs font-bold gap-2 rounded-full',
    lg: 'px-3.5 py-1.5 text-sm font-extrabold gap-2 rounded-full',
    xl: 'px-4 py-2 text-base font-extrabold gap-2.5 rounded-full',
    hero: 'px-6 py-4 text-3xl font-black gap-4 rounded-3xl shadow-xl',
  };

  const ariaLabel = isBypass
    ? 'Emergency Bypass Active — ESI 1 Immediate Resuscitation'
    : `ESI ${config.level}, ${config.name}`;

  return (
    <span
      role="status"
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center justify-center font-mono border backdrop-blur-sm select-none transition-transform uppercase tracking-wider',
        config.badgeBg,
        config.badgeText,
        config.badgeBorder,
        sizeClasses[size],
        isBypass ? 'animate-pulse ring-2 ring-rose-400/50 glow-red border-rose-400/50' : '',
        className
      )}
    >
      {isBypass ? (
        <Zap className="w-4 h-4 text-rose-700 fill-rose-700 shrink-0" />
      ) : acuity === 1 ? (
        <ShieldAlert className="w-3.5 h-3.5 text-rose-700 shrink-0" />
      ) : null}

      <span className="font-black">
        {config.level > 0 ? `ESI ${config.level}` : 'UNASSIGNED'}
      </span>

      {showLabel && config.level > 0 && (
        <>
          <span className="opacity-50 text-[0.8em]">/</span>
          <span className="font-sans font-semibold tracking-normal text-[0.9em] normal-case">
            {isBypass ? 'BYPASS ACTIVE' : config.shortName}
          </span>
        </>
      )}
    </span>
  );
};
