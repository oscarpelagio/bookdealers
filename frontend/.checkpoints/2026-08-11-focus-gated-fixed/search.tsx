import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigation } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { useEffect, useState } from 'react';
import { Platform, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { searchBooks } from '@/api/books';
import {
  clearSearchHistory,
  getMyCatalogs,
  getRecentSearches,
  recordSearchClick,
} from '@/api/favorites';
import type { BookBrief, Catalog } from '@/api/types';
import { BookCard } from '@/components/book-card';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { useAuth } from '@/lib/auth-context';

export default function SearchScreen() {
  const theme = useTheme();
  const navigation = useNavigation();
  const queryClient = useQueryClient();
  const { status: authStatus } = useAuth();
  const [text, setText] = useState('');
  const [query, setQuery] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (Platform.OS !== 'ios') return;
    navigation.setOptions({
      headerSearchBarOptions: {
        placeholder: 'Buscar por título',
        autoCapitalize: 'none',
        autoCorrect: false,
        obscureBackground: false,
        hideNavigationBar: false,
        onChangeText: (event: { nativeEvent: { text: string } }) =>
          setText(event.nativeEvent.text),
        onSearchButtonPress: (event: { nativeEvent: { text: string } }) =>
          setQuery(event.nativeEvent.text.trim() || null),
        onFocus: () => setFocused(true),
        onBlur: () => setFocused(false),
        onCancelButtonPress: () => {
          setText('');
          setQuery(null);
          setFocused(false);
        },
      },
    });
  }, [navigation]);

  const catalogsQuery = useQuery({
    queryKey: ['me', 'catalogs'],
    queryFn: getMyCatalogs,
    enabled: authStatus === 'signedIn',
  });

  const showHistory = focused && !query;

  const recentQuery = useQuery({
    queryKey: ['me', 'search-history', 'recent'],
    queryFn: getRecentSearches,
    enabled: showHistory && authStatus === 'signedIn',
  });

  const recordClick = useMutation({
    mutationFn: (bookId: number) => recordSearchClick(bookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'search-history', 'recent'] });
    },
  });

  const clearHistory = useMutation({
    mutationFn: clearSearchHistory,
    onSuccess: () => {
      queryClient.setQueryData<BookBrief[]>(['me', 'search-history', 'recent'], []);
      queryClient.invalidateQueries({ queryKey: ['me', 'search-history', 'recent'] });
    },
  });

  const z3950 = (catalogsQuery.data ?? []).find(
    (c: Catalog) => c.service === 'z3950',
  );

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['search', 'z3950', query, z3950?.name],
    queryFn: () => searchBooks('z3950', { title: query! }, z3950?.name),
    enabled: !!query,
  });

  return (
    <View style={[styles.root, { backgroundColor: theme.background }]}>
      {Platform.OS !== 'ios' ? (
        <View style={[styles.searchBar, { backgroundColor: theme.backgroundElement }]}>
          <SymbolView
            name="magnifyingglass"
            size={18}
            tintColor={theme.textTertiary}
            weight="semibold"
          />
          <TextInput
            value={text}
            onChangeText={setText}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onSubmitEditing={() => setQuery(text.trim() || null)}
            placeholder="Buscar por título"
            placeholderTextColor={theme.textTertiary}
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="search"
            style={[styles.searchInput, { color: theme.text }]}
          />
        </View>
      ) : null}

      {query ? (
        <SearchResults
          data={data}
          isLoading={isLoading}
          isError={isError}
          error={error}
          query={query}
          onOpenBook={(bookId) => recordClick.mutate(bookId)}
        />
      ) : showHistory ? (
        <RecentSearches
          books={recentQuery.data ?? []}
          isLoading={recentQuery.isLoading}
          onOpenBook={(bookId) => recordClick.mutate(bookId)}
          onClear={clearHistory.mutate}
        />
      ) : null}
    </View>
  );
}

function SearchResults({
  data,
  isLoading,
  isError,
  error,
  query,
  onOpenBook,
}: {
  data: Awaited<ReturnType<typeof searchBooks>> | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  query: string | null;
  onOpenBook: (bookId: number) => void;
}) {
  if (isLoading) {
    return (
      <ThemedText type="small" themeColor="textSecondary" style={styles.message}>
        Buscando…
      </ThemedText>
    );
  }

  if (isError) {
    return (
      <ThemedText type="small" themeColor="textSecondary" style={styles.message}>
        {error instanceof Error ? error.message : 'Error al buscar'}
      </ThemedText>
    );
  }

  if ((data?.length ?? 0) === 0) {
    return (
      <ThemedText type="small" themeColor="textSecondary" style={styles.message}>
        Sin resultados para “{query}”.
      </ThemedText>
    );
  }

  return (
    <View style={styles.results}>
      {data?.map((book, index) => (
        <View key={book.id}>
          {index > 0 ? <View style={styles.divider} /> : null}
          <BookCard book={book} plain onOpen={() => onOpenBook(book.id)} />
        </View>
      ))}
    </View>
  );
}

function RecentSearches({
  books,
  isLoading,
  onOpenBook,
  onClear,
}: {
  books: BookBrief[];
  isLoading: boolean;
  onOpenBook: (bookId: number) => void;
  onClear: () => void;
}) {
  const theme = useTheme();

  if (isLoading) {
    return (
      <ThemedText type="small" themeColor="textSecondary" style={styles.message}>
        Cargando…
      </ThemedText>
    );
  }

  if (books.length === 0) {
    return (
      <View style={styles.emptyState}>
        <SymbolView
          name="magnifyingglass"
          size={64}
          tintColor={theme.textTertiary}
          weight="light"
        />
        <ThemedText style={styles.emptyTitle}>No hay búsquedas recientes</ThemedText>
        <ThemedText type="small" themeColor="textTertiary" style={styles.emptySubtitle}>
          Las búsquedas que hayas realizado recientemente aparecerán aquí
        </ThemedText>
      </View>
    );
  }

  return (
    <View style={styles.results}>
      <View style={styles.recentHeader}>
        <ThemedText style={styles.recentTitle}>Búsquedas recientes</ThemedText>
        <Pressable onPress={onClear} hitSlop={8}>
          <ThemedText type="small" style={styles.clearButton}>
            Borrar
          </ThemedText>
        </Pressable>
      </View>
      <View style={styles.headerDivider} />
      {books.map((book, index) => (
        <View key={book.id}>
          {index > 0 ? <View style={styles.divider} /> : null}
          <BookCard book={book} plain onOpen={() => onOpenBook(book.id)} />
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: Spacing.two,
    margin: Spacing.four,
    marginBottom: Spacing.two,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    paddingVertical: 4,
  },
  message: {
    padding: 16,
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingTop: 140,
    gap: 8,
    paddingHorizontal: 32,
  },
  emptyTitle: {
    fontSize: 20,
    lineHeight: 26,
    fontWeight: '700',
    textAlign: 'center',
    marginTop: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    lineHeight: 19,
    fontWeight: '400',
    textAlign: 'center',
    marginTop: 2,
  },
  results: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: Spacing.four,
  },
  recentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  recentTitle: {
    fontSize: 17,
    lineHeight: 21,
    fontWeight: '600',
  },
  clearButton: {
    color: '#FF3B30',
    fontWeight: '600',
  },
  headerDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
    marginVertical: 16,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
    marginLeft: 56,
  },
});
