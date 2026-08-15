import { Stack } from 'expo-router';

import { tabHeaderOptions } from '@/constants/header-options';

export default function SearchStackLayout() {
  return (
    <Stack screenOptions={tabHeaderOptions()}>
      <Stack.Screen name="search" options={{ title: 'Buscar' }} />
    </Stack>
  );
}