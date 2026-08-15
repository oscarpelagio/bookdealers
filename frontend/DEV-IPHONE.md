# Desarrollo en iPhone físico — dev build nativa (sin Expo Go, sin simulador)

Reglas del proyecto (las usa el agente al tocar Expo/frontend):

- **NUNCA** usar Expo Go.
- **NUNCA** usar simuladores ni emuladores (no cargan en esta máquina: 8 GB RAM).
- La app corre como **development build nativa**: compilada con Xcode e instalada
  por cable en el iPhone físico, con JS servido por Metro.

## Estado del setup (verificado 2026-08-08)

- Xcode **26.6** + CocoaPods **1.17.0** instalados.
- `ios/` existe (generado por `prebuild`, está en `.gitignore`), Pods instalados.
- **Signing listo**: `ios.appleTeamId = Z8567P8HMM` en `app.json` (lo aplica `prebuild`
  al pbxproj; firma automática, identidad "Apple Development"). Bundle id: `com.oscaarpelagio.bookdealers`.
- **`expo-dev-client` instalado** (`npx expo install expo-dev-client`) y en el Podfile.
- iPhone físico "Oscar" (iPhone 16 Pro, iOS 26.5) pareado; se comprueba con
  `xcrun devicectl list devices` (estado `available (paired)`). Si `xctrace` lo muestra
  "Offline" es solo por pantalla bloqueada: desbloquear y re-comprobar con `devicectl`.
- **Compilado e instalado con éxito** vía `npx expo run:ios --device "Oscar"` (0 errores,
  bundle cargado desde Metro en LAN). El flujo ya funciona.
- `.env` con `EXPO_PUBLIC_API_URL` debe apuntar a la **IP LAN del Mac**, nunca `localhost`
  (en el iPhone, `localhost` = el teléfono).

## Requisitos para arrancar

1. iPhone conectado por cable USB, desbloqueado y con **"Confiar en esta computadora"**.
   - Comprobar que aparece online: `xcrun devicectl list devices` (estado `available (paired)`).
     > `xcrun xctrace list devices` suele listar SOLO simuladores y a veces no muestra el
     > físico: usar siempre `devicectl` para verificar el iPhone.
   - El nombre del iPhone para `--device` es `Oscar` (iOS 26.5).
2. Backend FastAPI corriendo y accesible desde el iPhone:
   - `docker compose up -d` desde la raíz del repo (expone `:8000` en `0.0.0.0`). **El daemon
     de Docker/OrbStack tiene que estar arrancado antes.**
3. IP LAN del Mac (el iPhone y el Mac deben estar en la misma red):
   - `ipconfig getifaddr en0` (o `en1`). Actual: `172.20.10.11`.
   - Debe coincidir con `EXPO_PUBLIC_API_URL` en `frontend/.env`.

## Configurar el networking

```bash
# frontend/.env — el iPhone no puede usar localhost
EXPO_PUBLIC_API_URL=http://<IP-LAN-DEL-MAC>:8000
```

`EXPO_PUBLIC_*` se inyectan al **hacer bundle** (tiempo de arranque de Metro): si cambia
la IP, reiniciar `expo start` con `--clear`. El app en el iPhone necesita alcanzar:
- `:8000` → backend FastAPI.
- `:8081` → Metro (bundle).

## One-time setup (solo la primera vez)

```bash
cd frontend
npx expo install expo-dev-client      # 1. añade el dev client
npx expo prebuild --clean             # 2. regenera ios/ con el plugin de dev-client
# (prebuild ejecuta `pod install` automáticamente)
```

> `ios/` está en `.gitignore`: es regenerable. Nunca editar el proyecto Xcode a mano;
> cualquier cambio nativo se hace desde `app.json`/plugins y `npx expo prebuild`.

## Correr la app en el iPhone (flujo diario)

Desde la **raíz del repo**, todo en un comando (hace preflight y luego compila):

```bash
make iphone-run
# (equivalente a: make iphone-preflight && cd frontend && npx expo run:ios --device "Oscar")
```

Alternativa manual paso a paso:

```bash
cd frontend
npx expo run:ios --device "Oscar"
```

`make iphone-preflight` valida en orden: daemon de docker, que el backend responda en
`:8000`, que la IP LAN de `en0` coincida con `EXPO_PUBLIC_API_URL` de `.env`, y que el
iPhone aparezca como `available (paired)` en `devicectl`.

Qué hace: compila con `xcodebuild` (el esquema `BookDealers`, Debug), instala el .app
por cable en el iPhone, arranca Metro y abre el dev client en la app. La **primera build
tarda varios minutos** (compila todos los pods). Con 8 GB de RAM: cerrar apps pesadas
(Xcode ya no necesita el simulador para nada).

Alternativa manual con Xcode (si `run:ios` falla):
1. Terminal A: `npx expo start --dev-client` (Metro en LAN).
2. Abrir `ios/BookDealers.xcworkspace` en Xcode.
3. Seleccionar el iPhone como destino del scheme y **Run**.
4. En el dev client del teléfono, elegir el dev server `exp://<IP-LAN>:8081`
   (o pulsar "Enter URL manually").

## Troubleshooting

- **iPhone aparece "Offline"** en `xcrun xctrace list devices`: desbloquearlo y esperar
  (y verificar con `xcrun devicectl list devices`, no con `xctrace`).
- **`make iphone-preflight` falla**: cada chequeo imprime un mensaje claro — falta arrancar
  Docker/OrbStack, backend caído, IP de `.env` desactualizada o iPhone no pareado.
- **Firma de desarrollador gratuita**: el app caduca a los 7 días; reinstalar con `npx expo run:ios`.
- **Cambios en `app.json` / dependencias nativas**: `npx expo prebuild --clean` y volver a correr.
- **Metro sirve bundle viejo / errores raros**: `npx expo start --clear`.
- **Backend inalcanzable desde el iPhone**: comprobar que el Mac y el iPhone están en la
  misma red, `docker compose ps` y que el firewall de macOS no bloquee `8000`/`8081`.
- **La app no conecta con Metro**: en el launcher del dev client, "Enter URL manually":
  `exp://<IP-LAN>:8081`.
- **Crashes / logs nativos**: Xcode → Window → Devices and Simulators → *ver dispositivo* →
  "Open Console" (o `log stream` filtrado por `BookDealers`). No usar `xcrun simctl` (simulador).

## Cheatsheet de comandos

```bash
xcrun devicectl list devices                  # ver si el iPhone está online
ipconfig getifaddr en0                        # IP LAN del Mac
make iphone-preflight                        # validación previa (docker, backend, IP, iPhone)
make iphone-run                              # preflight + compilar/instalar/arrancar en el iPhone
npx expo install expo-dev-client            # añadir dev client
npx expo prebuild --clean                   # regenerar ios/ (+ pod install)
npx expo run:ios --device "Oscar"           # compilar + instalar + arrancar Metro
npx expo start --dev-client                 # solo Metro (LAN)
npx expo start --clear                      # Metro limpiando caché
docker compose up -d                        # backend + z3950 + postgres (raíz del repo)
```
