import { Image } from 'expo-image';
import { Link } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { BookBrief } from '@/api/types';
import { NowReadingMenu } from '@/components/now-reading-menu';
import { useCoverColor } from '@/hooks/use-cover-color';

type NowReadingCardProps = {
  book: BookBrief;
};

export function NowReadingCard({ book }: NowReadingCardProps) {
  const coverColor = useCoverColor(book.thumbnail);
  return (
    <View testID={`now-reading-${book.id}`} style={styles.card}>
      <View style={styles.bgClip}>
        {book.thumbnail ? (
          <Image
            source={{ uri: book.thumbnail }}
            style={styles.cardBg}
            blurRadius={24}
            contentFit="cover"
          />
        ) : null}
        <View style={styles.overlayDark} />
        <View style={styles.overlayGradient} />
      </View>

      <Link
        href={{
          pathname: '/book/[id]',
          params: { id: String(book.id), coverUri: book.thumbnail ?? undefined, coverColor: coverColor ?? undefined },
        }}
        asChild>
        <Pressable style={styles.body}>
          <View style={styles.cover}>
            {book.thumbnail ? (
              <Image
                source={{ uri: book.thumbnail }}
                style={styles.coverImage}
                contentFit="cover"
              />
            ) : (
              <View style={styles.coverPlaceholder} />
            )}
          </View>

          <View style={styles.info}>
            <Text numberOfLines={2} style={styles.title}>
              {book.title}
            </Text>
            <Text numberOfLines={1} style={styles.subtitle}>
              {book.author}
            </Text>
          </View>
        </Pressable>
      </Link>

      <View style={styles.menu} pointerEvents="box-none">
        <NowReadingMenu bookId={book.id} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    position: 'relative',
    width: 300,
    borderRadius: 13,
    padding: 8,
  },
  bgClip: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    borderRadius: 13,
    overflow: 'hidden',
  },
  cardBg: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
  },
  overlayDark: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'rgba(0,0,0,0.55)',
  },
  overlayGradient: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'rgba(0,0,0,0.45)',
  },
  body: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingRight: 34,
  },
  cover: {
    width: 37,
    height: 55,
    borderRadius: 4,
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 4,
    elevation: 2,
  },
  coverImage: {
    width: '100%',
    height: '100%',
    borderRadius: 4,
  },
  coverPlaceholder: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  info: {
    flex: 1,
    minWidth: 0,
    justifyContent: 'center',
  },
  title: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '500',
    lineHeight: 17,
    marginBottom: 3,
  },
  subtitle: {
    color: 'rgba(255,255,255,0.65)',
    fontSize: 12,
    fontWeight: '400',
    marginBottom: 1,
  },
  menu: {
    position: 'absolute',
    top: 0,
    right: 12,
    bottom: 0,
    justifyContent: 'center',
  },
});