import { LinearGradient } from 'expo-linear-gradient';
import { useRef, useState } from 'react';
import { Pressable, StyleSheet, View, type NativeSyntheticEvent, type TextLayoutEventData } from 'react-native';

import { BottomSheetModal, BottomSheetScrollView } from '@expo/ui/community/bottom-sheet';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

const MAX_LINES = 4;

export function ClampedText({
  text,
  title,
  backgroundColor,
  textColor,
  maxLines = MAX_LINES,
}: {
  text: string;
  title?: string;
  backgroundColor?: string;
  textColor?: string;
  maxLines?: number;
}) {
  const theme = useTheme();
  const bg = backgroundColor ?? theme.background;
  const sheetRef = useRef<BottomSheetModal>(null);
  const [isClamped, setIsClamped] = useState(false);

  const onLayout = (e: NativeSyntheticEvent<TextLayoutEventData>) => {
    if (e.nativeEvent.lines.length > maxLines) setIsClamped(true);
  };

  return (
    <>
      <View>
        {isClamped ? (
          <>
            <ThemedText
              themeColor={textColor ? undefined : 'textSecondary'}
              style={[styles.description, textColor ? { color: textColor } : null]}
              numberOfLines={maxLines}>
              {text}
            </ThemedText>
            <LinearGradient
              pointerEvents="none"
              colors={[`${bg}00`, bg]}
              start={{ x: 0.5, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.fade}
            />
          </>
        ) : (
          <ThemedText
            themeColor={textColor ? undefined : 'textSecondary'}
            style={[styles.description, textColor ? { color: textColor } : null]}
            onTextLayout={onLayout}>
            {text}
          </ThemedText>
        )}

        {isClamped ? (
          <View style={styles.moreWrap}>
            <LinearGradient
              pointerEvents="none"
              colors={[`${bg}00`, bg, `${bg}00`]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={StyleSheet.absoluteFill}
            />
            <Pressable onPress={() => sheetRef.current?.present()} style={styles.more}>
              <ThemedText type="small" style={[styles.moreText, textColor ? { color: textColor } : null]}>
                MÁS
              </ThemedText>
            </Pressable>
          </View>
        ) : null}
      </View>

      <BottomSheetModal
        ref={sheetRef}
        snapPoints={['90%']}
        enablePanDownToClose
        handleComponent={null}
        backgroundStyle={{ backgroundColor: theme.background }}>
        <BottomSheetScrollView contentContainerStyle={styles.sheetContent}>
          {title ? (
            <ThemedText style={styles.sheetTitle} numberOfLines={2}>
              {title}
            </ThemedText>
          ) : null}
          <ThemedText style={styles.sheetDescription}>
            {text}
          </ThemedText>
        </BottomSheetScrollView>
      </BottomSheetModal>
    </>
  );
}

const styles = StyleSheet.create({
  description: {
    fontWeight: '400',
    fontSize: 16,
    lineHeight: 21,
  },
  sheetDescription: {
    fontWeight: '400',
    fontSize: 16,
    lineHeight: 24,
  },
  fade: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: 21,
  },
  moreWrap: {
    position: 'absolute',
    right: 0,
    bottom: -2,
  },
  more: {
    alignSelf: 'flex-start',
    paddingVertical: Spacing.one,
    paddingRight: Spacing.two,
    paddingLeft: Spacing.four,
  },
  moreText: {
    fontWeight: '600',
    fontSize: 12,
    lineHeight: 15,
  },
  sheetContent: {
    paddingHorizontal: Spacing.four,
    paddingTop: Spacing.four,
    paddingBottom: Spacing.six,
  },
  sheetTitle: {
    fontSize: 22,
    lineHeight: 28,
    fontWeight: '500',
    textAlign: 'center',
    paddingBottom: Spacing.five,
  },
});