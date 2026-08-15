import { Platform } from 'react-native';

/**
 * Opciones de header de los Stack de cada tab. En iOS el header nativo se oculta
 * porque el efecto de "progressive blur" lo dibuja `ProgressiveBlurScreen`.
 * En el resto de plataformas se usa el header nativo con título.
 */
export function tabHeaderOptions() {
  if (Platform.OS === 'ios') {
    return {
      headerShown: false,
    } as const;
  }

  return {
    headerBackButtonDisplayMode: 'minimal',
  } as const;
}