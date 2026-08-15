import { MenuView } from '@expo/ui/community/menu';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Share, StyleSheet, View } from 'react-native';

import { updateReadingStatus } from '@/api/favorites';
import type { Book, BookBrief, ReadingStatus } from '@/api/types';
import { useTheme } from '@/hooks/use-theme';

type BookActionsMenuProps = {
  book: Book | BookBrief;
  /** Color de los tres puntos (por defecto el del tema). */
  tintColor?: string;
};

export function BookActionsMenu({ book, tintColor }: BookActionsMenuProps) {
  const theme = useTheme();
  const queryClient = useQueryClient();
  const dotColor = tintColor ?? theme.text;

  const setStatus = useMutation({
    mutationFn: (status: ReadingStatus) => updateReadingStatus(book.id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'home'] });
    },
  });

  return (
    <MenuView
      onPressAction={(event) => {
        const action = event.nativeEvent.event;
        if (action === 'share') {
          Share.share({ message: `${book.title} — ${book.author}` });
        } else if (action === 'wtr') {
          setStatus.mutate('WANT_TO_READ');
        } else if (action === 'read') {
          setStatus.mutate('READ');
        }
      }}
      actions={[
        {
          id: 'primary',
          title: '',
          displayInline: true,
          subactions: [
            { id: 'share', title: 'Compartir', image: 'square.and.arrow.up' },
            { id: 'wtr', title: 'Para leer', image: 'plus' },
          ],
        },
        {
          id: 'secondary',
          title: '',
          displayInline: true,
          subactions: [
            { id: 'collection', title: 'Añadir a la colección', image: 'text.badge.plus' },
            { id: 'read', title: 'Marcar como terminado', image: 'checkmark.circle' },
          ],
        },
      ]}>
      <View style={styles.dots}>
        <View style={[styles.dot, { backgroundColor: dotColor }]} />
        <View style={[styles.dot, { backgroundColor: dotColor }]} />
        <View style={[styles.dot, { backgroundColor: dotColor }]} />
      </View>
    </MenuView>
  );
}

const styles = StyleSheet.create({
  dots: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    paddingVertical: 6,
    paddingHorizontal: 4,
  },
  dot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
  },
});