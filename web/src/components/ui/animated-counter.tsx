"use client"

import * as React from "react"

import { MotionValue, m, useSpring, useTransform } from "motion/react";
import { useEffect, useState } from "react";
import { twMerge } from "tailwind-merge";
import clsx from "clsx";

const cn = (...args: any[]) => {
  return twMerge(clsx(args));
};

const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;
const fontSize = 40;
const padding = 10;
const height = fontSize + padding;

interface CounterProps
  extends React.DetailedHTMLProps<
    React.HTMLAttributes<HTMLParagraphElement>,
    HTMLParagraphElement
  > {
  start?: number;
  end: number;
  duration?: number;
  className?: string;
  fontSize?: number;
}

export const Counter = ({
  start = 0,
  end,
  duration = end,
  className,
  fontSize = 30,
  ...rest
}: CounterProps) => {
  // Initial value derived from prop — counter only increments from here, never re-syncs
  const [value, setValue] = useState(() => start);

  useEffect(() => {
    const interval = setInterval(() => {
      if (value < end) {
        setValue((prev) => prev + 1);
      }
    }, (duration / (end - start)) * 1000);

    return () => clearInterval(interval);
  }, [value]);

  return (
    <div
      style={{ fontSize }}
      {...rest}
      className={cn(
        "flex overflow-hidden rounded px-2 leading-none text-primary font-bold ",
        className
      )}
    >
      {value >= 100000 && <Digit place={100000} value={value} />}
      {value >= 10000 && <Digit place={10000} value={value} />}
      {value >= 1000 && <Digit place={1000} value={value} />}
      {value >= 100 && <Digit place={100} value={value} />}
      {value >= 10 && <Digit place={10} value={value} />}
      <Digit place={1} value={value} />
    </div>
  );
};

function Digit({ place, value }: { place: number; value: number }) {
  let valueRoundedToPlace = Math.floor(value / place);
  let animatedValue = useSpring(valueRoundedToPlace);

  useEffect(() => {
    animatedValue.set(valueRoundedToPlace);
  }, [animatedValue, valueRoundedToPlace]);

  return (
    <div style={{ height }} className="relative w-[1ch] tabular-nums">
      {DIGITS.map((digit) => (
        <Number key={digit} mv={animatedValue} number={digit} />
      ))}
    </div>
  );
}

function Number({ mv, number }: { mv: MotionValue; number: number }) {
  let y = useTransform(mv, (latest) => {
    let placeValue = latest % 10;
    let offset = (10 + number - placeValue) % 10;

    let memo = offset * height;

    if (offset > 5) {
      memo -= 10 * height;
    }

    return memo;
  });

  return (
    <m.span
      style={{ y }}
      className="absolute inset-0 flex items-center justify-center"
    >
      {number}
    </m.span>
  );
}
