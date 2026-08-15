import { apiClient } from '@/api/client';

export interface AuthorPhoto {
  author: string;
  photo_url: string | null;
  source: string | null;
  status: string;
}

export function getAuthorPhoto(author: string) {
  return apiClient.get<AuthorPhoto>('/author-photo', { author });
}