import MaskedView from '@react-native-masked-view/masked-view';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import type { ReactNode } from 'react';
import { Platform, ScrollView, StyleSheet, Text, useColorScheme, View } from 'react-native';
import { easeGradient } from 'react-native-easing-gradient';
import Animated, {
  Extrapolation,
  interpolate,
  useAnimatedProps,
  useAnimatedScrollHandler,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

const MaxBlurIntensity = 50;

const AnimatedBlurView = Animated.createAnimatedComponent(BlurView);

type ProgressiveBlurScreenProps = {
  /** Título grande (fade al hacer scroll) y título compacto (spring in). */
  title: string;
  /** Subtítulo corto bajo el título grande y en el header compacto. */
  subtitle?: string;
  children: ReactNode;
};

/**
 * Pantalla con header "progressive blur" estilo iOS (Settings/Wallet/Music):
 * el título grande se desvanece al hacer scroll, entra un header compacto con
 * spring y el blur superior se intensifica progresivamente mediante una máscara
 * con gradiente. Solo aplica el efecto en iOS; el resto usa header nativo.
 */
export function ProgressiveBlurScreen({ title, subtitle, children }: ProgressiveBlurScreenProps) {
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const scheme = useColorScheme() ?? 'light';
  const isDark = scheme === 'dark';

  const scrollY = useSharedValue(0);

  const onScroll = useAnimatedScrollHandler({
    onScroll: (event) => {
      scrollY.value = event.contentOffset.y;
    },
  });

  const largeTitleStyle = useAnimatedStyle(() => ({
    opacity: interpolate(scrollY.value, [0, 60], [1, 0], Extrapolation.CLAMP),
  }));

  const smallHeaderStyle = useAnimatedStyle(() => ({
    opacity: interpolate(scrollY.value, [40, 80], [0, 1], Extrapolation.CLAMP),
    transform: [
      {
        translateY: interpolate(scrollY.value, [40, 80], [20, 0], Extrapolation.CLAMP),
      },
    ],
  }));

  const smallHeaderSubtitleStyle = useAnimatedStyle(() => {
    const shouldShow = scrollY.value > 70;
    return {
      opacity: withSpring(shouldShow ? 0.5 : 0, {
        damping: 18,
        stiffness: 120,
        mass: 1.2,
      }),
      transform: [
        {
          translateY: withSpring(shouldShow ? 0 : 30, {
            damping: 14,
            stiffness: 100,
            mass: 1,
          }),
        },
        {
          scale: withSpring(shouldShow ? 1 : 0.85, {
            damping: 16,
            stiffness: 150,
            mass: 0.8,
          }),
        },
      ],
    };
  });

  const headerBackgroundStyle = useAnimatedStyle(() => ({
    opacity: interpolate(scrollY.value, [0, 80], [0, 1], Extrapolation.CLAMP),
  }));

  const animatedHeaderBlur = useAnimatedProps(() => {
    const opacity = interpolate(scrollY.value, [100, 0], [0, 1], Extrapolation.CLAMP);
    return { intensity: opacity * MaxBlurIntensity };
  });

  const { colors, locations } = easeGradient({
    colorStops: isDark
      ? {
          0: { color: 'rgba(0,0,0,0.99)' },
          0.5: { color: 'black' },
          1: { color: 'transparent' },
        }
      : {
          0: { color: 'rgba(255,255,255,0.99)' },
          0.5: { color: 'white' },
          1: { color: 'transparent' },
        },
  });

  if (Platform.OS !== 'ios') {
    return (
      <ScrollView
        style={[styles.scrollView, { backgroundColor: theme.background }]}
        contentInsetAdjustmentBehavior="automatic"
        contentInset={{ bottom: insets.bottom + BottomTabInset + Spacing.three }}
        contentContainerStyle={styles.contentContainer}
        keyboardShouldPersistTaps="handled">
        <View style={[styles.container, styles.containerNonIos]}>{children}</View>
      </ScrollView>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor: theme.background }]}>
      <Animated.View
        style={[
          styles.maskedLayer,
          { height: insets.top + 150 },
          headerBackgroundStyle,
        ]}>
        <MaskedView
          maskElement={
            <LinearGradient
              colors={colors as any}
              locations={locations as any}
              style={StyleSheet.absoluteFill}
            />
          }
          style={StyleSheet.absoluteFill}>
          <LinearGradient
            colors={isDark ? ['black', 'rgba(0, 0, 0, 0.2)'] : ['white', 'rgba(255, 255, 255, 0.2)']}
            style={StyleSheet.absoluteFill}
          />
          <BlurView
            intensity={15}
            tint={isDark ? 'systemChromeMaterialDark' : 'systemChromeMaterialLight'}
            style={StyleSheet.absoluteFill}
          />
        </MaskedView>
      </Animated.View>

      <Animated.View
        style={[
          styles.fixedHeader,
          { paddingTop: insets.top + 12, height: insets.top + 56 },
          smallHeaderStyle,
        ]}>
        <Animated.Text style={[styles.smallHeaderTitle, { color: theme.text }]}>
          {title}
        </Animated.Text>
        {subtitle ? (
          <Animated.Text style={[styles.smallHeaderSubtitle, { color: theme.textSecondary }, smallHeaderSubtitleStyle]}>
            {subtitle}
          </Animated.Text>
        ) : null}
        <AnimatedBlurView
          animatedProps={animatedHeaderBlur}
          tint={isDark ? 'dark' : 'light'}
          style={StyleSheet.absoluteFill}
        />
      </Animated.View>

      <Animated.ScrollView
        scrollEventThrottle={16}
        onScroll={onScroll}
        showsVerticalScrollIndicator={false}
        contentInsetAdjustmentBehavior="automatic"
        contentInset={{ bottom: insets.bottom + BottomTabInset + Spacing.three }}
        contentContainerStyle={styles.contentContainer}
        keyboardShouldPersistTaps="handled">
        <View style={styles.container}>
          <Animated.View style={[styles.header, largeTitleStyle]}>
            <Text style={[styles.headerTitle, { color: theme.text }]}>{title}</Text>
            {subtitle ? (
              <Text style={[styles.headerSubtitle, { color: theme.textSecondary }]}>{subtitle}</Text>
            ) : null}
          </Animated.View>
          {children}
        </View>
      </Animated.ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  maskedLayer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 10,
  },
  fixedHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingHorizontal: Spacing.four,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 11,
    overflow: 'hidden',
  },
  smallHeaderTitle: {
    fontSize: 17,
    fontWeight: '600',
  },
  smallHeaderSubtitle: {
    fontSize: 12,
    fontWeight: '400',
    marginTop: 2,
  },
  contentContainer: {
    flexGrow: 1,
  },
  container: {
    width: '100%',
    maxWidth: MaxContentWidth,
    alignSelf: 'center',
    flexGrow: 1,
    gap: Spacing.two,
    paddingHorizontal: Spacing.four,
    paddingBottom: Spacing.five,
  },
  containerNonIos: {
    paddingTop: Spacing.six,
  },
  header: {
    paddingTop: Spacing.two,
    paddingBottom: Spacing.two,
  },
  headerTitle: {
    fontSize: 34,
    fontWeight: '700',
    letterSpacing: -0.5,
    paddingLeft: 2,
  },
  headerSubtitle: {
    fontSize: 11,
    fontWeight: '600',
    paddingTop: Spacing.one,
    paddingLeft: Spacing.one,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
});
