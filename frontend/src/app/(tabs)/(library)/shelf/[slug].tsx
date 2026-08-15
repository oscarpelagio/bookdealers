import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams, useNavigation } from 'expo-router';
import { useEffect } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';

import { getLibraryBooks } from '@/api/library';
import type { ReadingStatus } from '@/api/types';
import { BookCard } from '@/components/book-card';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { useAuth } from '@/lib/auth-context';

const SLUG_TO_STATUS: Record<string, ReadingStatus> = {
  reading: 'READING',
  'to-read': 'WANT_TO_READ',
  read: 'READ',
  abandoned: 'DNF',
};

const STATUS_LABEL: Record<ReadingStatus, string> = {
  READING: 'Leyendo',
  WANT_TO_READ: 'Por leer',
  READ: 'Leído',
  DNF: 'Abandonado',
};

export default function ShelfBooksScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const status = SLUG_TO_STATUS[slug];
  const theme = useTheme();
  const { status: authStatus } = useAuth();
  const navigation = useNavigation();

  useEffect(() => {
    navigation.setOptions({ title: STATUS_LABEL[status] ?? 'Estantería' });
  }, [navigation, status]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['library', 'me', status],
    queryFn: () => getLibraryBooks(status),
    enabled: authStatus === 'signedIn' && !!status,
  });

  return (
    <ThemedView style={styles.root}>
      <ScrollView
        style={styles.scrollView}
        contentInsetAdjustmentBehavior="automatic"
        contentInset={{ bottom: BottomTabInset + Spacing.three }}
        contentContainerStyle={styles.contentContainer}>
        <View style={styles.container}>
          {isLoading ? (
            <View style={styles.center}>
              <ActivityIndicator color={theme.text} />
            </View>
          ) : error ? (
            <ThemedText type="small" themeColor="textSecondary" selectable>
              No se pudo cargar esta estantería. Inténtalo de nuevo.
            </ThemedText>
          ) : (data?.length ?? 0) === 0 ? (
            <ThemedText type="small" themeColor="textSecondary">
              No hay libros aquí todavía.
            </ThemedText>
          ) : (
            <View style={styles.results}>
              {data?.map((ub, index) => (
                <View key={ub.id}>
                  {index > 0 ? <View style={styles.divider} /> : null}
                  <BookCard book={ub.book} plain />
                </View>
              ))}
            </View>
          )}
        </View>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  root: {
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
    paddingHorizontal: Spacing.four,
    paddingBottom: Spacing.five,
    paddingTop: Spacing.two,
  },
  center: {
    paddingTop: 80,
    alignItems: 'center',
  },
  results: {
    flex: 1,
    paddingVertical: 8,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
    marginLeft: 56,
  },
});