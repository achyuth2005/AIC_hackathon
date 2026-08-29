import { http } from '../lib/http';
import { Role } from '../types/enums';
import { LoginResponse } from '../types/api';

export const authApi = {
  login: (role: Role) => http.post<LoginResponse>('/auth/login', { role }),
};
