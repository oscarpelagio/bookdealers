import { Stack } from 'expo-router';
import { Platform } from 'react-native';

import { tabHeaderOptions } from '@/constants/header-options';

export default function SearchStackLayout() {
  return (
    <Stack screenOptions={tabHeaderOptions()}>
      <Stack.Screen
        name="search"
        options={
          Platform.OS === 'ios'
            ? { headerShown: true, headerTitle: 'Buscar', headerShadowVisible: false }
            : { title: 'Buscar' }
        }
      />
    </Stack>
  );
}
