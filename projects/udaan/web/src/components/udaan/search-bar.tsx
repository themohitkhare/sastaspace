"use client";

import type { ChangeEvent, FormEvent } from "react";
import { AIRPORTS } from "@/lib/udaan/airports";

export type SearchValue = {
  from: string;
  to: string;
  date: string;
};

type Props = {
  value: SearchValue;
  onChange?: (next: SearchValue) => void;
  onSubmit?: () => void;
};

export function SearchBar({ value, onChange, onSubmit }: Props) {
  const update = (patch: Partial<SearchValue>) => {
    onChange?.({ ...value, ...patch });
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit?.();
  };

  return (
    <form className="search" aria-label="find your flight" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="from">From</label>
        <select
          id="from"
          className="control"
          value={value.from}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => update({ from: e.target.value })}
        >
          {AIRPORTS.map((a) => (
            <option key={a.code} value={a.code}>
              {a.city} ({a.code})
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="to">To</label>
        <select
          id="to"
          className="control"
          value={value.to}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => update({ to: e.target.value })}
        >
          {AIRPORTS.map((a) => (
            <option key={a.code} value={a.code}>
              {a.city} ({a.code})
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="date">Date</label>
        <input
          id="date"
          className="control"
          type="date"
          value={value.date}
          onChange={(e: ChangeEvent<HTMLInputElement>) => update({ date: e.target.value })}
        />
      </div>
      <button className="btn-primary" type="submit">
        check risk →
      </button>
    </form>
  );
}
