"use client";

import { useFlip } from "@/lib/useFlip";
import { useRace } from "@/lib/useRace";
import { paint, points, type ConstructorRow, type DriverRow, type RaceRow } from "@/lib/types";
import { type ReactNode } from "react";

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03]">
      <h2 className="border-b border-white/10 px-3 py-2.5 text-[11px] font-bold tracking-[0.16em] text-[#9aa3b5]">
        {title}
      </h2>
      <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
    </section>
  );
}

function RaceOrder({ rows }: { rows: RaceRow[] }) {
  const nodes = useFlip(rows.map((row) => row.code));
  return (
    <Panel title="RACE ORDER">
      {rows.map((row) => (
        <div
          key={row.code}
          ref={(node) => {
            if (node) nodes.current.set(row.code, node);
            else nodes.current.delete(row.code);
          }}
          className={`grid grid-cols-[28px_4px_1fr_auto] items-center gap-2 border-t border-white/5 px-3 py-2 ${row.retired ? "opacity-45" : ""}`}
        >
          <span className="font-extrabold tabular-nums text-[#d5dbea]">{row.position}</span>
          <span className="h-7 rounded-sm" style={{ background: paint(row.color) }} />
          <span>
            <span className="block font-extrabold tracking-wide">{row.code}</span>
            <span className="block text-[11px] font-semibold text-[#8b95a8]">{row.name}</span>
          </span>
          <span className="text-xs font-bold tabular-nums text-[#c5d0e0]">{row.retired ? "OUT" : row.gap}</span>
        </div>
      ))}
    </Panel>
  );
}

function Drivers({ rows }: { rows: DriverRow[] }) {
  const nodes = useFlip(rows.map((row) => row.code));
  return (
    <Panel title="DRIVERS BY POINTS">
      {rows.map((row, index) => (
        <div
          key={row.code}
          ref={(node) => {
            if (node) nodes.current.set(row.code, node);
            else nodes.current.delete(row.code);
          }}
          className="grid grid-cols-[28px_4px_1fr_auto] items-center gap-2 border-t border-white/5 px-3 py-2"
        >
          <span className="font-extrabold tabular-nums text-[#d5dbea]">{index + 1}</span>
          <span className="h-7 rounded-sm" style={{ background: paint(row.color) }} />
          <span>
            <span className="block font-extrabold tracking-wide">{row.code}</span>
            <span className="block text-[11px] font-semibold text-[#8b95a8]">
              {row.retired ? "Retired" : `P${row.position} on track`}
            </span>
          </span>
          <span className="text-right tabular-nums">
            <span className="block text-base font-extrabold">{points(row.projected)}</span>
            <span className="block text-[11px] text-[#8b95a8]">
              {points(row.season)} + {points(row.racePoints)}
            </span>
          </span>
        </div>
      ))}
    </Panel>
  );
}

function Constructors({ rows }: { rows: ConstructorRow[] }) {
  const nodes = useFlip(rows.map((row) => row.name));
  return (
    <Panel title="CONSTRUCTORS BY POINTS">
      {rows.map((row, index) => (
        <div
          key={row.name}
          ref={(node) => {
            if (node) nodes.current.set(row.name, node);
            else nodes.current.delete(row.name);
          }}
          className="grid grid-cols-[22px_4px_1fr_auto] items-center gap-2 border-t border-white/5 px-3 py-2.5"
        >
          <span className="font-extrabold tabular-nums text-[#d5dbea]">{index + 1}</span>
          <span className="h-9 rounded-sm" style={{ background: paint(row.color) }} />
          <span>
            <span className="block font-extrabold">{row.name}</span>
            <span className="block text-[11px] font-semibold text-[#8b95a8]">
              {row.drivers.map((driver) => `${driver.code} ${points(driver.racePoints)}`).join(" + ")}
            </span>
          </span>
          <span className="text-right tabular-nums">
            <span className="block text-base font-extrabold">{points(row.projected)}</span>
            <span className="block text-[11px] text-[#8b95a8]">
              {points(row.season)} + {points(row.racePoints)}
            </span>
          </span>
        </div>
      ))}
    </Panel>
  );
}

function Track({
  track,
  cars,
}: {
  track: [number, number][];
  cars: { code: string; color: string; x: number; y: number }[];
}) {
  const line = track.map((point, index) => `${index === 0 ? "M" : "L"}${point[0]} ${point[1]}`).join(" ");
  return (
    <section className="relative min-h-[420px] overflow-hidden rounded-2xl border border-white/10 bg-[radial-gradient(closest-side_at_30%_40%,rgba(46,92,58,.55),transparent_70%),radial-gradient(closest-side_at_72%_62%,rgba(38,74,48,.4),transparent_72%),linear-gradient(180deg,#122016,#0c1612)]">
      <svg viewBox="0 0 100 100" className="h-full min-h-[420px] w-full" role="img" aria-label="Live circuit">
        {line && (
          <>
            <path d={line} fill="none" stroke="#15281c" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
            <path d={line} fill="none" stroke="#5c6574" strokeWidth="5.2" strokeLinecap="round" strokeLinejoin="round" />
            <path d={line} fill="none" stroke="#f7f8fb" strokeWidth="0.45" strokeDasharray="1.6 1.15" strokeLinecap="round" />
          </>
        )}
        {cars.map((car) => (
          <g key={car.code}>
            <circle cx={car.x} cy={car.y} r="1.35" fill={paint(car.color)} stroke="#07080d" strokeWidth="0.25" />
            <text x={car.x + 1.8} y={car.y + 0.7} fontSize="2.3" fontWeight="800" fill="#f4f6fb">
              {car.code}
            </text>
          </g>
        ))}
      </svg>
    </section>
  );
}

const pills: Record<string, string> = {
  live: "LIVE",
  replay: "REPLAY",
  preview: "PREVIEW",
  connecting: "CONNECTING",
  offline: "OFFLINE",
};

export default function Dashboard() {
  const race = useRace();
  const pill = pills[race.status] || race.status.toUpperCase();

  return (
    <main className="min-h-screen bg-[radial-gradient(1200px_500px_at_50%_-10%,#1a2436_0%,#07080c_55%)] p-3 text-[#f4f6fb] sm:p-4">
      <header className="mb-3 flex items-end justify-between gap-4 border-b border-[#e10600]/60 px-1 pb-3">
        <div>
          <p className="text-[11px] font-bold tracking-[0.22em] text-[#e10600]">CIRCUIT</p>
          <h1 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-[28px]">{race.session.trackName}</h1>
          <p className="mt-1 text-sm text-[#9aa3b5]">{race.session.location}</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-[#e10600]/50 bg-[#e10600]/10 px-3 py-1.5 text-xs font-bold tracking-[0.14em] text-[#ffb4b0]">
          <span className="h-2 w-2 rounded-full bg-[#e10600] shadow-[0_0_10px_#e10600]" />
          {pill}
        </div>
      </header>
      <div className="grid h-[calc(100vh-118px)] min-h-[640px] grid-cols-[188px_minmax(0,1fr)_268px] gap-3 max-[760px]:h-auto max-[760px]:grid-cols-1">
        <RaceOrder rows={race.raceOrder} />
        <Track track={race.track} cars={race.cars} />
        <div className="grid min-h-0 grid-rows-[1.35fr_1fr] gap-3 max-[760px]:min-h-[520px]">
          <Drivers rows={race.drivers} />
          <Constructors rows={race.constructors} />
        </div>
      </div>
    </main>
  );
}
