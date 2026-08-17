import { useQuery } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { useLocalSearchParams, useNavigation } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Linking, Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { getSourceList, getSourceListBooks } from '@/api/books';
import { BookCard } from '@/components/book-card';
import { ClampedText } from '@/components/clamped-text';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useCoverColor } from '@/hooks/use-cover-color';
import { useTheme } from '@/hooks/use-theme';
import { darkenColor, isDarkColor, lightenColor } from '@/utils/format';

export default function SourceListScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const theme = useTheme();
  const navigation = useNavigation();
  const [coverRatio, setCoverRatio] = useState<number | null>(null);

  const { data: list, isLoading: listLoading } = useQuery({
    queryKey: ['source-list', slug],
    queryFn: () => getSourceList(slug),
    enabled: Boolean(slug),
  });

  const { data: books, isLoading: booksLoading } = useQuery({
    queryKey: ['source-list-books', slug],
    queryFn: () => getSourceListBooks(slug),
    enabled: Boolean(slug),
    retry: 1,
  });

  useEffect(() => {
    navigation.setOptions({ title: '' });
  }, [navigation]);

  const coverUri = list?.portada_url;
  const coverColor = useCoverColor(coverUri);
  const backgroundColor = coverColor ?? theme.background;
  const isDark = coverColor != null && isDarkColor(coverColor);
  const textColor = isDark ? '#FFFFFF' : theme.text;
  const derivedTextColor = isDark
    ? lightenColor(backgroundColor, 0.7)
    : darkenColor(backgroundColor, 0.5);

  const meta = [
    list?.fecha,
    list?.tipo,
  ]
    .filter((v) => v != null && v.length > 0)
    .join(' · ');

  const text = list?.cuerpo ?? list?.intro ?? '';

  return (
    <View style={styles.screenRoot}>
      <ScrollView
        style={[styles.scrollView, { backgroundColor }]}
        contentInsetAdjustmentBehavior="automatic"
        contentInset={{ bottom: BottomTabInset + Spacing.three }}
        contentContainerStyle={styles.contentContainer}>
        <ThemedView style={[styles.container, { backgroundColor }]}>
          {listLoading ? (
            <View style={styles.center}>
              <ActivityIndicator color={theme.text} />
            </View>
          ) : list ? (
            <>
              {coverUri ? (
                <View style={styles.coverWrap}>
                  <View
                    style={[
                      styles.coverShadow,
                      coverRatio ? { aspectRatio: coverRatio } : null,
                    ]}>
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
                  </View>
                </View>
              ) : null}

              <View style={styles.titleBlock}>
                <ThemedText style={[styles.title, { color: textColor }]}>
                  {list.titulo}
                </ThemedText>
                {list.subtitulo ? (
                  <ThemedText style={[styles.subtitulo, { color: derivedTextColor }]}>
                    {list.subtitulo}
                  </ThemedText>
                ) : null}
                {list.autor ? (
                  <ThemedText style={[styles.listAuthor, { color: derivedTextColor }]}>
                    {list.autor}
                  </ThemedText>
                ) : null}
              </View>

              {meta.length > 0 ? (
                <ThemedText type="small" style={[styles.meta, { color: derivedTextColor }]}>
                  {meta}
                </ThemedText>
              ) : null}

              <View style={styles.actions}>
                <Pressable
                  style={[styles.button, { backgroundColor: isDark ? '#FFFFFF' : theme.text }]}
                  onPress={() => {
                    if (list.url) Linking.openURL(list.url).catch(() => {});
                  }}>
                  <ThemedText style={[styles.buttonLabel, { color: backgroundColor }]}>
                    La Central
                  </ThemedText>
                </Pressable>
              </View>

              {text.length > 0 ? (
                <ClampedText
                  text={text}
                  title={list.titulo}
                  backgroundColor={backgroundColor}
                  textColor={derivedTextColor}
                  maxLines={2}
                />
              ) : null}

              <View style={styles.divider} />

              <View style={styles.booksGroup}>
                {booksLoading ? (
                  <View style={styles.centerBlock}>
                    <ActivityIndicator color={theme.text} />
                  </View>
                ) : (books?.length ?? 0) === 0 ? (
                  <ThemedText type="small" themeColor="textSecondary">
                    Aún no se han podido resolver los libros de esta lista.
                  </ThemedText>
                ) : (
                  <View style={styles.results}>
                    {books?.map((book, index) => (
                      <View key={book.id}>
                        {index > 0 ? <View style={styles.itemDivider} /> : null}
                        <BookCard
                          book={book}
                          plain
                          titleColor={textColor}
                          authorColor={derivedTextColor}
                        />
                      </View>
                    ))}
                  </View>
                )}
              </View>
            </>
          ) : (
            <ThemedText type="small" themeColor="textSecondary">
              No se encontró esta lista.
            </ThemedText>
          )}
        </ThemedView>
      </ScrollView>
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
  center: {
    paddingTop: 80,
    alignItems: 'center',
  },
  centerBlock: {
    paddingVertical: Spacing.four,
    alignItems: 'center',
  },
  coverWrap: {
    alignItems: 'center',
  },
  coverShadow: {
    width: 320,
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
  titleBlock: {
    gap: Spacing.one,
  },
  title: {
    fontSize: 24,
    lineHeight: 30,
    fontWeight: '700',
    textAlign: 'center',
  },
  subtitulo: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: '500',
    textAlign: 'center',
  },
  listAuthor: {
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
    height: 52,
    paddingHorizontal: Spacing.five,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonLabel: {
    fontSize: 17,
    fontWeight: '700',
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
  },
  booksGroup: {
    gap: 0,
  },
  results: {
    paddingVertical: 0,
  },
  itemDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
    marginLeft: 56,
  },
});