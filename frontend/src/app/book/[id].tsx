import { useQuery } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { useLocalSearchParams, useNavigation, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Platform, ScrollView, StyleSheet, View, Pressable } from 'react-native';

import { getBook, searchBooksByAuthor, getBookAppearsIn } from '@/api/books';
import type { Book, BookBrief } from '@/api/types';
import { BookActionsMenu } from '@/components/book-actions-menu';
import { BookCover } from '@/components/book-cover';
import { AvailabilitySheet } from '@/components/availability-sheet.ios';
import { ClampedText } from '@/components/clamped-text';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { LibraryCoverWidth, MaxContentWidth, Spacing } from '@/constants/theme';
import { useCoverColor } from '@/hooks/use-cover-color';
import { useTheme } from '@/hooks/use-theme';
import { darkenColor, isDarkColor, lightenColor } from '@/utils/format';

type BookDetail = Book & BookBrief;

function extractYear(value: string | null | undefined): string | null {
  if (!value) return null;
  const s = String(value).trim();
  if (/^\d{8}$/.test(s)) return s.slice(-4);
  const iso = s.match(/^(\d{4})-/);
  if (iso) return iso[1];
  const plain = s.match(/^(\d{4})$/);
  return plain ? plain[1] : null;
}

export default function BookDetailScreen() {
  const params = useLocalSearchParams<{
    id: string;
    book?: string;
    coverUri?: string;
    coverColor?: string;
  }>();
  const passedBook: BookDetail | undefined = params.book
    ? (JSON.parse(params.book) as BookDetail)
    : undefined;

  const theme = useTheme();
  const navigation = useNavigation();
  const router = useRouter();
  const [coverRatio, setCoverRatio] = useState<number | null>(null);
  const [availabilityOpen, setAvailabilityOpen] = useState(false);

  const needsFullBook =
    passedBook == null ||
    passedBook.publisher == null ||
    passedBook.publisher_date == null ||
    passedBook.description == null;

  const { data: fetchedBook } = useQuery({
    queryKey: ['book', params.id],
    queryFn: () => getBook(Number(params.id)),
    enabled: needsFullBook,
  });

  const book: BookDetail | undefined = fetchedBook ?? passedBook;

  const isKnownAuthor = book?.author != null && book.author !== 'Unknown';
  const authorSearchKey = book?.author_biblioteca ?? book?.author;
  const { data: moreByAuthor } = useQuery({
    queryKey: ['book-author', authorSearchKey],
    queryFn: () => searchBooksByAuthor(authorSearchKey!),
    enabled: Boolean(isKnownAuthor && authorSearchKey),
  });
  const otherBooks = (moreByAuthor ?? []).filter((b) => b.id !== Number(params.id));

  const coverUri = book?.thumbnail ?? book?.small_thumbnail ?? params.coverUri;
  const coverColor = useCoverColor(coverUri, params.coverColor);
  const year = extractYear(book?.publisher_date);

  const { data: appearsIn } = useQuery({
    queryKey: ['book-appears-in', params.id],
    queryFn: () => getBookAppearsIn(Number(params.id)),
  });
  const appearsInLists = (appearsIn?.lists ?? []).filter(
    (l) => l.titulo != null && l.titulo.length > 0,
  );

  const backgroundColor = coverColor ?? theme.background;
  const isDark = coverColor != null && isDarkColor(coverColor);
  const textColor = isDark ? '#FFFFFF' : theme.text;
  const derivedTextColor = isDark
    ? lightenColor(backgroundColor, 0.7)
    : darkenColor(backgroundColor, 0.5);

  useEffect(() => {
    navigation.setOptions({
      headerRight: () =>
        book ? <BookActionsMenu book={book} tintColor={textColor} /> : null,
    });
  }, [navigation, book, textColor]);

  return (
    <View style={styles.screenRoot}>
      <ScrollView
        style={[styles.scrollView, { backgroundColor }]}
        contentInsetAdjustmentBehavior="automatic"
        contentContainerStyle={styles.contentContainer}>
      <ThemedView style={[styles.container, { backgroundColor }]}>
        <View style={styles.coverWrap}>
          <View
            style={[
              styles.coverShadow,
              coverRatio ? { aspectRatio: coverRatio } : null,
            ]}>
            {coverUri ? (
              <Image
                source={{ uri: coverUri }}
                style={styles.cover}
                contentFit="cover"
                transition={150}
                onLoad={(e) => {
                  const { width, height } = e.source;
                  if (width > 0 && height > 0) setCoverRatio(width / height);
                }}
              />
            ) : (
              <View style={[styles.cover, styles.coverPlaceholder]}>
                <Image
                  source={require('@/assets/images/fondo-cover.webp')}
                  style={StyleSheet.absoluteFill}
                  contentFit="cover"
                />
                <ThemedText
                  type="small"
                  numberOfLines={3}
                  ellipsizeMode="tail"
                  style={styles.placeholderAuthor}>
                  {book?.author ?? ''}
                </ThemedText>
                <ThemedText
                  type="small"
                  numberOfLines={4}
                  ellipsizeMode="tail"
                  style={styles.placeholderTitle}>
                  {book?.title ?? 'Libro'}
                </ThemedText>
              </View>
            )}
          </View>
        </View>

        <View style={styles.titleBlock}>
          <ThemedText style={[styles.title, { color: textColor }]}>
            {book?.title ?? 'Libro'}
          </ThemedText>
          <Pressable
            disabled={!book?.author || book.author === 'Unknown'}
            hitSlop={8}
            onPress={() => {
              if (book?.author) {
                router.push({
                  pathname: '/author/[author]',
                  params: {
                    author: book.author,
                    authorBiblioteca: book.author_biblioteca ?? book.author,
                  },
                });
              }
            }}>
            <ThemedText style={[styles.author, { color: textColor }]}>
              {book?.author ?? ''}
            </ThemedText>
          </Pressable>

          <ThemedText type="small" style={[styles.meta, { color: derivedTextColor }]}>
            {[book?.page_count ? `${book.page_count} páginas` : null, year, book?.publisher]
              .filter(Boolean)
              .join(' · ')}
          </ThemedText>
        </View>

        <View style={styles.actions}>
          <Pressable
            style={[styles.button, { backgroundColor: isDark ? '#FFFFFF' : theme.text }]}
            onPress={() => setAvailabilityOpen(true)}>
            <ThemedText style={[styles.buttonLabel, { color: backgroundColor }]}>
              Disponibilidad
            </ThemedText>
          </Pressable>
        </View>

        {book?.description ? (
          <ClampedText
            text={book.description}
            title={book.title}
            backgroundColor={backgroundColor}
            textColor={derivedTextColor}
          />
        ) : null}

        {otherBooks.length > 0 ? (
          <View style={styles.moreSection}>
            <ThemedText style={[styles.moreTitle, { color: textColor }]}>
              Más de {book?.author ?? ''}
            </ThemedText>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.moreList}>
              {otherBooks.map((b) => (
                <BookCover
                  key={b.id}
                  book={b}
                  width={LibraryCoverWidth}
                  titleColor={derivedTextColor}
                  shadow
                />
              ))}
            </ScrollView>
          </View>
        ) : null}

        {appearsInLists.length > 0 ? (
          <View style={styles.appearsMore}>
            <ThemedText style={[styles.moreTitle, { color: textColor }]}>
              Aparece en
            </ThemedText>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.appearsList}>
              {appearsInLists.map((l) => (
                <Pressable
                  key={l.list_id}
                  style={styles.appearsCard}
                  onPress={() => {
                    router.push({
                      pathname: '/list/[slug]',
                      params: { slug: l.slug },
                    });
                  }}>
                  <View style={styles.appearsThumbWrap}>
                    {l.portada_url ? (
                      <Image
                        source={{ uri: l.portada_url }}
                        style={styles.appearsThumb}
                        contentFit="cover"
                        transition={120}
                      />
                    ) : (
                      <ThemedView
                        type="backgroundSelected"
                        style={[styles.appearsThumb, styles.appearsThumbPlaceholder]}>
                        <ThemedText
                          type="small"
                          numberOfLines={2}
                          ellipsizeMode="tail"
                          style={styles.appearsThumbTitle}>
                          {l.titulo}
                        </ThemedText>
                      </ThemedView>
                    )}
                  </View>
                  <ThemedText
                    style={[styles.appearsCardTitle, { color: textColor }]}
                    numberOfLines={2}
                    ellipsizeMode="tail">
                    {l.titulo}
                  </ThemedText>
                  <ThemedText
                    type="small"
                    style={[styles.appearsCardAuthor, { color: textColor }]}
                    numberOfLines={1}
                    ellipsizeMode="tail">
                    {l.autor ?? ''}
                  </ThemedText>
                </Pressable>
              ))}
            </ScrollView>
          </View>
        ) : null}

        <View style={[styles.descriptionDivider, { backgroundColor: textColor, opacity: 0.5 }]} />
      </ThemedView>
      </ScrollView>
      <AvailabilitySheet
        bookId={Number(params.id)}
        isPresented={availabilityOpen}
        onDismiss={() => setAvailabilityOpen(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screenRoot: {
    flex: 1,
  },
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
  coverShadow: {
    width: 220,
    aspectRatio: 0.72,
    borderRadius: 14,
    ...Platform.select({
      ios: {
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.4,
        shadowRadius: 16,
      },
      android: {
        elevation: 12,
      },
    }),
  },
  cover: {
    width: '100%',
    height: '100%',
    borderRadius: 14,
  },
  coverPlaceholder: {
    overflow: 'hidden',
  },
  placeholderTitle: {
    position: 'absolute',
    bottom: '13.5%',
    left: '7%',
    right: '5.5%',
    fontSize: 30,
    lineHeight: 30 * 1.05,
    fontWeight: '700',
    letterSpacing: -0.045 * 30,
    textAlign: 'right',
    color: '#000',
  },
  placeholderAuthor: {
    position: 'absolute',
    top: '8.8%',
    right: '8.5%',
    width: '50%',
    fontSize: 30,
    lineHeight: 30 * 1.08,
    fontWeight: '700',
    letterSpacing: -0.045 * 30,
    textAlign: 'right',
    color: '#000',
  },
  titleBlock: {
    gap: Spacing.one,
    marginTop: Spacing.three,
  },
  title: {
    fontSize: 24,
    lineHeight: 30,
    fontWeight: '700',
    textAlign: 'center',
  },
  author: {
    fontSize: 19,
    lineHeight: 25,
    fontWeight: '400',
    textAlign: 'center',
  },
  meta: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  actions: {
    alignItems: 'center',
  },
  button: {
    alignSelf: 'center',
    height: 48,
    paddingHorizontal: Spacing.four,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonLabel: {
    fontSize: 16,
    fontWeight: '700',
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
    marginVertical: Spacing.two,
  },
  descriptionDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
  },
  moreSection: {
    gap: Spacing.three,
    marginTop: Spacing.two,
  },
  appearsMore: {
    gap: Spacing.three,
    marginTop: Spacing.two,
  },
  appearsList: {
    gap: Spacing.three,
  },
  appearsCard: {
    width: 170,
    gap: Spacing.one,
  },
  appearsThumbWrap: {
    aspectRatio: 1,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: 'rgba(0,0,0,0.05)',
  },
  appearsThumb: {
    width: '100%',
    height: '100%',
  },
  appearsThumbPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing.two,
  },
  appearsThumbTitle: {
    textAlign: 'center',
  },
  appearsCardTitle: {
    fontSize: 15,
    lineHeight: 20,
    fontWeight: '600',
  },
  appearsCardAuthor: {
    fontSize: 13,
    lineHeight: 17,
    fontWeight: '400',
  },
  moreTitle: {
    fontSize: 19,
    lineHeight: 24,
    fontWeight: '700',
  },
  moreList: {
    gap: Spacing.three,
  },
});