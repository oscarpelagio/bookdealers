import { Stack } from 'expo-router';

import { tabHeaderOptions } from '@/constants/header-options';

export default function LibraryStackLayout() {
  return (
    <Stack screenOptions={tabHeaderOptions()}>
      <Stack.Screen name="library" options={{ title: 'Mi librería' }} />
      <Stack.Screen
        name="shelf/[slug]"
        options={{
          headerShown: true,
          title: '',
          headerShadowVisible: false,
          headerBackButtonDisplayMode: 'minimal',
        }}
      />
    </Stack>
  );
}