import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import type { Book, BookBrief } from '@/api/types';
import { BookActionsMenu } from '@/components/book-actions-menu';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useCoverColor } from '@/hooks/use-cover-color';

type BookCardProps = {
  book: Book | BookBrief;
  /** Ancho fijo para listados horizontales (shelves). */
  width?: number;
  /** Sin fondo de tarjeta (para listas planas con dividers). */
  plain?: boolean;
  /** Callback al abrir el libro (antes de navegar). */
  onOpen?: (book: Book | BookBrief) => void;
  /** Color del título (por ejemplo, heredar el del encabezado). */
  titleColor?: string;
  /** Color del autor (por ejemplo, heredar el del encabezado). */
  authorColor?: string;
};

export function BookCard({
  book,
  width,
  plain = false,
  onOpen,
  titleColor,
  authorColor,
}: BookCardProps) {
  const router = useRouter();
  const coverUri = 'small_thumbnail' in book ? book.small_thumbnail ?? book.thumbnail : book.thumbnail;
  const coverColor = useCoverColor(coverUri);

  return (
    <View style={plain ? styles.plainRow : undefined}>
      <Pressable
        testID={`book-${book.id}`}
        onPress={() => {
          onOpen?.(book);
          router.push({
            pathname: '/book/[id]',
            params: { id: String(book.id), coverUri: coverUri ?? undefined, coverColor: coverColor ?? undefined },
          });
        }}
        style={({ pressed }) => [plain ? styles.grow : undefined, pressed && styles.pressed]}>
        <ThemedView
          type="backgroundElement"
          style={[styles.card, width ? { width } : null, plain && styles.plainCard]}>
          {coverUri ? (
            <Image source={{ uri: coverUri }} style={[styles.cover, plain && styles.plainCover]} contentFit="cover" />
          ) : (
            <ThemedView
              type="backgroundSelected"
              style={[styles.cover, styles.coverPlaceholder, plain && styles.plainCover]}>
              <ThemedText type="small" themeColor="textSecondary">
                📖
              </ThemedText>
            </ThemedView>
          )}
          <View style={styles.info}>
            <ThemedText
              type={plain ? 'small' : 'smallBold'}
              numberOfLines={2}
              style={[plain && styles.plainTitle, titleColor ? { color: titleColor } : null]}>
              {book.title}
            </ThemedText>
            <ThemedText
              type="small"
              themeColor={plain ? 'textTertiary' : 'textSecondary'}
              numberOfLines={1}
              style={[plain && styles.plainAuthor, authorColor ? { color: authorColor } : null]}>
              {book.author}
            </ThemedText>
          </View>
        </ThemedView>
      </Pressable>
      {plain ? <BookActionsMenu book={book} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    gap: Spacing.three,
    padding: Spacing.three,
    borderRadius: Spacing.three,
  },
  plainCard: {
    backgroundColor: 'transparent',
    paddingVertical: Spacing.two,
    paddingHorizontal: 0,
    borderRadius: 0,
    gap: Spacing.three,
  },
  plainRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  grow: {
    flex: 1,
  },
  plainCover: {
    width: 40,
    height: 60,
    borderRadius: 4,
  },
  plainTitle: {
    fontSize: 15,
    lineHeight: 19,
    fontWeight: 500,
  },
  plainAuthor: {
    fontSize: 13,
    lineHeight: 17,
    fontWeight: 400,
  },
  cover: {
    width: 64,
    height: 94,
    borderRadius: Spacing.two,
  },
  coverPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  info: {
    flex: 1,
    gap: Spacing.half,
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.7,
  },
});