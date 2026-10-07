export type RaceRow = {
  code: string;
  name: string;
  team: string;
  color: string;
  position: number;
  gap: string;
  retired: boolean;
};

export type DriverRow = {
  code: string;
  name: string;
  team: string;
  color: string;
  position: number;
  retired: boolean;
  season: number;
  racePoints: number;
  projected: number;
};

export type ConstructorRow = {
  name: string;
  color: string;
  season: number;
  racePoints: number;
  projected: number;
  drivers: { code: string; racePoints: number }[];
};

export type Snapshot = {
  status: "preview" | "live" | "connecting" | "offline" | string;
  preview: boolean;
  session: { trackName: string; location: string; name: string; kind: string };
  raceOrder: RaceRow[];
  drivers: DriverRow[];
  constructors: ConstructorRow[];
  cars: { code: string; color: string; x: number; y: number }[];
  track: [number, number][];
};

export const emptySnapshot: Snapshot = {
  status: "connecting",
  preview: false,
  session: { trackName: "Waiting for session", location: "", name: "", kind: "" },
  raceOrder: [],
  drivers: [],
  constructors: [],
  cars: [],
  track: [],
};

export function paint(color: string) {
  if (!color) return "#888888";
  return color.startsWith("#") ? color : `#${color}`;
}

export function points(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}
