# Frontend BookDealers (Expo SDK 57)

App React Native con **Expo SDK 57**, `expo-router`, **@expo/ui** y **@tanstack/react-query**.

## Lectura obligatoria antes de tocar código

- Expo ha cambiado mucho: lee la documentación versionada **v57.0.0** en https://docs.expo.dev/versions/v57.0.0/
- Usa el índice llms.txt para descubrir páginas: https://docs.expo.dev/llms.txt (cada página se lee como `.md`).

## Instalación / arranque

```bash
npm install
npx expo run:ios --device "Oscar"   # dev build nativa en iPhone físico (Xcode, por cable)
npx expo start --dev-client         # solo Metro (LAN)
```

> **NUNCA** usar Expo Go ni simuladores/emuladores (no cargan en esta máquina, 8 GB RAM).
> Todo el flujo de dispositivo físico está documentado en `DEV-IPHONE.md` — leerlo antes
> de tocar nada de build/arranque.

## Estructura

```
src/
  app/                     # expo-router: SOLO rutas
    _layout.tsx            # Stack + QueryClientProvider + ThemeProvider
    (tabs)/                # NativeTabs: index (buscar), explore (catálogos)
    book/[id].tsx          # Detalle de libro + disponibilidad
  components/              # UI reutilizable (kebab-case)
  api/                     # client.ts (fetch+ApiError), books.ts, types.ts
  constants/theme.ts       # Colors, Spacing, Fonts
  hooks/use-theme.ts       # color scheme → Colors
  utils/format.ts          # formateo fechas + labels de estado
```

Convención: las rutas (`src/app/*`) solo renderizan; la UI compleja va en la misma
carpeta si es privada. Estilos con `StyleSheet.create` al final del archivo.

## API del backend (FastAPI, host `EXPO_PUBLIC_API_URL`)

- `GET /search/google?title=&author=` → `Book[]`
- `GET /search/openlibrary?title=&author=` → `Book[]`
- `GET /search/z3950?title=&author=&catalog=aladi` → `Book[]`
- `GET /availability/z3950?book_id=&catalog=aladi` → `AvailabilityEntry[]`
- `GET /availability/ebiblio?book_id=&catalog=ebiblio` → `AvailabilityEntry[]`

Tipos en `src/api/types.ts`. Los errores tipados van en `ApiError` (client.ts).
Auth usa JWT (acceso 15 min + refresh 30 días) — tokens en `expo-secure-store`.

## Assets existentes

Iconos de tabs en `assets/images/tabIcons/` (home.png, explore.png). El tema
define los colores semánticos `text`, `backgroundElement`, `textSecondary`...

## AI / agentes disponibles

El proyecto incluye skills de Expo oficiales en `.agents/skills/` (cargadas por opencode vía
`..opencode.json`) y el MCP remoto de Expo configurado.

- **Expo MCP (remoto)**: `https://mcp.expo.dev/mcp`. Permite leer docs, gestionar EAS
  builds/workflows. Autentícate con tu cuenta de Expo cuando lo pida el cliente MCP.
- **agent-device (local MCP)**: comandos `agent-device` (de Callstack) para operar la app
  corriendo en simulador/emulador (snapshots, taps, screenshots, logs). CLI instalado globalmente.
- **expo-mcp (local)**: para capacidades locales (screenshots, devtools) usa
  `EXPO_UNSTABLE_MCP_SERVER=1 npx expo start` tras `npx expo install expo-mcp --dev`.
- **Argent (Software Mansion)**: opcional, `npx @swmansion/argent init` (registra MCP +
  skills). Útil para controlar emulador iOS/Android desde el editor.
- **Skills Expo**: siempre que un agente vaya a tocar Expo que cargue la skill apropiada
  (`expo-router`, `expo-ui`, `expo-data-fetching`, `expo-native-ui`, `expo-project-structure`...).

Instrucciones detalladas en `..opencode.json` de la raíz del repo y en `frontend/README.md`.

## Preferencias

- Data fetching: `@tanstack/react-query` (sin axios). fetch con manejador de error.
- Iconos: `expo-symbols` (SymbolView). textos: `ThemedText` (tipos: title, subtitle,
  small, smallBold, link...).
- Variables públicas de exposed solo con prefijo `EXPO_PUBLIC_`.
- **No usar screenshots ni agent-device sobre el dispositivo**: el usuario verifica
  visualmente en su iPhone. No intentar capturas de pantalla.