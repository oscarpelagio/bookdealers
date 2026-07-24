import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

export const options = {
  scenarios: {
    ramp_users: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '30s', target: 5 },
        { duration: '1m', target: 10 },
        { duration: '1m', target: 20 },
        { duration: '30s', target: 0 }
      ],
      gracefulRampDown: '30s'
    }
  }
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const latency = new Trend('latency');
export const errorRate = new Rate('error_rate');

const libros_populares = [
  { title: 'Cien anos de soledad', author: 'Gabriel Garcia Marquez' },
  { title: 'El nombre de la rosa', author: 'Umberto Eco' },
  { title: 'La sombra del viento', author: 'Carlos Ruiz Zafon' },
  { title: 'Don Quijote de la Mancha', author: 'Miguel de Cervantes' },
  { title: '1984', author: 'George Orwell' },
  { title: 'Crimen y castigo', author: 'Fiodor Dostoievski' },
  { title: 'El gran Gatsby', author: 'F. Scott Fitzgerald' },
  { title: 'Orgullo y prejuicio', author: 'Jane Austen' }
];

const libros_aleatorios = [
  { title: 'Rayuela', author: 'Julio Cortazar' },
  { title: 'Ficciones', author: 'Jorge Luis Borges' },
  { title: 'El tunel', author: 'Ernesto Sabato' },
  { title: 'La ciudad y los perros', author: 'Mario Vargas Llosa' },
  { title: 'Pedro Paramo', author: 'Juan Rulfo' },
  { title: 'La metamorfosis', author: 'Franz Kafka' },
  { title: 'Ulises', author: 'James Joyce' },
  { title: 'La insoportable levedad del ser', author: 'Milan Kundera' },
  { title: 'El extranjero', author: 'Albert Camus' },
  { title: 'Ensayo sobre la ceguera', author: 'Jose Saramago' },
  { title: 'La casa de los espiritus', author: 'Isabel Allende' }
];

const searchProviders = ['google', 'openlibrary'];

const catalogs = {
  z3950: ['aladi', 'argus', 'cabib'],
  ebiblio: ['catalunya']
};

function record(res, endpoint) {
  const ok = check(res, { 'status is 2xx': (r) => r.status >= 200 && r.status < 300 });
  latency.add(res.timings.duration, { endpoint });
  errorRate.add(!ok, { endpoint });
}

function pickBook() {
  const source = Math.random() < 0.7 ? libros_populares : libros_aleatorios;
  return source[Math.floor(Math.random() * source.length)];
}

function buildQuery(book) {
  const params = [];
  if (book.title) params.push(`title=${encodeURIComponent(book.title)}`);
  if (book.author) params.push(`author=${encodeURIComponent(book.author)}`);
  return params.join('&');
}

function doSearch() {
  const provider = searchProviders[Math.floor(Math.random() * searchProviders.length)];
  const book = pickBook();
  const url = `${BASE_URL}/search/${provider}?${buildQuery(book)}`;
  const res = http.get(url, { tags: { endpoint: `search_${provider}` } });
  record(res, `search_${provider}`);

  let items = [];
  try {
    items = res.json();
  } catch (_) {
    items = [];
  }

  if (!items || items.length === 0 || !items[0].id) {
    return null;
  }

  return { id: items[0].id };
}

function doAvailability(bookId) {
  const zCatalog = catalogs.z3950[Math.floor(Math.random() * catalogs.z3950.length)];
  const ebCatalog = catalogs.ebiblio[0];

  const batch = http.batch([
    ['GET', `${BASE_URL}/availability/z3950?book_id=${bookId}&catalog=${zCatalog}`],
    ['GET', `${BASE_URL}/availability/ebiblio?book_id=${bookId}&catalog=${ebCatalog}`],
    ['GET', `${BASE_URL}/availability/todostuslibros?book_id=${bookId}`]
  ]);

  record(batch[0], 'availability_z3950');
  record(batch[1], 'availability_ebiblio');
  record(batch[2], 'availability_todostuslibros');
}

export default function () {
  const result = doSearch();
  if (result && result.id) {
    doAvailability(result.id);
  }

  sleep(1);
}
