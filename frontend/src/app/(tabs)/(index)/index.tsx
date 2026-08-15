import { useQuery } from '@tanstack/react-query';
import { Link, router } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { Image } from 'expo-image';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { getMyHome } from '@/api/favorites';
import type { HomeShelf } from '@/api/types';
import { BookCover } from '@/components/book-cover';
import { NowReadingCard } from '@/components/now-reading-card';
import { ProgressiveBlurScreen } from '@/components/progressive-blur-screen';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing, LibraryCoverWidth } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { useCoverColor } from '@/hooks/use-cover-color';
import { formatPrice } from '@/utils/format';
import { FadeWrapper } from 'rn-fade-wrapper';

function chunk<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < items.length; i += size) {
    chunks.push(items.slice(i, i + size));
  }
  return chunks;
}

export default function HomeScreen() {
  const theme = useTheme();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['me', 'home'],
    queryFn: getMyHome,
  });

  const shelves = data?.shelves ?? [];

  return (
    <ProgressiveBlurScreen title="Inicio">
      {isLoading ? (
        <View style={styles.center}>
          <ActivityIndicator color={theme.text} />
        </View>
      ) : isError ? (
        <View style={styles.center}>
          <ThemedText type="small" themeColor="textSecondary">
            No se pudo cargar tu panel.
          </ThemedText>
        </View>
      ) : (
        shelves.map((shelf) => <ShelfSection key={shelf.key} shelf={shelf} />)
      )}
    </ProgressiveBlurScreen>
  );
}

function LibraryBookCard({ book }: { book: HomeShelf['books'][number] }) {
  const libraryName = book.establishment_name ?? '';
  const dotIndex = libraryName.indexOf('.');
  const libraryShort = dotIndex >= 0 ? libraryName.slice(dotIndex + 1) : libraryName;
  const coverColor = useCoverColor(book.thumbnail);

  return (
    <Link
      href={{
        pathname: '/book/[id]',
        params: { id: String(book.id), coverUri: book.thumbnail ?? undefined, coverColor: coverColor ?? undefined },
      }}
      asChild>
      <Pressable>
        {({ pressed }) => (
          <View style={[styles.card, pressed && styles.cardPressed]}>
            <ThemedView type="backgroundElement" style={styles.coverCard}>
              {book.thumbnail ? (
                <Image source={{ uri: book.thumbnail }} style={styles.cardCover} contentFit="cover" transition={150} />
              ) : (
                <ThemedView type="backgroundSelected" style={[styles.cardCover, styles.coverPlaceholder]}>
                  <ThemedText type="small" themeColor="textSecondary">
                    📖
                  </ThemedText>
                </ThemedView>
              )}
            </ThemedView>
            {libraryShort ? (
              <View style={styles.chip}>
                <ThemedText type="small" style={styles.chipText} numberOfLines={1}>
                  {libraryShort}
                </ThemedText>
              </View>
            ) : null}
          </View>
        )}
      </Pressable>
    </Link>
  );
}

function BookStackCard({ book }: { book: HomeShelf['books'][number] }) {
  const storeName = book.establishment_name;
  const price = formatPrice(book.price);
  const coverColor = useCoverColor(book.thumbnail);

  return (
    <Link
      href={{
        pathname: '/book/[id]',
        params: { id: String(book.id), coverUri: book.thumbnail ?? undefined, coverColor: coverColor ?? undefined },
      }}
      asChild>
      <Pressable>
        {({ pressed }) => (
          <View style={[styles.stackRow, pressed && styles.cardPressed]}>
            <ThemedView type="backgroundElement" style={styles.stackCoverCard}>
              {book.thumbnail ? (
                <Image source={{ uri: book.thumbnail }} style={styles.stackCover} contentFit="cover" transition={150} />
              ) : (
                <ThemedView type="backgroundSelected" style={[styles.stackCover, styles.coverPlaceholder]}>
                  <ThemedText type="small" themeColor="textSecondary">
                    📖
                  </ThemedText>
                </ThemedView>
              )}
            </ThemedView>
            <View style={styles.stackMeta}>
              <ThemedText numberOfLines={1} style={styles.stackTitle}>
                {book.title}
              </ThemedText>
              <ThemedText type="small" themeColor="textSecondary" numberOfLines={1} style={styles.stackAuthor}>
                {book.author}
              </ThemedText>
              {storeName ? (
                <ThemedText type="small" themeColor="textSecondary" numberOfLines={1} style={styles.stackStore}>
                  {storeName}
                </ThemedText>
              ) : null}
            </View>
            {price ? (
              <View style={styles.priceChip}>
                <ThemedText type="small" style={styles.priceChipText}>
                  {price}
                </ThemedText>
              </View>
            ) : null}
          </View>
        )}
      </Pressable>
    </Link>
  );
}

function ShelfSection({ shelf }: { shelf: HomeShelf }) {
  const theme = useTheme();

  if (shelf.books.length === 0) return null;

  const isLibraries = shelf.key === 'WTR_LIBRARIES';

  return (
    <View style={styles.section}>
      {isLibraries ? (
        <Pressable
          onPress={() => router.push('/libraries')}
          style={({ pressed }) => [styles.sectionTitleRow, pressed && styles.sectionTitlePressed]}
          hitSlop={8}>
          <ThemedText style={styles.sectionTitle}>{shelf.title}</ThemedText>
          <SymbolView
            name="chevron.right"
            size={16}
            tintColor={theme.textTertiary}
            weight="semibold"
          />
        </Pressable>
      ) : (
        <ThemedText style={styles.sectionTitle}>{shelf.title}</ThemedText>
      )}
      <FadeWrapper color={theme.background} orientation="horizontal" size={Spacing.four}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.shelfContent}
          nestedScrollEnabled>
          {shelf.key === 'WTR_BOOKSTORES'
            ? chunk(shelf.books, 4).map((group, index) => (
                <View key={`stack-${index}`} style={styles.stackColumn}>
                  {group.map((book, i) => (
                    <View key={book.id} style={styles.stackItem}>
                      <BookStackCard book={book} />
                      {i < group.length - 1 ? <View style={styles.stackDivider} /> : null}
                    </View>
                  ))}
                </View>
              ))
            : shelf.books.map((book) =>
                shelf.key === 'READING' ? (
                  <NowReadingCard key={book.id} book={book} />
                ) : shelf.key === 'WTR_LIBRARIES' ? (
                  <LibraryBookCard key={`${book.id}-${book.establishment_name}`} book={book} />
                ) : shelf.key === 'WTR_EBIBLIO' ? (
                  <BookCover key={book.id} book={book} width={LibraryCoverWidth * 0.8} showMeta={false} />
                ) : (
                  <BookCover key={book.id} book={book} />
                )
              )}
        </ScrollView>
      </FadeWrapper>
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
    gap: 8,
  },
  section: {
    gap: 12,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 20,
    lineHeight: 26,
    fontWeight: '700',
  },
  sectionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  sectionTitlePressed: {
    opacity: 0.5,
  },
  shelfContent: {
    gap: 14,
  },
  stackColumn: {
    width: 310,
  },
  stackItem: {
    gap: 0,
  },
  stackRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    paddingVertical: Spacing.two,
  },
  stackCoverCard: {
    borderRadius: 4,
  },
  stackCover: {
    width: 40,
    height: 60,
    borderRadius: 4,
  },
  stackMeta: {
    flex: 1,
    gap: 0,
  },
  stackTitle: {
    fontSize: 15,
    lineHeight: 19,
    fontWeight: '600',
  },
  stackAuthor: {
    fontSize: 13,
    lineHeight: 17,
  },
  stackDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
    marginLeft: 56,
  },
  stackStore: {
    fontSize: 12,
    lineHeight: 15,
  },
  priceChip: {
    borderWidth: 1,
    borderColor: '#000000',
    borderRadius: 999,
    paddingHorizontal: Spacing.one + 2,
    paddingVertical: 0,
    alignSelf: 'center',
  },
  priceChipText: {
    fontSize: 11,
    lineHeight: 13,
    fontWeight: '600',
  },
  card: {
    gap: Spacing.one,
    width: 112,
  },
  cardPressed: {
    opacity: 0.7,
  },
  coverCard: {
    borderRadius: Spacing.two,
  },
  cardCover: {
    aspectRatio: 2 / 3,
    width: 112,
    borderRadius: Spacing.two,
  },
  coverPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  chip: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: '#000000',
    borderRadius: 999,
    paddingHorizontal: Spacing.two,
    paddingVertical: 0,
    maxWidth: '100%',
    marginTop: Spacing.one,
  },
  chipText: {
    fontSize: 11,
    lineHeight: 12,
    fontWeight: '500',
    textTransform: 'uppercase',
  },
});