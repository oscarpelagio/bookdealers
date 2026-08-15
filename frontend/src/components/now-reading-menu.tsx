import { StyleSheet, View } from 'react-native';

type NowReadingMenuProps = {
  bookId: number;
};

export function NowReadingMenu(_props: NowReadingMenuProps) {
  return (
    <View style={styles.dots}>
      <View style={styles.dot} />
      <View style={styles.dot} />
      <View style={styles.dot} />
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
    backgroundColor: '#ffffff',
  },
});