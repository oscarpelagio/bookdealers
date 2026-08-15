import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { ApiError } from '@/api/client';
import { FormField } from '@/components/form-field';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';

export default function LoginScreen() {
  const router = useRouter();
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [fieldError, setFieldError] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);

  const validate = () => {
    const next: { email?: string; password?: string } = {};
    if (!email.trim()) next.email = 'Introduce tu email';
    else if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = 'Email no válido';
    if (!password) next.password = 'Introduce tu contraseña';
    setFieldError(next);
    return Object.keys(next).length === 0;
  };

  const onSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await signIn(email.trim(), password);
      router.replace('/');
    } catch (error) {
      if (error instanceof ApiError) {
        setFormError(
          error.code === 'invalid_credentials'
            ? 'Email o contraseña incorrectos.'
            : error.message,
        );
      } else {
        setFormError('No se pudo iniciar sesión. Inténtalo de nuevo.');
      }
      setSubmitting(false);
    }
  };

  return (
    <ThemedView style={styles.screen}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled">
          <View style={styles.container}>
            <View style={styles.header}>
              <ThemedText type="subtitle">BookDealers</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                Inicia sesión para buscar libros y consultar tu librería.
              </ThemedText>
            </View>

            <FormField
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="tu@email.com"
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              editable={!submitting}
              error={fieldError.email}
              testID="login-email"
            />

            <FormField
              label="Contraseña"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry
              autoComplete="current-password"
              editable={!submitting}
              error={fieldError.password}
              testID="login-password"
            />

            {formError ? (
              <ThemedText type="small" style={styles.errorSecondary} testID="login-error">
                {formError}
              </ThemedText>
            ) : null}

            <Pressable
              onPress={onSubmit}
              disabled={submitting}
              style={({ pressed }) => [
                styles.submitButton,
                (pressed || submitting) && styles.submitButtonPressed,
              ]}
              testID="login-submit">
              {submitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <ThemedText type="smallBold" style={styles.submitLabel}>
                  Iniciar sesión
                </ThemedText>
              )}
            </Pressable>

            <View style={styles.footer}>
              <ThemedText type="small" themeColor="textSecondary">
                ¿No tienes cuenta?
              </ThemedText>
              <Link href="/register" asChild>
                <Pressable disabled={submitting}>
                  <ThemedText type="smallBold" style={styles.link}>
                    Regístrate
                  </ThemedText>
                </Pressable>
              </Link>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  flex: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.five,
  },
  container: {
    width: '100%',
    maxWidth: MaxContentWidth,
    gap: Spacing.three,
  },
  header: {
    gap: Spacing.one,
    marginBottom: Spacing.two,
  },
  submitButton: {
    backgroundColor: '#208AEF',
    borderRadius: Spacing.two,
    paddingVertical: Spacing.three,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  submitButtonPressed: {
    opacity: 0.7,
  },
  submitLabel: {
    color: '#FFFFFF',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.one,
    marginTop: Spacing.two,
  },
  link: {
    color: '#208AEF',
  },
  errorSecondary: {
    color: '#FF3B30',
  },
});