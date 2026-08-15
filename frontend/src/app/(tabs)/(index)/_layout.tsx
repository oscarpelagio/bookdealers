import { Stack } from 'expo-router';

import { tabHeaderOptions } from '@/constants/header-options';

export default function IndexStackLayout() {
  return (
    <Stack screenOptions={tabHeaderOptions()}>
      <Stack.Screen name="index" options={{ title: 'Inicio' }} />
    </Stack>
  );
}