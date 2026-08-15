import { Stack } from 'expo-router';

import { tabHeaderOptions } from '@/constants/header-options';

export default function DiscoverStackLayout() {
  return (
    <Stack screenOptions={tabHeaderOptions()}>
      <Stack.Screen name="discover" options={{ title: 'Descubrir' }} />
    </Stack>
  );
}