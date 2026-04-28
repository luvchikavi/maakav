"use client";

import { forwardRef, InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type"> & {
  value: string | number | null | undefined;
  onChange: (value: string) => void;
  decimals?: number;
};

const formatWithCommas = (raw: string, decimals: number): string => {
  if (raw === "" || raw === "-") return raw;
  const negative = raw.startsWith("-");
  const cleaned = raw.replace(/[^0-9.]/g, "");
  if (cleaned === "" || cleaned === ".") return negative ? "-" : "";
  const parts = cleaned.split(".");
  const intPart = parts[0].replace(/^0+(?=\d)/, "") || "0";
  const withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  let result = withCommas;
  if (parts.length > 1) {
    const decPart = parts.slice(1).join("").slice(0, decimals);
    result = `${withCommas}.${decPart}`;
  }
  return negative ? `-${result}` : result;
};

const stripCommas = (formatted: string): string => formatted.replace(/,/g, "");

const NumberInput = forwardRef<HTMLInputElement, Props>(function NumberInput(
  { value, onChange, decimals = 2, className = "", ...rest },
  ref,
) {
  const display = value === null || value === undefined || value === ""
    ? ""
    : formatWithCommas(String(value), decimals);

  return (
    <input
      ref={ref}
      type="text"
      inputMode="decimal"
      dir="ltr"
      value={display}
      onChange={(e) => {
        const raw = stripCommas(e.target.value);
        if (raw === "" || raw === "-" || /^-?\d*\.?\d*$/.test(raw)) {
          onChange(raw);
        }
      }}
      className={className}
      {...rest}
    />
  );
});

export default NumberInput;
