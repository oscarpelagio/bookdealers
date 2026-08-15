import { useEffect, useState } from 'react';

import { getColors } from 'react-native-image-colors';

export function useCoverColor(uri?: string | null, initial?: string | null): string | null {
  const [color, setColor] = useState<string | null>(initial ?? null);

  useEffect(() => {
    let cancelled = false;

    if (!uri) return;

    getColors(uri, {
      fallback: '#000000',
      cache: true,
      key: uri,
      quality: 'low',
    })
      .then((result) => {
        if (cancelled) return;
        const next =
          result.platform === 'ios' ? result.background : result.dominant;
        setColor(next || null);
      })
      .catch(() => {
        if (!cancelled) setColor(null);
      });

    return () => {
      cancelled = true;
    };
  }, [uri]);

  return uri ? color : null;
}
