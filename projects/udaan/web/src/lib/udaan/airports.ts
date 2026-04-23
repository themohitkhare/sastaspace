export type Airport = {
  code: string;
  city: string;
  metro: boolean;
  /** 0..1 — SW monsoon exposure. 1.0 = coastal west, 0.3 = rain-shadow. */
  monsoonSeverity: number;
  /** Northern-India Dec–Jan fog belt. */
  fogProne?: boolean;
};

// Top-30 Indian airports by scheduled passenger traffic. monsoonSeverity is a
// hand-curated climate-zone proxy (coastal-west = 1.0, coastal-east/NE = 0.9,
// deccan-inland = 0.7, north-plains = 0.5, rain-shadow = 0.3). fogProne flags
// the North-Indian winter fog belt (Punjab, Delhi-NCR, UP, Bihar, Haryana).
// Sorted alphabetically by city for readable dropdown UX.
export const AIRPORTS: Airport[] = [
  { code: "IXA", city: "Agartala", metro: false, monsoonSeverity: 0.9 },
  { code: "AMD", city: "Ahmedabad", metro: false, monsoonSeverity: 0.5, fogProne: true },
  { code: "ATQ", city: "Amritsar", metro: false, monsoonSeverity: 0.5, fogProne: true },
  { code: "IXB", city: "Bagdogra", metro: false, monsoonSeverity: 0.9 },
  { code: "BLR", city: "Bengaluru", metro: true, monsoonSeverity: 0.7 },
  { code: "BHO", city: "Bhopal", metro: false, monsoonSeverity: 0.7 },
  { code: "BBI", city: "Bhubaneswar", metro: false, monsoonSeverity: 0.9 },
  { code: "IXC", city: "Chandigarh", metro: false, monsoonSeverity: 0.5, fogProne: true },
  { code: "MAA", city: "Chennai", metro: true, monsoonSeverity: 0.8 },
  { code: "GOX", city: "Goa (Mopa)", metro: false, monsoonSeverity: 1.0 },
  { code: "GOI", city: "Goa (Dabolim)", metro: false, monsoonSeverity: 1.0 },
  { code: "GAU", city: "Guwahati", metro: false, monsoonSeverity: 0.9 },
  { code: "HYD", city: "Hyderabad", metro: true, monsoonSeverity: 0.7 },
  { code: "IDR", city: "Indore", metro: false, monsoonSeverity: 0.7 },
  { code: "JAI", city: "Jaipur", metro: false, monsoonSeverity: 0.5, fogProne: true },
  { code: "COK", city: "Kochi", metro: false, monsoonSeverity: 1.0 },
  { code: "CCU", city: "Kolkata", metro: true, monsoonSeverity: 0.9 },
  { code: "LKO", city: "Lucknow", metro: false, monsoonSeverity: 0.6, fogProne: true },
  { code: "IXM", city: "Madurai", metro: false, monsoonSeverity: 0.7 },
  { code: "IXE", city: "Mangaluru", metro: false, monsoonSeverity: 1.0 },
  { code: "BOM", city: "Mumbai", metro: true, monsoonSeverity: 1.0 },
  { code: "NAG", city: "Nagpur", metro: false, monsoonSeverity: 0.7 },
  { code: "DEL", city: "New Delhi", metro: true, monsoonSeverity: 0.5, fogProne: true },
  { code: "PAT", city: "Patna", metro: false, monsoonSeverity: 0.7, fogProne: true },
  { code: "PNQ", city: "Pune", metro: false, monsoonSeverity: 0.8 },
  { code: "IXR", city: "Ranchi", metro: false, monsoonSeverity: 0.7 },
  { code: "SXR", city: "Srinagar", metro: false, monsoonSeverity: 0.3, fogProne: true },
  { code: "TRV", city: "Thiruvananthapuram", metro: false, monsoonSeverity: 1.0 },
  { code: "VNS", city: "Varanasi", metro: false, monsoonSeverity: 0.7, fogProne: true },
  { code: "VTZ", city: "Visakhapatnam", metro: false, monsoonSeverity: 0.8 },
];

export function airportByCode(code: string): Airport | undefined {
  return AIRPORTS.find((a) => a.code === code);
}

export function cityOf(code: string): string {
  return airportByCode(code)?.city ?? code;
}
