import { useMemo, useState } from 'react';
import { Linking } from 'react-native';

import { Host } from '@expo/ui';
import {
  BottomSheet,
  Button,
  ContentUnavailableView,
  Group,
  HStack,
  Image,
  List,
  Picker,
  ProgressView,
  Section,
  Spacer,
  Text,
  VStack,
} from '@expo/ui/swift-ui';
import {
  background,
  buttonBorderShape,
  buttonStyle,
  clipShape,
  controlSize,
  font,
  foregroundColor,
  frame,
  listSectionMargins,
  listStyle,
  lineLimit,
  onTapGesture,
  padding,
  pickerStyle,
  presentationBackground,
  presentationBackgroundInteraction,
  presentationDetents,
  presentationDragIndicator,
  scrollContentBackground,
  shapes,
  tag,
  truncationMode,
} from '@expo/ui/swift-ui/modifiers';

import type { AvailabilityEntry } from '@/api/types';
import { useBookAvailability } from '@/hooks/use-book-availability';
import { useUserLocation } from '@/hooks/use-user-location';
import { formatLanguage, statusPriority } from '@/utils/format';
import { distanceKm, formatKm } from '@/utils/distance';

const SERVICE_VALUES = ['Bibliotecas', 'Librerías'];
const PREVIEW_COUNT = 5;

const STATUS_GROUP_TITLES: Record<number, string> = {
  0: 'Disponibles',
  1: 'Disponibles',
  2: 'Cola',
};

type AvailabilityItem = {
  entry: AvailabilityEntry;
  km: number | null;
  status: number;
  index: number;
};

function dedupeByEstablishment(items: AvailabilityItem[]): AvailabilityItem[] {
  const byKey = new Map<string, AvailabilityItem>();
  for (const item of items) {
    const key = [item.entry.establishment_name, item.entry.establishment_city].filter(Boolean).join('\u0000');
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, item);
      continue;
    }
    let better = existing;
    if (item.status !== existing.status) {
      better = item.status < existing.status ? item : existing;
    } else if (existing.status === 2) {
      const itemQueue = item.entry.queue ?? Number.MAX_SAFE_INTEGER;
      const existingQueue = existing.entry.queue ?? Number.MAX_SAFE_INTEGER;
      better = itemQueue < existingQueue ? item : existing;
    } else if (item.km != null && existing.km == null) {
      better = item;
    }
    if (better !== existing) byKey.set(key, better);
  }
  return [...byKey.values()];
}

function formatLibraryName(name: string, city: string | null): string {
  const transformed = name
    .replace(/\bbiblioteca de\b/gi, '')
    .replace(/\bbiblioteca\b/gi, '')
    .trim();
  const base = transformed.length > 0 ? transformed : (city ?? name);
  return base.charAt(0).toUpperCase() + base.slice(1);
}

function AvailabilityRow({
  entry,
  distanceKmAway,
  transparent = false,
}: {
  entry: AvailabilityEntry;
  distanceKmAway: number | null;
  transparent?: boolean;
}) {
  const address = [
    entry.establishment_city,
    entry.establishment_street,
    entry.establishment_province,
  ]
    .filter(Boolean)
    .join(' · ');
  const openDirections = () => {
    if (entry.lat == null || entry.lon == null) return;
    const gmaps = `comgooglemaps://?daddr=${entry.lat},${entry.lon}`;
    const fallback = `https://maps.apple.com/?daddr=${entry.lat},${entry.lon}`;
    Linking.canOpenURL(gmaps).then((ok) => Linking.openURL(ok ? gmaps : fallback));
  };

  return (
    <HStack spacing={12}>
      <VStack
        alignment="leading"
        spacing={4}
        modifiers={[
          frame({ maxWidth: Infinity, alignment: 'leading' }),
          onTapGesture(() => (entry.link ? Linking.openURL(entry.link) : undefined)),
        ]}>
        <Text modifiers={[font({ size: 16, weight: 'semibold' })]}>
          {formatLibraryName(entry.establishment_name, entry.establishment_city)}
        </Text>
        {address.length > 0 ? (
          <Text
            modifiers={[
              font({ size: 14 }),
              lineLimit(1),
              truncationMode('tail'),
              foregroundColor('secondary'),
            ]}>
            {address}
          </Text>
        ) : null}
        {formatLanguage(entry.book_language) != null ? (
          <Text modifiers={[font({ size: 13 }), foregroundColor('tertiary')]}>
            {formatLanguage(entry.book_language)}
          </Text>
        ) : null}
      </VStack>
      {distanceKmAway != null ? (
        <Button
          onPress={openDirections}
          modifiers={[
            frame({ width: 60, height: 60, alignment: 'center' }),
            ...(transparent ? [] : [background('#F1F7FD', shapes.roundedRectangle({ cornerRadius: 12 }))]),
          ]}>
          <VStack
            alignment="center"
            spacing={1}
            modifiers={[
              frame({ maxWidth: Infinity, maxHeight: Infinity, alignment: 'center' }),
              padding({ top: 8, bottom: 8, leading: 6, trailing: 6 }),
              foregroundColor('#0187FD'),
            ]}>
            <Image systemName="arrow.triangle.turn.up.right.diamond.fill" size={16} />
            <Text modifiers={[font({ size: 12, weight: 'semibold' })]}>{formatKm(distanceKmAway)}</Text>
          </VStack>
        </Button>
      ) : null}
    </HStack>
  );
}

type AvailabilitySheetProps = {
  bookId: number;
  isPresented: boolean;
  onDismiss: () => void;
};

export function AvailabilitySheet({ bookId, isPresented, onDismiss }: AvailabilitySheetProps) {
  const [isLarge, setIsLarge] = useState(false);
  const [serviceIndex, setServiceIndex] = useState(0);
  const [shownCount, setShownCount] = useState<Record<number, number>>({});
  const availability = useBookAvailability(bookId, isPresented);
  const userCoords = useUserLocation(isPresented);

  const services = [
    { has: availability.hasLibraries, items: availability.libraries },
    { has: availability.hasBookshops, items: availability.bookshops },
  ];
  const active = services[serviceIndex] ?? services[0];

  const groupedItems = useMemo(() => {
    const computed = active.items.map((entry, index) => {
      const km =
        userCoords && entry.lat != null && entry.lon != null
          ? distanceKm(userCoords.lat, userCoords.lon, entry.lat, entry.lon)
          : null;
      return { entry, km, status: statusPriority(entry.book_status), index };
    });
    const items = dedupeByEstablishment(computed);

    const groups: { status: number; title: string; items: typeof items }[] = [];
    const groupPlan: { status: number; title: string; match: (s: number) => boolean }[] = [
      { status: 0, title: STATUS_GROUP_TITLES[0], match: (s) => s <= 1 },
      { status: 2, title: STATUS_GROUP_TITLES[2], match: (s) => s === 2 },
    ];
    for (const plan of groupPlan) {
      const members = items
        .filter((item) => plan.match(item.status))
        .sort((a, b) => {
          if (a.km == null && b.km == null) return 0;
          if (a.km == null) return 1;
          if (b.km == null) return -1;
          return a.km - b.km;
        });
      if (members.length === 0) continue;
      groups.push({ status: plan.status, title: plan.title, items: members });
    }
    return groups;
  }, [active.items, userCoords]);

  let body;
  if (availability.isLoading) {
    body = (
      <VStack
        alignment="center"
        spacing={8}
        modifiers={[frame({ maxHeight: Infinity, maxWidth: Infinity, alignment: 'top' }), padding({ top: 48 })]}>
        <ProgressView />
      </VStack>
    );
  } else if (availability.isError) {
    body = (
      <ContentUnavailableView
        title="Vaya, algo ha fallado"
        systemImage="wifi.exclamationmark"
        description="No se pudo consultar la disponibilidad. Inténtalo de nuevo."
      />
    );
  } else if (!active.has) {
    body = (
      <ContentUnavailableView
        title="No está en tu catálogo"
        systemImage="books.vertical"
        description={`El servicio ${SERVICE_VALUES[serviceIndex]} no está configurado.`}
      />
    );
  } else if (active.items.length === 0) {
    body = (
      <ContentUnavailableView
        title="Sin resultados"
        systemImage="magnifyingglass"
        description="No hay ejemplares disponibles en este servicio ahora mismo."
      />
    );
  } else {
    body = (
      <List
        modifiers={[
          listStyle('insetGrouped'),
          ...(!isLarge ? [scrollContentBackground('hidden')] : []),
          listSectionMargins({ length: 4, edges: 'top' }),
          frame({ maxHeight: Infinity, alignment: 'top' }),
        ]}>
        {groupedItems.map((group) => {
          const shown = shownCount[group.status] ?? PREVIEW_COUNT;
          const visible = group.items.slice(0, shown);
          const hasMore = group.items.length > shown;
          return (
            <Section key={group.status} title={group.title}>
              {visible.map(({ entry, km }, index) => (
                <AvailabilityRow
                  key={`${entry.catalog_id}-${entry.book_id}-${entry.establishment_name}-${index}`}
                  entry={entry}
                  distanceKmAway={km}
                  transparent={!isLarge}
                />
              ))}
              {hasMore ? (
                <HStack alignment="center" modifiers={[frame({ maxWidth: Infinity })]}>
                  <Text
                    modifiers={[
                      onTapGesture(() =>
                        setShownCount((prev) => ({
                          ...prev,
                          [group.status]: (prev[group.status] ?? PREVIEW_COUNT) + PREVIEW_COUNT,
                        })),
                      ),
                      font({ size: 14, weight: 'medium' }),
                      foregroundColor('#007AFF'),
                      padding({ top: 0, bottom: 0 }),
                    ]}>
                    Ver más
                  </Text>
                </HStack>
              ) : null}
            </Section>
          );
        })}
      </List>
    );
  }

  return (
    <Host matchContents colorScheme="light">
      <BottomSheet
        isPresented={isPresented}
        onIsPresentedChange={(value) => {
          if (!value) onDismiss();
        }}
        onDismiss={onDismiss}>
        <Group
          modifiers={[
            presentationDetents(['medium', 'large'], {
              selection: isLarge ? 'large' : 'medium',
              onSelectionChange: (detent) => setIsLarge(detent === 'large'),
            }),
            presentationDragIndicator('hidden'),
            presentationBackground(isLarge ? '#F1F2F6FF' : '#00000000'),
            presentationBackgroundInteraction('enabled'),
          ]}>
          <VStack
            alignment="center"
            spacing={0}
            modifiers={[frame({ maxHeight: Infinity, maxWidth: Infinity, alignment: 'top' })]}>
            <HStack
              alignment="center"
              spacing={16}
              modifiers={[padding({ top: 12, leading: 16, trailing: 16 }), frame({ maxWidth: Infinity })]}>
              <Button
                onPress={() => {}}
                modifiers={[
                  buttonStyle('glass'),
                  buttonBorderShape('circle'),
                  clipShape('circle'),
                  controlSize('extraLarge'),
                  frame({ width: 56, height: 56, alignment: 'center' }),
                ]}>
                <Image systemName="line.3.horizontal.decrease" size={24} />
              </Button>
              <Spacer />
              <Picker
                selection={serviceIndex}
                onSelectionChange={(value) => setServiceIndex(value as number)}
                modifiers={[pickerStyle('segmented'), controlSize('extraLarge'), foregroundColor('#000000')]}>
                <Text modifiers={[tag(0), foregroundColor('#000000')]}>Bibliotecas</Text>
                <Text modifiers={[tag(1), foregroundColor('#000000')]}>Librerías</Text>
              </Picker>
            </HStack>
            {body}
          </VStack>
        </Group>
      </BottomSheet>
    </Host>
  );
}