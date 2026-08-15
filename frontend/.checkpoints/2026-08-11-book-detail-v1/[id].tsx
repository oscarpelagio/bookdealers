import { Image } from 'expo-image';
import { useLocalSearchParams, useNavigation } from 'expo-router';
import { useEffect } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';

import type { Book } from '@/api/types';
import { BookActionsMenu } from '@/components/book-actions-menu';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { formatPrice } from '@/utils/format';

type BookDetail = Book & { price?: number | null };

export default function BookDetailScreen() {
  const params = useLocalSearchParams<{ id: string; book?: string }>();
  const book: BookDetail | undefined = params.book
    ? (JSON.parse(params.book) as BookDetail)
    : undefined;

  const theme = useTheme();
  const navigation = useNavigation();

  useEffect(() => {
    navigation.setOptions({
      headerRight: () => (book ? <BookActionsMenu book={book} /> : null),
    });
  }, [navigation, book]);

  const price = formatPrice(book?.price);
  const year = book?.publisher_date ? String(book.publisher_date).slice(0, 4) : null;

  return (
    <ScrollView
      style={[styles.scrollView, { backgroundColor: theme.background }]}
      contentInsetAdjustmentBehavior="automatic"
      contentContainerStyle={styles.contentContainer}>
      <ThemedView style={styles.container}>
        <View style={styles.coverWrap}>
          {book?.thumbnail ? (
            <Image
              source={{ uri: book.thumbnail }}
              style={styles.cover}
              contentFit="cover"
              transition={150}
            />
          ) : (
            <ThemedView type="backgroundSelected" style={[styles.cover, styles.coverPlaceholder]}>
              <ThemedText type="subtitle" themeColor="textSecondary">
                📖
              </ThemedText>
            </ThemedView>
          )}
        </View>

        <ThemedText style={styles.title}>{book?.title ?? 'Libro'}</ThemedText>
        <ThemedText themeColor="textSecondary" style={styles.author}>
          {book?.author ?? ''}
        </ThemedText>

        <ThemedText type="small" themeColor="textSecondary" style={styles.meta}>
          {[book?.page_count ? `${book.page_count} págs.` : null, year, book?.publisher]
            .filter(Boolean)
            .join(' · ')}
        </ThemedText>

        <View style={styles.actions}>
          <Pressable style={[styles.button, { backgroundColor: theme.text }]}>
            <ThemedText type="smallBold" style={{ color: theme.background }}>
              Ver disponibilidad
            </ThemedText>
          </Pressable>
          {price ? (
            <View style={styles.priceChip}>
              <ThemedText type="small" style={styles.priceChipText}>
                {price}
              </ThemedText>
            </View>
          ) : null}
        </View>

        <View style={styles.divider} />

        {book?.description ? (
          <ThemedText type="small" themeColor="textSecondary" style={styles.description}>
            {book.description}
          </ThemedText>
        ) : null}
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
    width: '100%',
    maxWidth: MaxContentWidth,
    flexGrow: 1,
    gap: Spacing.three,
    paddingHorizontal: Spacing.four,
    paddingBottom: Spacing.five,
    paddingTop: Spacing.three,
  },
  coverWrap: {
    alignItems: 'center',
  },
  cover: {
    width: 190,
    height: 285,
    borderRadius: 12,
    ...Platform.select({
      ios: {
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.25,
        shadowRadius: 8,
      },
      android: {
        elevation: 6,
      },
    }),
  },
  coverPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    lineHeight: 30,
    fontWeight: '700',
    textAlign: 'center',
  },
  author: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: '400',
    textAlign: 'center',
  },
  meta: {
    textAlign: 'center',
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two,
    marginTop: Spacing.one,
  },
  button: {
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.three,
    borderRadius: Spacing.five,
  },
  priceChip: {
    borderWidth: 1,
    borderColor: '#000000',
    borderRadius: 999,
    paddingHorizontal: Spacing.one + 2,
    paddingVertical: 2,
  },
  priceChipText: {
    fontSize: 13,
    lineHeight: 16,
    fontWeight: '600',
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
    marginVertical: Spacing.two,
  },
  description: {
    lineHeight: 22,
  },
});
