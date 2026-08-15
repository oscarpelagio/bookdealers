import { Image } from 'expo-image';
import { Link } from 'expo-router';
import { Platform, Pressable, StyleSheet, View } from 'react-native';

import type { Book, BookBrief } from '@/api/types';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useCoverColor } from '@/hooks/use-cover-color';

type BookCoverProps = {
  book: Book | BookBrief;
  /** Ancho de la portada (por defecto 112 px ≈ tarjeta de estante). */
  width?: number;
  /** Muestra título y autor bajo la portada (por defecto true). */
  showMeta?: boolean;
  /** Color del título bajo la portada (por defecto el del tema). */
  titleColor?: string;
  /** Sombra sutil bajo la portada. */
  shadow?: boolean;
};

export function BookCover({ book, width = 112, showMeta = true, titleColor, shadow = false }: BookCoverProps) {
  const coverUri = 'small_thumbnail' in book ? book.small_thumbnail ?? book.thumbnail : book.thumbnail;
  const coverColor = useCoverColor(coverUri);
  const coverHeight = width * 1.5;

  return (
    <Link
      href={{
        pathname: '/book/[id]',
        params: { id: String(book.id), coverUri: coverUri ?? undefined, coverColor: coverColor ?? undefined },
      }}
      asChild>
      <Pressable
        testID={`book-cover-${book.id}`}
        style={({ pressed }) => [
          styles.container,
          { width },
          pressed && styles.pressed,
        ]}>
        <ThemedView
          type="backgroundElement"
          style={[styles.card, { width, height: coverHeight }, shadow && styles.shadow]}>
          {coverUri ? (
            <Image
              source={{ uri: coverUri }}
              style={[styles.cover, { width, height: coverHeight }]}
              contentFit="cover"
              transition={150}
            />
          ) : (
            <View
              style={[styles.cover, styles.coverPlaceholder, { width, height: coverHeight }]}>
              <Image
                source={require('@/assets/images/fondo-cover.webp')}
                style={StyleSheet.absoluteFill}
                contentFit="cover"
              />
              <ThemedText
                type="small"
                numberOfLines={3}
                ellipsizeMode="tail"
                style={[
                  styles.placeholderAuthor,
                  {
                    top: coverHeight * 0.088,
                    right: width * 0.085,
                    width: width * 0.5,
                    fontSize: 14,
                    lineHeight: 14 * 1.08,
                  },
                ]}>
                {book.author}
              </ThemedText>
              <ThemedText
                type="small"
                numberOfLines={4}
                ellipsizeMode="tail"
                style={[
                  styles.placeholderTitle,
                  {
                    bottom: coverHeight * 0.135,
                    left: width * 0.07,
                    right: width * 0.055,
                    fontSize: 13,
                    lineHeight: 13 * 1.05,
                  },
                ]}>
                {book.title}
              </ThemedText>
            </View>
          )}
        </ThemedView>
        {showMeta ? (
          <View style={[styles.meta, { width }]}>
            <ThemedText
              type="small"
              numberOfLines={2}
              ellipsizeMode="tail"
              style={[styles.title, titleColor ? { color: titleColor } : null]}>
              {book.title}
            </ThemedText>
          </View>
        ) : null}
      </Pressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  container: {
    flexShrink: 0,
    overflow: 'hidden',
  },
  card: {
    borderRadius: Spacing.two,
  },
  shadow: {
    ...Platform.select({
      ios: {
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.15,
        shadowRadius: 3,
      },
      android: {
        elevation: 3,
      },
    }),
  },
  cover: {
    borderRadius: Spacing.two,
  },
  coverPlaceholder: {
    overflow: 'hidden',
  },
  placeholderTitle: {
    position: 'absolute',
    lineHeight: undefined,
    fontWeight: '700',
    letterSpacing: -0.045 * 1,
    textAlign: 'right',
    color: '#000',
  },
  placeholderAuthor: {
    position: 'absolute',
    lineHeight: undefined,
    fontWeight: '700',
    letterSpacing: -0.045 * 1,
    textAlign: 'right',
    color: '#000',
  },
  meta: {
    gap: 0,
    marginTop: Spacing.two,
  },
  title: {
    fontSize: 13,
    lineHeight: 16,
    fontWeight: '500',
  },
  pressed: {
    opacity: 0.7,
  },
});