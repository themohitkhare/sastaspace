export type ItemKind =
  | "kurta"
  | "saree"
  | "blouse"
  | "dupatta"
  | "sherwani"
  | "shirt"
  | "jeans"
  | "lehenga"
  | "juttis"
  | "jacket";

export type ItemTone =
  | "warm"
  | "red"
  | "indigo"
  | "green"
  | "ink"
  | "sand"
  | "rose"
  | "olive"
  | "cream"
  | "navy"
  | "black"
  | "denim";

export type Rack = "ethnic" | "office" | "weekend";

export interface Item {
  id: string;
  kind: ItemKind;
  name: string;
  tone: ItemTone;
  rack: Rack;
  lastWorn: string;
  wears: number;
  price: number;
}

export interface GapSuggestion {
  id: string;
  kind: ItemKind;
  name: string;
  tone: ItemTone;
  reason: string;
  source: "Myntra" | "Ajio" | "Amazon";
  price: number;
  url: string;
}

export const ITEMS: Item[] = [
  // ETHNIC rack
  { id: "i01", kind: "kurta",    name: "ivory chikankari kurta",    tone: "cream",  rack: "ethnic",  lastWorn: "3w",  wears: 11, price: 2400 },
  { id: "i02", kind: "kurta",    name: "indigo block-print kurta",  tone: "indigo", rack: "ethnic",  lastWorn: "6d",  wears: 14, price: 1800 },
  { id: "i03", kind: "kurta",    name: "rust linen kurta",          tone: "warm",   rack: "ethnic",  lastWorn: "2mo", wears: 6,  price: 2100 },
  { id: "i04", kind: "kurta",    name: "black silk kurta",          tone: "ink",    rack: "ethnic",  lastWorn: "4mo", wears: 3,  price: 3200 },
  { id: "i05", kind: "saree",    name: "red kanjivaram saree",      tone: "red",    rack: "ethnic",  lastWorn: "5mo", wears: 3,  price: 18500 },
  { id: "i06", kind: "saree",    name: "olive banarasi saree",      tone: "olive",  rack: "ethnic",  lastWorn: "8mo", wears: 2,  price: 9200 },
  { id: "i07", kind: "saree",    name: "sky chiffon saree",         tone: "indigo", rack: "ethnic",  lastWorn: "1y",  wears: 1,  price: 4200 },
  { id: "i08", kind: "lehenga",  name: "rose mirror-work lehenga",  tone: "rose",   rack: "ethnic",  lastWorn: "3mo", wears: 2,  price: 12500 },
  { id: "i09", kind: "blouse",   name: "gold brocade blouse",       tone: "warm",   rack: "ethnic",  lastWorn: "5mo", wears: 3,  price: 1600 },
  { id: "i10", kind: "blouse",   name: "olive zari blouse",         tone: "olive",  rack: "ethnic",  lastWorn: "8mo", wears: 2,  price: 1800 },
  { id: "i11", kind: "dupatta",  name: "cream bandhani dupatta",    tone: "cream",  rack: "ethnic",  lastWorn: "2w",  wears: 9,  price: 1200 },
  { id: "i12", kind: "dupatta",  name: "rose gota dupatta",         tone: "rose",   rack: "ethnic",  lastWorn: "3mo", wears: 2,  price: 2100 },
  { id: "i13", kind: "sherwani", name: "navy embroidered sherwani", tone: "navy",   rack: "ethnic",  lastWorn: "5mo", wears: 1,  price: 14000 },
  { id: "i14", kind: "juttis",   name: "cream embroidered juttis",  tone: "cream",  rack: "ethnic",  lastWorn: "2w",  wears: 8,  price: 1400 },
  { id: "i15", kind: "juttis",   name: "red wedding juttis",        tone: "red",    rack: "ethnic",  lastWorn: "5mo", wears: 2,  price: 1800 },

  // OFFICE rack
  { id: "i20", kind: "shirt",    name: "white oxford shirt",        tone: "cream",  rack: "office",  lastWorn: "2d",  wears: 22, price: 1500 },
  { id: "i21", kind: "shirt",    name: "sand linen shirt",          tone: "sand",   rack: "office",  lastWorn: "5d",  wears: 9,  price: 1900 },
  { id: "i22", kind: "shirt",    name: "indigo oxford shirt",       tone: "indigo", rack: "office",  lastWorn: "1w",  wears: 13, price: 1700 },
  { id: "i23", kind: "jacket",   name: "charcoal blazer",           tone: "ink",    rack: "office",  lastWorn: "3w",  wears: 6,  price: 5400 },
  { id: "i24", kind: "jeans",    name: "tailored black trousers",   tone: "ink",    rack: "office",  lastWorn: "4d",  wears: 18, price: 2800 },
  { id: "i25", kind: "jeans",    name: "beige chinos",              tone: "sand",   rack: "office",  lastWorn: "8d",  wears: 11, price: 2400 },

  // WEEKEND rack
  { id: "i30", kind: "shirt",    name: "faded green tee",           tone: "green",  rack: "weekend", lastWorn: "3d",  wears: 21, price: 600 },
  { id: "i31", kind: "shirt",    name: "cream band tee",            tone: "cream",  rack: "weekend", lastWorn: "1d",  wears: 28, price: 800 },
  { id: "i32", kind: "jeans",    name: "dark wash jeans",           tone: "denim",  rack: "weekend", lastWorn: "2d",  wears: 34, price: 2800 },
  { id: "i33", kind: "jeans",    name: "light wash straight jeans", tone: "denim",  rack: "weekend", lastWorn: "5d",  wears: 18, price: 2500 },
  { id: "i34", kind: "jacket",   name: "denim trucker jacket",      tone: "denim",  rack: "weekend", lastWorn: "3w",  wears: 7,  price: 3400 },
];

export const GAP_SUGGESTIONS: GapSuggestion[] = [
  { id: "g1", kind: "kurta",  name: "mustard cotton kurta",   tone: "warm", reason: "rounds out your ethnic-daily rack — you skew cool-toned",                 source: "Myntra", price: 1899, url: "https://www.myntra.com/kurta/mustard-cotton" },
  { id: "g2", kind: "blouse", name: "maroon raw-silk blouse", tone: "red",  reason: "your red saree has no matching blouse; you've reused the gold one 3x",   source: "Ajio",   price: 1299, url: "https://www.ajio.com/search/?text=maroon+silk+blouse" },
  { id: "g3", kind: "juttis", name: "black leather juttis",   tone: "ink",  reason: "a dark jutti would unlock the navy sherwani for low-key events",          source: "Amazon", price: 1650, url: "https://www.amazon.in/s?k=black+leather+juttis" },
];

export const itemsByRack = (rack: Rack): Item[] =>
  ITEMS.filter((i) => i.rack === rack);

export const itemById = (id: string): Item | undefined =>
  ITEMS.find((i) => i.id === id);

export const TONE_BG: Record<ItemTone, string> = {
  warm: "#f0e8d5",
  red: "#e9c3b2",
  indigo: "#ccd0d8",
  green: "#d0d4b8",
  ink: "#cac2b0",
  sand: "#ebe2c7",
  rose: "#e8ceca",
  olive: "#d4d0a8",
  cream: "#f0e9d4",
  navy: "#bcc1cc",
  black: "#c0bcb3",
  denim: "#c4cad0",
};

export const TONE_SWATCH: Record<ItemTone, string> = {
  warm: "#c9a56a",
  red: "#b93a2a",
  indigo: "#3e516f",
  green: "#6d7a3c",
  ink: "#2c2a27",
  sand: "#c8b37a",
  rose: "#c07a72",
  olive: "#7a7b3a",
  cream: "#e4d7a8",
  navy: "#34415c",
  black: "#1a1917",
  denim: "#4a5a72",
};

export const COUNT_IN_ROTATION = (items: Item[]): number =>
  items.filter((i) => i.lastWorn.endsWith("d") || i.lastWorn === "1w").length;
