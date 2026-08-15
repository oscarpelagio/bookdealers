export interface Book {
  id: number;
  title: string;
  author: string;
  author_biblioteca: string | null;
  publisher: string | null;
  publisher_date: string | null;
  description: string | null;
  isbn: string | null;
  page_count: number | null;
  print_type: string | null;
  categories: string | null;
  maturity_rating: string | null;
  small_thumbnail: string | null;
  thumbnail: string | null;
  language: string;
  preview_link: string | null;
  original_title: string | null;
  bib_id: string | null;
  normal_title: string;
  normal_author: string;
  normal_original_title: string | null;
}

/** Resumen de libro devuelto en la librería (BookBrief del backend). */
export interface BookBrief {
  id: number;
  title: string;
  author: string;
  thumbnail: string | null;
  page_count: number | null;
  language: string;
  establishment_name?: string | null;
  price?: number | null;
}

export type AvailabilityStatus =
  | 'AVAILABLE'
  | 'BORROW'
  | 'LOST'
  | 'LIB_USE_ONLY'
  | 'UNKNOWN';

export interface AvailabilityEntry {
  establishment_type: string;
  establishment_name: string;
  establishment_street: string | null;
  establishment_postal_code: string | null;
  establishment_city: string | null;
  establishment_province: string | null;
  lat: number | null;
  lon: number | null;
  catalog_id: number;
  book_id: number;
  book_language: string;
  book_status: AvailabilityStatus;
  queue: number | null;
  link: string;
}

export interface SearchParams {
  title?: string;
  author?: string;
}

export type SearchSource = 'google' | 'openlibrary' | 'z3950';

export type AvailabilitySource = 'z3950' | 'ebiblio' | 'todostuslibros';

// ---------- Blog La Central (Aparece en) ----------

export interface BookAppearsInList {
  article_id: number;
  slug: string;
  url: string;
  titulo: string;
  autor: string | null;
  fecha: string | null;
  portada_url: string | null;
  posicion: number;
}

export interface BookAppearsInResponse {
  book_id: number;
  total: number;
  lists: BookAppearsInList[];
}

export interface CentralList {
  article_id: number;
  slug: string;
  url: string;
  tipo: string | null;
  titulo: string;
  subtitulo: string | null;
  intro: string | null;
  autor: string | null;
  fecha: string | null;
  cuerpo: string | null;
  portada_url: string | null;
}

// ---------- Auth ----------

export interface AuthUser {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  roles: string[];
  is_email_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_token_expires_in: number;
  refresh_token_expires_in: number;
  expires_at: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string | null;
  device_id?: string | null;
}

export interface RegisterResponse {
  user: AuthUser;
  requires_email_verification: boolean;
  dev_verification_url: string | null;
  dev_reset_url: string | null;
}

export interface MessageResponse {
  message: string;
}

// ---------- Library / Shelves ----------

export type ReadingStatus = 'WANT_TO_READ' | 'READING' | 'READ' | 'DNF';

export interface Shelf {
  id: string;
  name: string;
  slug: string;
  kind: 'STATUS' | 'CUSTOM';
  is_default: boolean;
  is_private: boolean;
  position: number;
  description: string | null;
  book_count: number;
}

export interface UserBook {
  id: string;
  book_id: number;
  status: ReadingStatus;
  current_page: number | null;
  percent_read: number | null;
  started_at: string | null;
  finished_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  book: BookBrief;
}

// ---------- Favorites / Home ----------

export interface Catalog {
  id: number;
  service: string;
  name: string;
  url: string | null;
}

export interface Establishment {
  id: number;
  type: 'library' | 'book_shop' | 'ebiblio';
  name: string;
  street: string | null;
  postal_code: string | null;
  city: string | null;
  province: string | null;
  catalog_id: number;
  favorite: boolean;
}

export interface HomeShelf {
  key: string;
  title: string;
  books: BookBrief[];
}

export interface HomeResponse {
  shelves: HomeShelf[];
}

export interface LibraryShelf {
  establishment: Establishment;
  books: BookBrief[];
}

export interface LibrariesResponse {
  shelves: LibraryShelf[];
}