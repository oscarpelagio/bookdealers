import { apiClient } from '@/api/client';

export interface AnagramaRelatedItem {
  tipo: string | null;
  titulo: string | null;
  url: string | null;
  fecha: string | null;
  descripcion: string | null;
  thumbnail: string | null;
}

export interface AuthorAnagrama {
  found: boolean;
  slug: string | null;
  name: string | null;
  description: string | null;
  image_url: string | null;
  extra: AnagramaRelatedItem[] | null;
}

export function getAuthorAnagrama(author: string) {
  return apiClient.get<AuthorAnagrama>('/author-anagrama', { author });
}