import { apiClient } from '@/api/client';
import type { ReadingStatus, Shelf, UserBook } from '@/api/types';

export function getShelves() {
  return apiClient.get<Shelf[]>('/shelves');
}

export function getLibraryBooks(status?: ReadingStatus) {
  return apiClient.get<UserBook[]>('/library/me', status ? { status } : undefined);
}
