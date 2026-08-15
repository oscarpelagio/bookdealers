import { useEffect, useState } from 'react';
import * as Location from 'expo-location';

export type UserCoords = { lat: number; lon: number };

export function useUserLocation(enabled: boolean): UserCoords | null {
  const [coords, setCoords] = useState<UserCoords | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    (async () => {
      let status: Location.PermissionStatus;
      try {
        ({ status } = await Location.requestForegroundPermissionsAsync());
      } catch {
        return;
      }
      if (status !== 'granted' || cancelled) return;
      try {
        const loc = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        if (!cancelled) {
          setCoords({ lat: loc.coords.latitude, lon: loc.coords.longitude });
        }
      } catch {
        // sin ubicación: el listado se muestra sin ordenar por distancia
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return coords;
}