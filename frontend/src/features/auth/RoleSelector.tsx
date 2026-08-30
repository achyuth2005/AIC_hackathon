import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Role } from '../../types/enums';
import { Button } from '../../components/ui/Button';
import { Shield, Stethoscope, UserCheck } from 'lucide-react';
import { useToast } from '../../components/ui/Toast';
import { useNavigate } from 'react-router-dom';

interface RoleSelectorProps {
  onSuccess?: () => void;
}

export const RoleSelector: React.FC<RoleSelectorProps> = ({ onSuccess }) => {
  const { login, isLoading } = useAuth();
  const [selectedRole, setSelectedRole] = useState<Role>('NURSE');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { error } = useToast();
  const navigate = useNavigate();

  const handleLogin = async (role: Role) => {
    setIsSubmitting(true);
    try {
      await login(role);
      if (onSuccess) {
        onSuccess();
      } else {
        if (role === 'NURSE') navigate('/queue');
        else if (role === 'DOCTOR') navigate('/doctor');
        else if (role === 'ADMIN') navigate('/admin');
      }
    } catch (err: unknown) {
      error(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const roles = [
    {
      id: 'NURSE' as Role,
      title: 'Triage Nurse',
      name: 'Nurse Priya Nair',
      idString: 'demo-nurse-01',
      desc: 'Guardian Queue scanning, fast vitals intake, 1-tap escalation & clinical overrides.',
      icon: <UserCheck className="w-6 h-6 text-indigo-600" />,
      color: 'hover:bg-white/80 bg-white/50 border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(0,0,0,0.02)]',
      activeBorder: 'border-indigo-300/60 bg-indigo-500/10 shadow-[inset_0_0_0_1px_rgba(99,102,241,0.3),0_4px_16px_rgba(99,102,241,0.08)]',
    },
    {
      id: 'DOCTOR' as Role,
      title: 'Physician / ED Doctor',
      name: 'Dr. Arjun Rao',
      idString: 'demo-doctor-01',
      desc: 'Identity-relative case reviews, vital trends, diagnostic tracking & pending actions.',
      icon: <Stethoscope className="w-6 h-6 text-emerald-600" />,
      color: 'hover:bg-white/80 bg-white/50 border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(0,0,0,0.02)]',
      activeBorder: 'border-emerald-300/60 bg-emerald-500/10 shadow-[inset_0_0_0_1px_rgba(16,185,129,0.3),0_4px_16px_rgba(16,185,129,0.08)]',
    },
    {
      id: 'ADMIN' as Role,
      title: 'ED Administrator / Lead',
      name: 'Admin Sana Sheikh',
      idString: 'demo-admin-01',
      desc: 'Retrospective de-escalation review, equity monitoring, surge simulation & demo control.',
      icon: <Shield className="w-6 h-6 text-violet-600" />,
      color: 'hover:bg-white/80 bg-white/50 border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8),0_2px_8px_rgba(0,0,0,0.02)]',
      activeBorder: 'border-violet-300/60 bg-violet-500/10 shadow-[inset_0_0_0_1px_rgba(139,92,246,0.3),0_4px_16px_rgba(139,92,246,0.08)]',
    },
  ];

  return (
    <div className="w-full space-y-5">
      <div className="bg-amber-500/15 border border-amber-300/40 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)] backdrop-blur-sm rounded-xl p-3 text-xs text-amber-900 flex items-center justify-between">
        <span className="font-medium">⚡ Demo shortcut — not a real login</span>
        <span className="text-amber-800/80">Tokens valid for 12 hours</span>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {roles.map((r) => {
          const isSelected = selectedRole === r.id;
          return (
            <button
              key={r.id}
              type="button"
              disabled={isLoading || isSubmitting}
              onClick={() => setSelectedRole(r.id)}
              className={`text-left p-4 rounded-2xl border transition-all duration-150 flex items-start gap-4 cursor-pointer outline-none backdrop-blur-md ${
                isSelected
                  ? r.activeBorder
                  : `${r.color}`
              }`}
            >
              <div className="p-2.5 rounded-xl bg-white/70 border border-white/80 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.8)] shrink-0">
                {r.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-slate-900">{r.title}</div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-700 font-mono shadow-[inset_0_0_0_1px_rgba(255,255,255,0.7)]">
                    {r.name}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">{r.desc}</p>
              </div>
            </button>
          );
        })}
      </div>

      <Button
        onClick={() => handleLogin(selectedRole)}
        isLoading={isLoading || isSubmitting}
        size="lg"
        className="w-full font-semibold"
      >
        Continue as {roles.find((r) => r.id === selectedRole)?.title}
      </Button>
    </div>
  );
};
