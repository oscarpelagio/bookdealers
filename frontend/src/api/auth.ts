import { apiClient } from '@/api/client';
import type {
  AuthTokens,
  AuthUser,
  MessageResponse,
  RegisterRequest,
  RegisterResponse,
} from '@/api/types';

export function login(email: string, password: string, deviceId?: string | null) {
  return apiClient.post<AuthTokens>('/auth/login', {
    email,
    password,
    ...(deviceId ? { device_id: deviceId } : {}),
  });
}

export function register(payload: RegisterRequest) {
  return apiClient.post<RegisterResponse>('/auth/register', payload);
}

export function refresh(refreshToken: string, deviceId?: string | null) {
  return apiClient.post<AuthTokens>('/auth/refresh', {
    refresh_token: refreshToken,
    ...(deviceId ? { device_id: deviceId } : {}),
  });
}

export function logout(refreshToken: string, logoutEverywhere = false) {
  return apiClient.post<MessageResponse>('/auth/logout', {
    refresh_token: refreshToken,
    logout_everywhere: logoutEverywhere,
  });
}

export function me() {
  return apiClient.get<AuthUser>('/auth/me');
}