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
      icon: <UserCheck className="w-6 h-6 text-cyan-400" />,
      color: 'hover:border-cyan-500/60 focus:border-cyan-500 bg-cyan-950/20',
      activeBorder: 'border-cyan-500 bg-cyan-950/40 ring-1 ring-cyan-500',
    },
    {
      id: 'DOCTOR' as Role,
      title: 'Physician / ED Doctor',
      name: 'Dr. Arjun Rao',
      idString: 'demo-doctor-01',
      desc: 'Identity-relative case reviews, vital trends, diagnostic tracking & pending actions.',
      icon: <Stethoscope className="w-6 h-6 text-emerald-400" />,
      color: 'hover:border-emerald-500/60 focus:border-emerald-500 bg-emerald-950/20',
      activeBorder: 'border-emerald-500 bg-emerald-950/40 ring-1 ring-emerald-500',
    },
    {
      id: 'ADMIN' as Role,
      title: 'ED Administrator / Lead',
      name: 'Admin Sana Sheikh',
      idString: 'demo-admin-01',
      desc: 'Retrospective de-escalation review, equity monitoring, surge simulation & demo control.',
      icon: <Shield className="w-6 h-6 text-purple-400" />,
      color: 'hover:border-purple-500/60 focus:border-purple-500 bg-purple-950/20',
      activeBorder: 'border-purple-500 bg-purple-950/40 ring-1 ring-purple-500',
    },
  ];

  return (
    <div className="w-full space-y-5">
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3 text-xs text-slate-300 flex items-center justify-between">
        <span className="font-medium text-amber-300">⚡ Demo shortcut — not a real login</span>
        <span className="text-slate-400">Tokens valid for 12 hours</span>
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
              className={`text-left p-4 rounded-xl border transition-all duration-150 flex items-start gap-4 cursor-pointer outline-none ${
                isSelected
                  ? r.activeBorder
                  : `border-slate-800 bg-slate-900/60 ${r.color}`
              }`}
            >
              <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/50 shrink-0">
                {r.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-slate-100">{r.title}</div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                    {r.name}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{r.desc}</p>
              </div>
            </button>
          );
        })}
      </div>

      <Button
        onClick={() => handleLogin(selectedRole)}
        isLoading={isLoading || isSubmitting}
        size="lg"
        className="w-full font-semibold shadow-lg shadow-cyan-950/50"
      >
        Continue as {roles.find((r) => r.id === selectedRole)?.title}
      </Button>
    </div>
  );
};
