import { apiClient } from '@/api/client';
import type { AvailabilityEntry, AvailabilitySource, Book, SearchParams, SearchSource, BookAppearsInResponse, CentralList } from '@/api/types';

export function searchBooks(
  source: SearchSource,
  params: SearchParams,
  catalog?: string,
) {
  if (source === 'z3950') {
    return apiClient.get<Book[]>('/search/z3950', {
      ...params,
      catalog: catalog ?? 'aladi',
    });
  }
  return apiClient.get<Book[]>(`/search/${source}`, { ...params });
}

export function searchBooksByAuthor(author: string, catalog: string = 'aladi') {
  return apiClient.get<Book[]>('/search/z3950/author', { author, catalog });
}

export function getAvailability(
  bookId: number,
  source: AvailabilitySource,
  catalog?: string,
) {
  const path =
    source === 'todostuslibros' ? '/availability/todostuslibros' : `/availability/${source}`;
  return apiClient.get<AvailabilityEntry[]>(path, {
    book_id: bookId,
    ...(source === 'todostuslibros'
      ? {}
      : { catalog: catalog ?? (source === 'z3950' ? 'aladi' : 'catalunya') }),
  });
}

export function getBook(bookId: number) {
  return apiClient.get<Book>(`/books/${bookId}`);
}

export function getBookAppearsIn(bookId: number) {
  return apiClient.get<BookAppearsInResponse>(`/books/${bookId}/appears-in`);
}

export function getAuthorAppearsIn(author: string) {
  return apiClient.get<BookAppearsInResponse>('/author-profile/appears-in', { author });
}

export function getCentralList(slug: string) {
  return apiClient.get<CentralList>(`/blog-articles/${slug}`);
}

export function getCentralListBooks(slug: string) {
  return apiClient.get<Book[]>(`/blog-articles/${slug}/books`);
}