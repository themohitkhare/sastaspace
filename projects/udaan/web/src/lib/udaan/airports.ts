export type Airport = {
  code: string;
  city: string;
  metro: boolean;
  fogProne?: boolean;
};

export const AIRPORTS: Airport[] = [
  { code: "DEL", city: "New Delhi", metro: true, fogProne: true },
  { code: "BOM", city: "Mumbai", metro: true },
  { code: "BLR", city: "Bengaluru", metro: true },
  { code: "HYD", city: "Hyderabad", metro: true },
  { code: "MAA", city: "Chennai", metro: true },
  { code: "CCU", city: "Kolkata", metro: true },
];

export function airportByCode(code: string): Airport | undefined {
  return AIRPORTS.find((a) => a.code === code);
}

export function cityOf(code: string): string {
  return airportByCode(code)?.city ?? code;
}
