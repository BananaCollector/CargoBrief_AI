export type AddressParts = {
  pickup_location?: string | null;
  pickup_street?: string | null;
  pickup_building_number?: string | null;
  pickup_apartment?: string | null;
  pickup_postal_code?: string | null;
  delivery_location?: string | null;
  delivery_street?: string | null;
  delivery_building_number?: string | null;
  delivery_apartment?: string | null;
  delivery_postal_code?: string | null;
};

export function formatOrderAddress(
  order: AddressParts,
  addressType: 'pickup' | 'delivery',
): string {
  const street = order[`${addressType}_street`];
  const buildingNumber = order[`${addressType}_building_number`];
  const apartment = order[`${addressType}_apartment`];
  const postalCode = order[`${addressType}_postal_code`];
  const city = order[`${addressType}_location`];
  const streetLine = [street, buildingNumber]
    .filter(Boolean)
    .join(' ');
  const fullStreetLine = streetLine
    ? `${streetLine}${apartment ? `/${apartment}` : ''}`
    : apartment ?? '';
  const postalLine = [postalCode, city].filter(Boolean).join(' ');
  return [fullStreetLine, postalLine].filter(Boolean).join(', ');
}
