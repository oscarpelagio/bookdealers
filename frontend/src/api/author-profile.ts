import { apiClient } from '@/api/client';

export interface AuthorRelatedItem {
  tipo: string | null;
  titulo: string | null;
  url: string | null;
  fecha: string | null;
  descripcion: string | null;
  thumbnail: string | null;
  categoria: string | null;
}

export interface AuthorProfile {
  found: boolean;
  editorial: string | null;
  slug: string | null;
  name: string | null;
  description: string | null;
  image_url: string | null;
  extra: AuthorRelatedItem[] | null;
}

export function getAuthorProfile(author: string) {
  return apiClient.get<AuthorProfile>('/author-profile', { author });
}