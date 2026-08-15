import { ProgressiveBlurScreen } from '@/components/progressive-blur-screen';
import { ThemedText } from '@/components/themed-text';

export default function DiscoverScreen() {
  return (
    <ProgressiveBlurScreen title="Descubrir">
      <ThemedText type="small" themeColor="textSecondary" selectable>
        Novedades, recomendaciones y catálogos para explorar.
      </ThemedText>
    </ProgressiveBlurScreen>
  );
}
