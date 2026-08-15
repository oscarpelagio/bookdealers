# Frontend BookDealers (Expo SDK 57)

App React Native con **Expo SDK 57**, `expo-router`, `@expo/ui` y `@tanstack/react-query`.
Solo corre en **iPhone físico** como dev build nativa (Xcode + cable). **Sin Expo Go y sin simuladores.**

## Arranque en iPhone físico

```bash
npm install
npx expo run:ios --device "Oscar"   # compila con Xcode, instala por cable, arranca Metro
npx expo start --dev-client         # solo Metro (LAN)
```

> Detalle completo (requisitos, networking, troubleshooting) en `DEV-IPHONE.md`.
> El backend FastAPI debe estar en marcha (`docker compose up -d` desde la raíz del repo).
> La URL se configura en `.env` con `EXPO_PUBLIC_API_URL` → **IP LAN del Mac** (ej. `http://192.168.x.x:8000`), nunca `localhost`.

## Estructura del proyecto

```
src/
  app/                     # expo-router: SOLO rutas
    _layout.tsx            # Stack + QueryClientProvider + ThemeProvider
    (tabs)/                # NativeTabs: index (buscar), explore (catálogos)
    book/[id].tsx          # Detalle de libro + disponibilidad
  components/              # UI reutilizable (kebab-case)
  api/                     # client.ts (fetch+ApiError), books.ts, types.ts
  constants/theme.ts       # Colors, Spacing, Fonts
  hooks/use-theme.ts
  utils/format.ts
```

## AI / agentes

El proyecto incluye skills de Expo para agentes (`.agents/skills`) y la config `..opencode.json` en la raíz del repo con el MCP remoto de Expo (`https://mcp.expo.dev/mcp`). Para el setup completo de agentes, ver `frontend/AGENTS.md`.

## Other setup steps

- To set up ESLint for linting, run `npx expo lint`, or follow our [guide on "Using ESLint and Prettier"](https://docs.expo.dev/guides/using-eslint/)
- If you'd like to set up unit testing, follow our guide on ["Unit Testing with Jest"](https://docs.expo.dev/develop/unit-testing/)
- Learn more about the TypeScript setup in this template in our guide on ["Using TypeScript"](https://docs.expo.dev/guides/typescript/)

## Learn more

To learn more about developing your project with Expo, look at the following resources:

- [Expo documentation](https://docs.expo.dev/): Learn fundamentals, or go into advanced topics with our [guides](https://docs.expo.dev/guides).
- [Learn Expo tutorial](https://docs.expo.dev/tutorial/introduction/): Follow a step-by-step tutorial where you'll create a project that runs on Android, iOS, and the web.

## Join the community

Join our community of developers creating universal apps.

- [Expo on GitHub](https://github.com/expo/expo): View our open source platform and contribute.
- [Discord community](https://chat.expo.dev): Chat with Expo users and ask questions.