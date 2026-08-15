import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

interface TokenStorage {
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
  removeItem: (key: string) => Promise<void>;
}

const webStorage: TokenStorage = {
  getItem: async (key) =>
    typeof localStorage === 'undefined' ? null : localStorage.getItem(key),
  setItem: async (key, value) => {
    if (typeof localStorage !== 'undefined') localStorage.setItem(key, value);
  },
  removeItem: async (key) => {
    if (typeof localStorage !== 'undefined') localStorage.removeItem(key);
  },
};

const nativeStorage: TokenStorage = {
  getItem: (key) => SecureStore.getItemAsync(key),
  setItem: (key, value) => SecureStore.setItemAsync(key, value),
  removeItem: (key) => SecureStore.deleteItemAsync(key),
};

export const tokenStorage: TokenStorage =
  Platform.OS === 'web' ? webStorage : nativeStorage;