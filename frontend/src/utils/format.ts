export function formatPrice(value: number | null | undefined): string | null {
  if (value == null) return null;
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value);
}

export function isDarkColor(hex: string): boolean {
  const { r, g, b } = parseHex(hex);
  if (r == null) return false;
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance < 0.5;
}

export function darkenColor(hex: string, amount: number): string {
  const { r, g, b } = parseHex(hex);
  if (r == null) return hex;
  const scale = 1 - amount;
  const to = (v: number) =>
    Math.max(0, Math.round(v * scale))
      .toString(16)
      .padStart(2, '0');
  return `#${to(r)}${to(g)}${to(b)}`;
}

export function lightenColor(hex: string, amount: number): string {
  const { r, g, b } = parseHex(hex);
  if (r == null) return hex;
  const scale = 1 - amount;
  const to = (v: number) =>
    Math.min(255, Math.round(255 - (255 - v) * scale))
      .toString(16)
      .padStart(2, '0');
  return `#${to(r)}${to(g)}${to(b)}`;
}

function parseHex(hex: string): { r: number; g: number; b: number } {
  const m = hex.replace('#', '');
  const full = m.length === 3 ? m.split('').map((c) => c + c).join('') : m;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return { r: 0, g: 0, b: 0 };
  return { r, g, b };
}

export function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

export const STATUS_LABEL: Record<string, string> = {
  AVAILABLE: 'Disponible',
  AVAILABLE_IN_2_3_DAYS: 'Disponible en 2-3 días',
  BORROW: 'Prestado',
  LOST: 'Extraviado',
  LIB_USE_ONLY: 'Solo consulta',
  UNKNOWN: 'Estado desconocido',
};

export function statusPriority(status: string): number {
  switch (status) {
    case 'AVAILABLE':
      return 0;
    case 'AVAILABLE_IN_2_3_DAYS':
      return 1;
    case 'BORROW':
      return 2;
    default:
      return 3;
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case 'AVAILABLE':
      return '#2e7d32';
    case 'AVAILABLE_IN_2_3_DAYS':
      return '#2e7d32';
    case 'BORROW':
      return '#f57c00';
    case 'LOST':
      return '#c62828';
    default:
      return '#757575';
  }
}

const LANGUAGE_LABEL: Record<string, string> = {
  es: 'Castellano',
  spa: 'Castellano',
  en: 'Inglés',
  eng: 'Inglés',
  fr: 'Francés',
  fra: 'Francés',
  ca: 'Català',
  cat: 'Català',
  gl: 'Gallego',
  eu: 'Euskera',
  de: 'Alemán',
  deu: 'Alemán',
  it: 'Italiano',
  ita: 'Italiano',
  pt: 'Portugués',
  por: 'Portugués',
  nl: 'Neerlandés',
  ru: 'Ruso',
  ja: 'Japonés',
  zh: 'Chino',
};

export function formatLanguage(value: string | null | undefined): string | null {
  if (!value) return null;
  const code = value.trim().toLowerCase();
  const label = LANGUAGE_LABEL[code] ?? LANGUAGE_LABEL[code.slice(0, 2)];
  if (label) return label;
  return code.charAt(0).toUpperCase() + code.slice(1);
}