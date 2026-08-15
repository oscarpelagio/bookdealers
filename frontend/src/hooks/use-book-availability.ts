import { useQueries, useQuery, type UseQueryResult } from '@tanstack/react-query';

import { getAvailability } from '@/api/books';
import { getMyCatalogs } from '@/api/favorites';
import type { AvailabilityEntry } from '@/api/types';

export type AvailabilityGroups = {
  libraries: AvailabilityEntry[];
  ebiblio: AvailabilityEntry[];
  bookshops: AvailabilityEntry[];
  hasLibraries: boolean;
  hasEbiblio: boolean;
  hasBookshops: boolean;
  isLoading: boolean;
  isError: boolean;
};

function flatten(results: UseQueryResult<AvailabilityEntry[]>[]): AvailabilityEntry[] {
  return results.flatMap((result) => result.data ?? []);
}

export function useBookAvailability(
  bookId: number | null | undefined,
  enabled: boolean,
): AvailabilityGroups {
  const catalogsQuery = useQuery({
    queryKey: ['me', 'catalogs'],
    queryFn: getMyCatalogs,
    enabled: enabled && bookId != null && !Number.isNaN(bookId),
  });

  const catalogs = catalogsQuery.data ?? [];
  const ready = enabled && bookId != null && !Number.isNaN(bookId) && catalogsQuery.isSuccess;

  const libraryCatalogs = catalogs.filter((c) => c.service === 'z3950');
  const ebiblioCatalogs = catalogs.filter((c) => c.service === 'ebiblio');
  const bookshopCatalogs = catalogs.filter((c) => c.service === 'todostuslibros');

  const libraryQueries = useQueries({
    queries: libraryCatalogs.map((catalog) => ({
      queryKey: ['availability', 'z3950', bookId, catalog.name],
      queryFn: () => getAvailability(bookId!, 'z3950', catalog.name),
      enabled: ready,
    })),
  });

  const ebiblioQueries = useQueries({
    queries: ebiblioCatalogs.map((catalog) => ({
      queryKey: ['availability', 'ebiblio', bookId, catalog.name],
      queryFn: () => getAvailability(bookId!, 'ebiblio', catalog.name),
      enabled: ready,
    })),
  });

  const bookshopQueries = useQueries({
    queries: [
      {
        queryKey: ['availability', 'todostuslibros', bookId],
        queryFn: () => getAvailability(bookId!, 'todostuslibros'),
        enabled: ready,
      },
    ],
  });

  const isLoading =
    catalogsQuery.isLoading ||
    libraryQueries.some((q) => q.isLoading) ||
    ebiblioQueries.some((q) => q.isLoading) ||
    bookshopQueries.some((q) => q.isLoading);

  const isError =
    catalogsQuery.isError ||
    libraryQueries.some((q) => q.isError) ||
    ebiblioQueries.some((q) => q.isError) ||
    bookshopQueries.some((q) => q.isError);

  return {
    libraries: flatten(libraryQueries),
    ebiblio: flatten(ebiblioQueries),
    bookshops: flatten(bookshopQueries),
    hasLibraries: libraryCatalogs.length > 0,
    hasEbiblio: ebiblioCatalogs.length > 0,
    hasBookshops: true,
    isLoading,
    isError,
  };
}