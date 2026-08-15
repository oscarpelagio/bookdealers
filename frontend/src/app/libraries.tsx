import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  addFavorite,
  getMyEstablishments,
  getMyLibraries,
} from '@/api/favorites';
import type { Establishment } from '@/api/types';
import { BookCover } from '@/components/book-cover';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { LibraryCoverWidth, MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type LibraryGroup = {
  title: string | null;
  items: Establishment[];
};

function splitName(name: string): { title: string; subtitle: string | null } {
  const dotIndex = name.indexOf('.');
  if (dotIndex >= 0) {
    return { title: name.slice(dotIndex + 1), subtitle: name.slice(0, dotIndex) };
  }
  return { title: name, subtitle: null };
}

function groupLibraries(libraries: Establishment[]): LibraryGroup[] {
  const byTitle = new Map<string, Establishment[]>();
  const standalone: Establishment[] = [];

  for (const lib of libraries) {
    const { subtitle } = splitName(lib.name ?? '');
    if (subtitle) {
      byTitle.set(subtitle, [...(byTitle.get(subtitle) ?? []), lib]);
    } else {
      standalone.push(lib);
    }
  }

  const groups: LibraryGroup[] = [];
  for (const [title, items] of byTitle) {
    items.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
    groups.push({ title, items });
  }
  groups.sort((a, b) => (a.title ?? '').localeCompare(b.title ?? ''));

  standalone.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
  for (const lib of standalone) {
    groups.push({ title: null, items: [lib] });
  }

  return groups;
}

export default function LibrariesScreen() {
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['me', 'libraries'],
    queryFn: getMyLibraries,
  });

  const shelves = data?.shelves ?? [];

  return (
    <View style={[styles.root, { backgroundColor: theme.background }]}>
      <Stack.Screen
        options={{
          headerRight: () => (
            <Pressable
              onPress={() => setShowAdd(true)}
              hitSlop={8}
              style={({ pressed }) => pressed && styles.headerButtonPressed}>
              <SymbolView name="plus" size={22} tintColor={theme.text} weight="semibold" />
            </Pressable>
          ),
        }}
      />
      <ScrollView
        style={styles.scrollView}
        contentInset={{ top: insets.top, bottom: insets.bottom }}
        contentContainerStyle={styles.contentContainer}>
        <ThemedView style={styles.container}>
          {isLoading ? (
            <ThemedText type="small" themeColor="textSecondary">
              Cargando tus bibliotecas…
            </ThemedText>
          ) : isError ? (
            <ThemedText type="small" themeColor="textSecondary">
              No se pudieron cargar tus bibliotecas.
            </ThemedText>
          ) : shelves.length === 0 ? (
            <ThemedText type="small" themeColor="textSecondary">
              Aún no tienes bibliotecas favoritas.
            </ThemedText>
          ) : (
            shelves.map((shelf) => {
              const { title, subtitle } = splitName(shelf.establishment.name ?? '');

              return (
                <View key={shelf.establishment.id} style={styles.section}>
                  <View style={styles.sectionTitleGroup}>
                    <ThemedText style={styles.sectionTitle} numberOfLines={1}>
                      {title}
                    </ThemedText>
                    {subtitle ? (
                      <ThemedText type="small" themeColor="textSecondary" numberOfLines={1} style={styles.sectionSubtitle}>
                        {subtitle}
                      </ThemedText>
                    ) : null}
                  </View>
                  {shelf.books.length === 0 ? (
                    <ThemedText type="small" themeColor="textSecondary">
                      Sin libros disponibles.
                    </ThemedText>
                  ) : (
                    <ScrollView
                      horizontal
                      showsHorizontalScrollIndicator={false}
                      contentContainerStyle={styles.shelfContent}>
                      {shelf.books.map((book) => (
                        <BookCover key={book.id} book={book} width={LibraryCoverWidth} showMeta={false} />
                      ))}
                    </ScrollView>
                  )}
                </View>
              );
            })
          )}
        </ThemedView>
      </ScrollView>

      <AddLibrarySheet
        visible={showAdd}
        onClose={() => setShowAdd(false)}
      />
    </View>
  );
}

function AddLibrarySheet({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();

  const { data: libraries = [] } = useQuery({
    queryKey: ['me', 'establishments', 'library'],
    queryFn: () => getMyEstablishments('library'),
    enabled: visible,
  });

  const addFav = useMutation({
    mutationFn: (id: number) => addFavorite(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'libraries'] });
      queryClient.invalidateQueries({ queryKey: ['me', 'home'] });
      queryClient.invalidateQueries({ queryKey: ['me', 'establishments', 'library'] });
    },
  });

  const groups = groupLibraries(libraries);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <Pressable style={styles.modalBackdrop} onPress={onClose} />
        <ThemedView
          style={[
            styles.sheet,
            { paddingBottom: insets.bottom + Spacing.three },
          ]}>
          <View style={[styles.sheetHandle, { backgroundColor: theme.backgroundSelected }]} />
          <ThemedText style={styles.sheetTitle}>Añadir biblioteca a favoritos</ThemedText>
          <ScrollView style={styles.sheetList} showsVerticalScrollIndicator={false}>
            {libraries.length === 0 ? (
              <ThemedText type="small" themeColor="textSecondary">
                No hay bibliotecas disponibles.
              </ThemedText>
            ) : (
              groups.map((group) => (
                <View key={group.title ?? group.items[0]?.name}>
                  {group.title ? (
                    <ThemedText type="smallBold" themeColor="textSecondary" style={styles.groupHeader}>
                      {group.title.toUpperCase()}
                    </ThemedText>
                  ) : null}
                  {group.items.map((lib) => (
                    <AddLibraryRow
                      key={lib.id}
                      library={lib}
                      onAdd={() => {
                        if (!lib.favorite) addFav.mutate(lib.id);
                      }}
                    />
                  ))}
                </View>
              ))
            )}
          </ScrollView>
          <Pressable onPress={onClose} style={styles.doneButton}>
            <ThemedText type="smallBold" themeColor="text">
              Hecho
            </ThemedText>
          </Pressable>
        </ThemedView>
      </View>
    </Modal>
  );
}

function AddLibraryRow({ library, onAdd }: { library: Establishment; onAdd: () => void }) {
  const theme = useTheme();
  const { title } = splitName(library.name ?? '');

  return (
    <Pressable
      onPress={onAdd}
      disabled={library.favorite}
      style={({ pressed }) => [
        styles.libraryRow,
        pressed && !library.favorite && styles.libraryRowPressed,
      ]}>
      <ThemedText
        type="small"
        themeColor={library.favorite ? 'textTertiary' : 'text'}
        numberOfLines={1}
        style={styles.libraryRowTitle}>
        {title}
      </ThemedText>
      {library.favorite ? (
        <SymbolView name="checkmark" size={18} tintColor={theme.textTertiary} weight="semibold" />
      ) : (
        <SymbolView name="plus" size={18} tintColor={theme.textSecondary} weight="semibold" />
      )}
    </Pressable>
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
    flexGrow: 1,
    maxWidth: MaxContentWidth,
    width: '100%',
    gap: Spacing.four,
    paddingHorizontal: Spacing.four,
    paddingBottom: Spacing.five,
  },
  headerButtonPressed: {
    opacity: 0.5,
  },
  section: {
    gap: Spacing.two,
  },
  sectionTitleGroup: {
    flex: 1,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: '500',
    letterSpacing: -0.3,
  },
  sectionSubtitle: {
    fontSize: 15,
    lineHeight: 20,
    fontWeight: '400',
  },
  shelfContent: {
    gap: Spacing.three,
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  modalBackdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  sheet: {
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.two,
    maxHeight: '85%',
  },
  sheetHandle: {
    alignSelf: 'center',
    width: 36,
    height: 5,
    borderRadius: 2.5,
  },
  sheetTitle: {
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
    paddingVertical: Spacing.three,
  },
  sheetList: {
    flexGrow: 0,
  },
  groupHeader: {
    fontSize: 13,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    paddingTop: Spacing.three,
    paddingBottom: Spacing.one,
  },
  libraryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
    paddingVertical: Spacing.two + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#E0E1E6',
  },
  libraryRowPressed: {
    opacity: 0.6,
  },
  libraryRowTitle: {
    flex: 1,
    fontSize: 15,
  },
  doneButton: {
    alignSelf: 'center',
    marginTop: Spacing.three,
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.four,
  },
});