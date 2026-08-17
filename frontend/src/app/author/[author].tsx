import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { router, useLocalSearchParams, useNavigation } from 'expo-router';
import { Linking, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SymbolView } from 'expo-symbols';

import { apiClient } from '@/api/client';
import { searchBooksByAuthor, getAuthorAppearsIn } from '@/api/books';
import { getAuthorPhoto } from '@/api/author-photo';
import { getAuthorProfile, type AuthorRelatedItem } from '@/api/author-profile';
import type { BookAppearsInList } from '@/api/types';
import { BookCover } from '@/components/book-cover';
import { ClampedText } from '@/components/clamped-text';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { LibraryCoverWidth, MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

const EDITORIAL_BASES: Record<string, string> = {
  anagrama: 'https://www.anagrama-ed.es',
  penguin: 'https://www.penguinlibros.com',
  blackie: 'https://blackiebooks.org',
  transito: 'https://editorialtransito.es',
  asteroide: 'https://librosdelasteroide.com',
};

const EDITORIAL_LABELS: Record<string, string> = {
  anagrama: 'Anagrama',
  penguin: 'Penguin Books',
  blackie: 'Blackie Books',
  transito: 'Tránsito',
  asteroide: 'Libros del Asteroide',
};

const thumbUrl = (url: string | null | undefined): string | null =>
  url?.includes('penguinlibros.com')
    ? `${apiClient.BASE_URL}/thumb?url=${encodeURIComponent(url)}`
    : (url ?? null);

export default function AuthorScreen() {
  const params = useLocalSearchParams<{ author: string; authorBiblioteca?: string }>();
  const author = params.author ?? '';
  const authorBiblioteca = params.authorBiblioteca ?? author;
  const theme = useTheme();
  const navigation = useNavigation();

  const { data: books } = useQuery({
    queryKey: ['book-author', authorBiblioteca],
    queryFn: () => searchBooksByAuthor(authorBiblioteca),
    enabled: Boolean(authorBiblioteca),
  });

  const { data: photo } = useQuery({
    queryKey: ['author-photo', author],
    queryFn: () => getAuthorPhoto(author),
    enabled: Boolean(author),
    staleTime: 24 * 60 * 60 * 1000,
  });

  const { data: profile } = useQuery({
    queryKey: ['author-profile', author],
    queryFn: () => getAuthorProfile(author),
    enabled: Boolean(author),
  });

  const { data: appearsIn } = useQuery({
    queryKey: ['author-appears-in', author],
    queryFn: () => getAuthorAppearsIn(author),
    enabled: Boolean(author),
  });
  const appearsInLists = (appearsIn?.lists ?? []).filter(
    (l) => l.titulo != null && l.titulo.length > 0,
  );

  useEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <View style={styles.headerActions}>
          <Pressable hitSlop={8} onPress={() => {}}>
            <View style={styles.dots}>
              <View style={[styles.dot, { backgroundColor: '#000000' }]} />
              <View style={[styles.dot, { backgroundColor: '#000000' }]} />
              <View style={[styles.dot, { backgroundColor: '#000000' }]} />
            </View>
          </Pressable>
        </View>
      ),
    });
  }, [navigation]);

  const profileFound = profile?.found;
  const photoSourceValue = profileFound ? thumbUrl(profile.image_url) : photo?.photo_url ?? null;
  const photoSource = photoSourceValue ? { uri: photoSourceValue } : null;

  const firstBook = books?.[0];
  const restBooks = firstBook ? books.slice(1) : books ?? [];

  return (
    <ScrollView
      style={styles.screen}
      contentInsetAdjustmentBehavior="never"
      contentContainerStyle={styles.contentContainer}>
      <View style={styles.container}>
        <View style={styles.photoWrap}>
          <Image
            source={photoSource}
            style={styles.photo}
            contentFit="cover"
            contentPosition="top"
            transition={150}
          />
          <LinearGradient
            colors={['transparent', 'rgba(0,0,0,0.4)']}
            style={styles.photoGradient}
          />
          <View style={styles.nameOverlay} pointerEvents="none">
            {profileFound && profile.editorial ? (
              <View style={styles.verifiedChip}>
                <ThemedText type="small" style={styles.verifiedChipText}>
                  Información de {EDITORIAL_LABELS[profile.editorial] ?? profile.editorial}
                </ThemedText>
              </View>
            ) : null}
            <ThemedText style={styles.nameText} numberOfLines={2}>
              {author}
            </ThemedText>
          </View>
        </View>

        {firstBook ? (
          <View style={styles.startSection}>
            <Pressable
              onPress={() => router.push({ pathname: '/book/[id]', params: { id: String(firstBook.id) } })}
              style={({ pressed }) => [styles.startCard, pressed && { opacity: 0.7 }]}>
              <View style={styles.startCover}>
                {firstBook.thumbnail ? (
                  <Image
                    source={{ uri: firstBook.thumbnail }}
                    style={styles.startCoverImg}
                    contentFit="cover"
                    transition={150}
                  />
                ) : (
                  <ThemedText
                    type="small"
                    themeColor="textSecondary"
                    numberOfLines={3}
                    style={styles.startPlaceholder}>
                    {firstBook.title}
                  </ThemedText>
                )}
              </View>
              <View style={styles.startInfo}>
                <ThemedText type="small" themeColor="textTertiary" style={styles.startLabel}>
                  EMPIEZA POR
                </ThemedText>
                <ThemedText style={styles.startTitle} numberOfLines={2}>
                  {firstBook.title}
                </ThemedText>
              </View>
            </Pressable>
          </View>
        ) : null}

        <View style={styles.section}>
          <ThemedText style={styles.sectionTitle}>Libros</ThemedText>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.shelfContent}>
            {restBooks.map((b) => (
              <BookCover key={b.id} book={b} width={LibraryCoverWidth} />
            ))}
          </ScrollView>
        </View>

        {appearsInLists.length > 0 ? (
          <View style={styles.section}>
            <ThemedText style={styles.sectionTitle}>Aparece en</ThemedText>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.appearsShelf}>
              {appearsInLists.map((l) => (
                <AppearsInCard key={l.list_id} item={l} />
              ))}
            </ScrollView>
          </View>
        ) : null}

        {profileFound && profile.extra?.length ? (
          <View style={styles.section}>
            <ThemedText style={styles.sectionTitle}>Contenido relacionado</ThemedText>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.extraShelf}>
              {profile.extra.map((item) => (
                <ExtraItem
                  key={item.url ?? item.titulo}
                  item={item}
                  theme={theme}
                  baseUrl={profile.editorial ? EDITORIAL_BASES[profile.editorial] : undefined}
                />
              ))}
            </ScrollView>
          </View>
        ) : null}

        {profileFound && profile.description ? (
          <View style={styles.section}>
            <ThemedText style={styles.sectionTitle}>Sobre {author}</ThemedText>
            <ClampedText text={profile.description.trim()} title={author} />
          </View>
        ) : null}
      </View>
    </ScrollView>
  );
}

function ExtraItem({
  item,
  theme,
  baseUrl,
}: {
  item: AuthorRelatedItem;
  theme: ReturnType<typeof useTheme>;
  baseUrl?: string;
}) {
  const open = () => {
    const url = item.url?.startsWith('http') ? item.url : `${baseUrl ?? ''}${item.url ?? ''}`;
    if (url && url.length > (baseUrl?.length ?? 0)) {
      Linking.openURL(url).catch(() => {});
    }
  };

  const meta = [item.tipo?.toUpperCase(), item.categoria].filter(Boolean).join(' · ');

  const thumb = item.thumbnail ? thumbUrl(item.thumbnail) : null;
  const isPenguin = item.thumbnail?.includes('penguinlibros.com') ?? false;

  return (
    <Pressable onPress={open} style={({ pressed }) => [styles.extraCard, pressed && { opacity: 0.7 }]}>
      {thumb ? (
        <Image
          source={{ uri: thumb }}
          style={styles.extraThumb}
          contentFit={isPenguin ? 'contain' : 'cover'}
          contentPosition="center"
          transition={150}
        />
      ) : null}
      {meta ? (
        <ThemedText type="smallBold" style={[styles.extraTipo, { color: theme.textSecondary }]}>
          {meta}
        </ThemedText>
      ) : null}
      {item.titulo ? (
        <ThemedText type="smallBold" numberOfLines={2}>
          {item.titulo}
        </ThemedText>
      ) : null}
    </Pressable>
  );
}

function AppearsInCard({ item }: { item: BookAppearsInList }) {
  const open = () => {
    router.push({
      pathname: '/list/[slug]',
      params: { slug: item.slug },
    });
  };

  return (
    <Pressable onPress={open} style={({ pressed }) => [styles.appearsCard, pressed && { opacity: 0.7 }]}>
      <View style={styles.appearsThumbWrap}>
        {item.portada_url ? (
          <Image
            source={{ uri: item.portada_url }}
            style={styles.appearsThumb}
            contentFit="cover"
            transition={150}
          />
        ) : (
          <View style={styles.appearsThumbPlaceholder}>
            <ThemedText type="small" numberOfLines={2} ellipsizeMode="tail" style={styles.appearsThumbTitle}>
              {item.titulo}
            </ThemedText>
          </View>
        )}
      </View>
      <ThemedText type="smallBold" numberOfLines={2}>
        {item.titulo}
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary" numberOfLines={1} ellipsizeMode="tail">
        {item.autor ?? ''}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  contentContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
  },
  container: {
    width: '100%',
    maxWidth: MaxContentWidth,
    flexGrow: 1,
    gap: Spacing.five,
    paddingBottom: Spacing.five,
  },
  photoWrap: {
    width: '100%',
    aspectRatio: 1,
  },
  photo: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  photoGradient: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: 160,
  },
  nameOverlay: {
    position: 'absolute',
    left: Spacing.four,
    right: Spacing.four,
    bottom: Spacing.three,
    gap: Spacing.one,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    paddingVertical: 6,
  },
  dots: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
  },
  verifiedChip: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(0,0,0,0.55)',
    borderColor: 'rgba(255,255,255,0.5)',
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 999,
    paddingHorizontal: Spacing.one,
    paddingVertical: 0,
  },
  verifiedChipText: {
    color: '#FFFFFF',
    fontSize: 11,
    lineHeight: 16,
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  nameText: {
    color: '#FFFFFF',
    fontSize: 34,
    lineHeight: 40,
    fontWeight: '700',
    letterSpacing: -0.5,
    textShadowColor: 'rgba(0,0,0,0.5)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
  section: {
    gap: Spacing.two,
    paddingHorizontal: Spacing.four,
  },
  startSection: {
    paddingHorizontal: Spacing.four,
  },
  startCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
  },
  startCover: {
    width: LibraryCoverWidth,
    height: LibraryCoverWidth * 1.5,
    borderRadius: 10,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing.one,
  },
  startCoverImg: {
    width: '100%',
    height: '100%',
  },
  startPlaceholder: {
    textAlign: 'center',
  },
  startInfo: {
    flex: 1,
    gap: Spacing.half,
  },
  startLabel: {
    fontSize: 11,
    lineHeight: 15,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  startTitle: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: '400',
  },
  sectionTitle: {
    fontSize: 20,
    lineHeight: 26,
    fontWeight: '700',
  },
  shelfContent: {
    gap: Spacing.three,
  },
  extraShelf: {
    gap: Spacing.three,
  },
  appearsShelf: {
    gap: Spacing.three,
  },
  appearsCard: {
    width: 170,
    gap: 4,
  },
  appearsThumbWrap: {
    width: '100%',
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
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing.two,
  },
  appearsThumbTitle: {
    textAlign: 'center',
  },
  extraCard: {
    width: 170,
    gap: 4,
  },
  extraThumb: {
    width: '100%',
    aspectRatio: 16 / 9,
    borderRadius: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  extraTipo: {
    fontSize: 11,
  },
});