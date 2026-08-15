import { apiClient } from '@/api/client';
import type { BookBrief, Catalog, Establishment, HomeResponse, LibrariesResponse, ReadingStatus, UserBook } from '@/api/types';

export function getMyCatalogs() {
  return apiClient.get<Catalog[]>('/me/catalogs');
}

export function addMyCatalog(catalogId: number) {
  return apiClient.post<Catalog>(`/me/catalogs/${catalogId}`);
}

export function removeMyCatalog(catalogId: number) {
  return apiClient.delete<void>(`/me/catalogs/${catalogId}`);
}

export function getMyFavorites(type?: 'library' | 'book_shop') {
  return apiClient.get<Establishment[]>('/me/favorites', type ? { type } : undefined);
}

export function getMyEstablishments(type?: 'library' | 'book_shop') {
  return apiClient.get<Establishment[]>('/me/establishments', type ? { type } : undefined);
}

export function addFavorite(establishmentId: number) {
  return apiClient.post<Establishment>(`/me/favorites/${establishmentId}`);
}

export function removeFavorite(establishmentId: number) {
  return apiClient.delete<void>(`/me/favorites/${establishmentId}`);
}

export function getMyHome() {
  return apiClient.get<HomeResponse>('/me/home');
}

export function getMyLibraries() {
  return apiClient.get<LibrariesResponse>('/me/libraries');
}

export function updateReadingStatus(bookId: number, status: ReadingStatus) {
  return apiClient.patch<UserBook>(`/library/me/${bookId}`, { status });
}

// ---------- Historial de búsquedas ----------

export function recordSearchClick(bookId: number) {
  return apiClient.post<void>(`/me/search-history/${bookId}`);
}

export function getRecentSearches() {
  return apiClient.get<BookBrief[]>('/me/search-history/recent');
}

export function clearSearchHistory() {
  return apiClient.delete<void>('/me/search-history');
}
