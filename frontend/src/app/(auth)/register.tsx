import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { ApiError } from '@/api/client';
import { FormField } from '@/components/form-field';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';

type FieldErrors = Partial<Record<'username' | 'email' | 'fullName' | 'password', string>>;

const PASSWORD_RE =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$/;

export default function RegisterScreen() {
  const router = useRouter();
  const { signUp } = useAuth();
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [fieldError, setFieldError] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [devVerifyUrl, setDevVerifyUrl] = useState<string | null>(null);

  const validate = () => {
    const next: FieldErrors = {};
    if (!username.trim()) next.username = 'Elige un nombre de usuario';
    else if (!/^[a-zA-Z0-9_.]{3,30}$/.test(username.trim()))
      next.username = '3-30 caracteres: letras, números, puntos o guiones bajos';
    if (!email.trim()) next.email = 'Introduce tu email';
    else if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = 'Email no válido';
    if (fullName.trim().length > 120) next.fullName = 'Máximo 120 caracteres';
    if (!password) next.password = 'Introduce una contraseña';
    else if (!PASSWORD_RE.test(password))
      next.password =
        'Mínimo 12 caracteres con mayúscula, minúscula, número y símbolo';
    setFieldError(next);
    return Object.keys(next).length === 0;
  };

  const onSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const result = await signUp({
        email: email.trim(),
        username: username.trim(),
        password,
        full_name: fullName.trim() || null,
      });
      if (result.requires_email_verification) {
        setFormError('Cuenta creada. Verifica tu email para poder iniciar sesión.');
        setDevVerifyUrl(result.dev_verification_url);
        setSubmitting(false);
        return;
      }
      router.replace('/login');
      router.dismissAll?.();
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(
          err.code === 'weak_password'
            ? 'Contraseña demasiado débil. Usa 12+ caracteres con mayúscula, minúscula, número y símbolo.'
            : err.code === 'already_exists'
              ? 'Ya existe una cuenta con ese email o nombre de usuario.'
              : err.message,
        );
      } else {
        setFormError('No se pudo crear la cuenta. Inténtalo de nuevo.');
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
              <ThemedText type="subtitle">Crear cuenta</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                Únete a BookDealers y guarda tu librería.
              </ThemedText>
            </View>

            <FormField
              label="Nombre de usuario"
              value={username}
              onChangeText={setUsername}
              placeholder="usuaria_books"
              autoCapitalize="none"
              autoCorrect={false}
              editable={!submitting}
              error={fieldError.username}
              testID="register-username"
            />

            <FormField
              label="Nombre completo (opcional)"
              value={fullName}
              onChangeText={setFullName}
              placeholder="Nombre Apellido"
              autoCapitalize="words"
              editable={!submitting}
              error={fieldError.fullName}
              testID="register-fullname"
            />

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
              testID="register-email"
            />

            <FormField
              label="Contraseña"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry
              autoComplete="new-password"
              editable={!submitting}
              error={fieldError.password}
              testID="register-password"
            />

            {formError ? (
              <ThemedText type="small" style={styles.errorSecondary} testID="register-error">
                {formError}
                {devVerifyUrl ? ' Abre el enlace de verificación que recibiste por email.' : ''}
              </ThemedText>
            ) : null}

            <Pressable
              onPress={onSubmit}
              disabled={submitting}
              style={({ pressed }) => [
                styles.submitButton,
                (pressed || submitting) && styles.submitButtonPressed,
              ]}
              testID="register-submit">
              {submitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <ThemedText type="smallBold" style={styles.submitLabel}>
                  Crear cuenta
                </ThemedText>
              )}
            </Pressable>

            <View style={styles.footer}>
              <ThemedText type="small" themeColor="textSecondary">
                ¿Ya tienes cuenta?
              </ThemedText>
              <Link href="/login" asChild>
                <Pressable disabled={submitting}>
                  <ThemedText type="smallBold" style={styles.link}>
                    Inicia sesión
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
    marginTop: Spacing.one,
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