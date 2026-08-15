import { MenuView } from '@expo/ui/community/menu';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { StyleSheet, View } from 'react-native';

import { updateReadingStatus } from '@/api/favorites';
import type { ReadingStatus } from '@/api/types';

type NowReadingMenuProps = {
  bookId: number;
};

export function NowReadingMenu({ bookId }: NowReadingMenuProps) {
  const queryClient = useQueryClient();

  const setStatus = useMutation({
    mutationFn: (status: ReadingStatus) => updateReadingStatus(bookId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me', 'home'] });
    },
  });

  return (
    <MenuView
      onPressAction={(event) => {
        const action = event.nativeEvent.event;
        if (action === 'wtr') setStatus.mutate('WANT_TO_READ');
        else if (action === 'read') setStatus.mutate('READ');
        else if (action === 'dnf') setStatus.mutate('DNF');
      }}
      actions={[
        { id: 'share', title: 'Compartir', image: 'square.and.arrow.up' },
        { id: 'wtr', title: 'Para leer', image: 'plus' },
        { id: 'collection', title: 'Añadir a la colección', image: 'text.badge.plus' },
        { id: 'read', title: 'Marcar como terminado', image: 'checkmark.circle' },
        {
          id: 'dnf',
          title: 'Marcar como abandonado',
          image: 'xmark.circle',
          attributes: { destructive: true },
        },
      ]}>
      <View style={styles.dots}>
        <View style={styles.dot} />
        <View style={styles.dot} />
        <View style={styles.dot} />
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
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#ffffff',
  },
});