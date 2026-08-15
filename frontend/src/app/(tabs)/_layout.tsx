import { NativeTabs } from 'expo-router/unstable-native-tabs';
import { Platform, useColorScheme } from 'react-native';

import { Colors } from '@/constants/theme';

export default function TabsLayout() {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'unspecified' ? 'light' : scheme];

  return (
    <NativeTabs
      blurEffect={Platform.OS === 'ios' ? 'systemUltraThinMaterial' : undefined}
      indicatorColor={colors.backgroundElement}
      tintColor="#E0353D"
      labelStyle={{ default: { color: colors.textSecondary }, selected: { color: '#E0353D' } }}
      iconColor={{ default: colors.textSecondary, selected: '#E0353D' }}>
      <NativeTabs.Trigger name="(index)" disableAutomaticContentInsets>
        <NativeTabs.Trigger.Label>Inicio</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="house.fill" md="home" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="(library)" disableAutomaticContentInsets>
        <NativeTabs.Trigger.Label>Mi librería</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="books.vertical.fill" md="menu_book" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="(discover)" disableAutomaticContentInsets>
        <NativeTabs.Trigger.Label>Descubrir</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="safari.fill" md="explore" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="(search)" role="search" disableAutomaticContentInsets>
        <NativeTabs.Trigger.Label>Buscar</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="magnifyingglass" md="search" />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}