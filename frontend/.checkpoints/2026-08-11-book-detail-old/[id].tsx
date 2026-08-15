import { useQuery } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { useLocalSearchParams } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { getAvailability } from '@/api/books';
import type { AvailabilitySource, Book } from '@/api/types';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { statusColor, STATUS_LABEL } from '@/utils/format';

const SOURCES: { value: AvailabilitySource; label: string }[] = [
  { value: 'z3950', label: 'ALADI' },
  { value: 'ebiblio', label: 'eBiblio' },
];

export default function BookDetailScreen() {
  const params = useLocalSearchParams<{ id: string; book?: string }>();
  const bookId = Number(params.id);
  const book: Book | undefined = params.book ? JSON.parse(params.book) : undefined;

  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const [source, setSource] = useState<AvailabilitySource>('z3950');

  const { data: availability, isLoading, isError, error } = useQuery({
    queryKey: ['availability', bookId, source],
    queryFn: () => getAvailability(bookId, source),
    enabled: !Number.isNaN(bookId),
  });

  const contentPlatformStyle = Platform.select({
    android: {
      paddingTop: insets.top,
      paddingLeft: insets.left,
      paddingRight: insets.right,
      paddingBottom: insets.bottom + Spacing.five,
    },
    web: {
      paddingTop: Spacing.five,
      paddingBottom: Spacing.five,
    },
  });

  return (
    <ScrollView
      style={[styles.scrollView, { backgroundColor: theme.background }]}
      contentInset={{ top: insets.top, bottom: insets.bottom }}
      contentContainerStyle={[styles.contentContainer, contentPlatformStyle]}>
      <ThemedView style={styles.container}>
        <View style={styles.hero}>
          {book?.small_thumbnail || book?.thumbnail ? (
            <Image
              source={{ uri: (book?.small_thumbnail ?? book?.thumbnail) ?? undefined }}
              style={styles.cover}
              contentFit="cover"
            />
          ) : (
            <ThemedView type="backgroundSelected" style={[styles.cover, styles.coverPlaceholder]}>
              <ThemedText type="subtitle" themeColor="textSecondary">
                📖
              </ThemedText>
            </ThemedView>
          )}
          <View style={styles.heroInfo}>
            <ThemedText type="subtitle">{book?.title ?? 'Libro'}</ThemedText>
            <ThemedText themeColor="textSecondary">{book?.author ?? ''}</ThemedText>
            {book?.publisher ? (
              <ThemedText type="small" themeColor="textSecondary">
                {book.publisher}
                {book.publisher_date ? ` · ${book.publisher_date}` : ''}
              </ThemedText>
            ) : null}
            {book?.isbn ? (
              <ThemedText type="small" themeColor="textSecondary">
                ISBN {book.isbn}
              </ThemedText>
            ) : null}
            {book?.language ? (
              <ThemedText type="small" themeColor="textSecondary">
                Idioma: {book.language}
              </ThemedText>
            ) : null}
          </View>
        </View>

        {book?.description ? <ThemedText type="small">{book.description}</ThemedText> : null}

        <View style={styles.sourceTabs}>
          {SOURCES.map((option) => (
            <Pressable
              key={option.value}
              testID={`availability-tab-${option.value}`}
              onPress={() => setSource(option.value)}
              style={[
                styles.sourceTab,
                {
                  backgroundColor:
                    source === option.value ? theme.text : theme.backgroundElement,
                },
              ]}>
              <ThemedText
                type="smallBold"
                style={{ color: source === option.value ? theme.background : theme.textSecondary }}>
                {option.label}
              </ThemedText>
            </Pressable>
          ))}
        </View>

        {isLoading && (
          <ThemedText type="small" themeColor="textSecondary">
            Consultando disponibilidad…
          </ThemedText>
        )}
        {isError && (
          <ThemedText type="small" themeColor="textSecondary" style={styles.error}>
            {error instanceof Error ? error.message : 'Error al consultar disponibilidad'}
          </ThemedText>
        )}
        {!isLoading && !isError && (availability?.length ?? 0) === 0 && (
          <ThemedText type="small" themeColor="textSecondary" style={styles.error}>
            Sin copias disponibles en este catálogo.
          </ThemedText>
        )}

        {availability?.map((entry) => (
          <ThemedView
            key={`${entry.establishment_name}-${entry.book_language}`}
            type="backgroundElement"
            style={styles.entry}>
            <View style={styles.entryHeader}>
              <ThemedText type="smallBold" style={styles.entryName}>
                {entry.establishment_name}
              </ThemedText>
              <View style={[styles.badge, { backgroundColor: statusColor(entry.book_status) }]}>
                <ThemedText type="small" style={styles.badgeText}>
                  {STATUS_LABEL[entry.book_status] ?? entry.book_status}
                </ThemedText>
              </View>
            </View>
            {entry.establishment_city || entry.establishment_province ? (
              <ThemedText type="small" themeColor="textSecondary">
                {[entry.establishment_city, entry.establishment_province].filter(Boolean).join(', ')}
              </ThemedText>
            ) : null}
            {entry.book_language ? (
              <ThemedText type="small" themeColor="textSecondary">
                Idioma: {entry.book_language}
              </ThemedText>
            ) : null}
            {entry.queue != null && Number(entry.queue) > 0 ? (
              <ThemedText type="small" themeColor="textSecondary">
                Cola: {entry.queue} persona{Number(entry.queue) === 1 ? '' : 's'}
              </ThemedText>
            ) : null}
            {entry.link ? (
              <Pressable onPress={() => WebBrowser.openBrowserAsync(entry.link)}>
                <ThemedText type="linkPrimary">Ver en el catálogo</ThemedText>
              </Pressable>
            ) : null}
          </ThemedView>
        ))}
      </ThemedView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
  },
  contentContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
  },
  container: {
    maxWidth: MaxContentWidth,
    flexGrow: 1,
    gap: Spacing.three,
    paddingHorizontal: Spacing.four,
  },
  hero: {
    flexDirection: 'row',
    gap: Spacing.three,
    alignItems: 'flex-start',
  },
  cover: {
    width: 96,
    height: 144,
    borderRadius: Spacing.two,
  },
  coverPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroInfo: {
    flex: 1,
    gap: Spacing.one,
  },
  sourceTabs: {
    flexDirection: 'row',
    gap: Spacing.two,
    marginTop: Spacing.one,
  },
  sourceTab: {
    paddingVertical: Spacing.one,
    paddingHorizontal: Spacing.three,
    borderRadius: Spacing.five,
  },
  error: {
    paddingVertical: Spacing.two,
  },
  entry: {
    gap: Spacing.one,
    padding: Spacing.three,
    borderRadius: Spacing.three,
  },
  entryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
  },
  entryName: {
    flex: 1,
  },
  badge: {
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.half,
    borderRadius: Spacing.two,
  },
  badgeText: {
    color: '#ffffff',
    fontWeight: '700',
  },
});