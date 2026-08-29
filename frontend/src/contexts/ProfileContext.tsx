import React, { createContext, useContext, useState, useEffect } from 'react';
import { CONFIG } from '../config';

interface ProfileContextState {
  hospitalProfileId: string;
  setHospitalProfileId: (id: string) => void;
}

const ProfileContext = createContext<ProfileContextState | undefined>(undefined);

export const ProfileProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [hospitalProfileId, setHospitalProfileIdState] = useState<string>(() => {
    return localStorage.getItem(CONFIG.PROFILE_STORAGE_KEY) || CONFIG.DEFAULT_PROFILE_ID;
  });

  const setHospitalProfileId = (id: string) => {
    setHospitalProfileIdState(id);
    localStorage.setItem(CONFIG.PROFILE_STORAGE_KEY, id);
  };

  useEffect(() => {
    localStorage.setItem(CONFIG.PROFILE_STORAGE_KEY, hospitalProfileId);
  }, [hospitalProfileId]);

  return (
    <ProfileContext.Provider value={{ hospitalProfileId, setHospitalProfileId }}>
      {children}
    </ProfileContext.Provider>
  );
};

export function useProfile(): ProfileContextState {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error('useProfile must be used within a ProfileProvider');
  }
  return context;
}
