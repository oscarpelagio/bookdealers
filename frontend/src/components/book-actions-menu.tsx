import { StyleSheet, View } from 'react-native';

import { useTheme } from '@/hooks/use-theme';

type BookActionsMenuProps = {
  book: { id: number; title: string; author: string };
  /** Color de los tres puntos (por defecto el del tema). */
  tintColor?: string;
};

export function BookActionsMenu({ tintColor }: BookActionsMenuProps) {
  const theme = useTheme();
  const dotColor = tintColor ?? theme.textTertiary;

  return (
    <View style={styles.dots}>
      <View style={[styles.dot, { backgroundColor: dotColor }]} />
      <View style={[styles.dot, { backgroundColor: dotColor }]} />
      <View style={[styles.dot, { backgroundColor: dotColor }]} />
    </View>
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
  },
});
