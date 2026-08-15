import { router } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { Pressable, StyleSheet, View } from 'react-native';

import type { ReadingStatus } from '@/api/types';
import { ProgressiveBlurScreen } from '@/components/progressive-blur-screen';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { useAuth } from '@/lib/auth-context';

const STATUS_ORDER: { status: ReadingStatus; label: string; slug: string; symbol: string }[] = [
  { status: 'READING', label: 'Leyendo', slug: 'reading', symbol: 'book' },
  { status: 'WANT_TO_READ', label: 'Por leer', slug: 'to-read', symbol: 'bookmark' },
  { status: 'READ', label: 'Leído', slug: 'read', symbol: 'checkmark.circle' },
  { status: 'DNF', label: 'Abandonado', slug: 'abandoned', symbol: 'xmark.circle' },
];

const Red = '#E0353D';

export default function LibraryScreen() {
  const theme = useTheme();
  const { status: authStatus } = useAuth();

  if (authStatus !== 'signedIn') {
    return (
      <ProgressiveBlurScreen title="Mi librería">
        <ThemedText type="small" themeColor="textSecondary" selectable>
          Inicia sesión para ver tus libros guardados.
        </ThemedText>
      </ProgressiveBlurScreen>
    );
  }

  return (
    <ProgressiveBlurScreen title="Mi librería">
      <View style={styles.list}>
        {STATUS_ORDER.map((row, index) => (
          <View key={row.status}>
            {index > 0 ? <View style={styles.divider} /> : null}
            <Pressable
              onPress={() =>
                router.push({
                  pathname: '/shelf/[slug]',
                  params: { slug: row.slug },
                })
              }
              style={({ pressed }) => pressed && styles.rowPressed}>
              <View style={styles.row}>
                <SymbolView name={row.symbol as never} size={26} tintColor={Red} weight="regular" />
                <ThemedText style={styles.rowLabel}>{row.label}</ThemedText>
                <SymbolView name="chevron.right" size={14} tintColor={theme.textTertiary} weight="semibold" />
              </View>
            </Pressable>
          </View>
        ))}
      </View>
    </ProgressiveBlurScreen>
  );
}

const styles = StyleSheet.create({
  list: {
    marginTop: Spacing.two,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#C6C6C8',
    marginLeft: 42,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    paddingVertical: Spacing.three,
    paddingHorizontal: Spacing.two,
  },
  rowPressed: {
    opacity: 0.6,
  },
  rowLabel: {
    flex: 1,
    fontSize: 17,
    lineHeight: 21,
    fontWeight: '400',
  },
});