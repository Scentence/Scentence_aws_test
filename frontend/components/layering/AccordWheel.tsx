"use client";

import { ACCORD_COLORS, BACKEND_ACCORDS, DISPLAY_ACCORDS } from "@/lib/accords";

type AccordWheelProps = {
  vector: number[];
  size?: number;
};

type Point = {
  x: number;
  y: number;
};

const DEFAULT_SIZE = 360;
const OUTER_RADIUS = 170;
const INNER_RADIUS_MAX = 135;
const INNER_RADIUS_MIN = 70;

const polarToCartesian = (cx: number, cy: number, radius: number, angle: number): Point => {
  const radians = ((angle - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  };
};

const arcPath = (
  cx: number,
  cy: number,
  startAngle: number,
  endAngle: number,
  innerRadius: number,
  outerRadius: number,
): string => {
  const startOuter = polarToCartesian(cx, cy, outerRadius, startAngle);
  const endOuter = polarToCartesian(cx, cy, outerRadius, endAngle);
  const startInner = polarToCartesian(cx, cy, innerRadius, endAngle);
  const endInner = polarToCartesian(cx, cy, innerRadius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

  return [
    `M ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${startInner.x} ${startInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${endInner.x} ${endInner.y}`,
    "Z",
  ].join(" ");
};

export default function AccordWheel({ vector, size = DEFAULT_SIZE }: AccordWheelProps) {
  const safeVector = Array.isArray(vector) ? vector : [];
  const maxValue = Math.max(...safeVector, 0);
  const viewBox = `0 0 ${size} ${size}`;
  const cx = size / 2;
  const cy = size / 2;
  const segmentAngle = 360 / DISPLAY_ACCORDS.length;
  const backendIndex = new Map(
    BACKEND_ACCORDS.map((accord, index) => [accord, index]),
  );

  return (
    <svg viewBox={viewBox} width={size} height={size} aria-label="Accord wheel">
      {DISPLAY_ACCORDS.map((accord, index) => {
        const vectorIndex = backendIndex.get(accord) ?? index;
        const rawValue = safeVector[vectorIndex] ?? 0;
        const normalized = maxValue > 0 ? Math.min(rawValue / maxValue, 1) : 0;
        const innerRadius =
          INNER_RADIUS_MAX - (INNER_RADIUS_MAX - INNER_RADIUS_MIN) * normalized;
        const opacity = 0.25 + normalized * 0.75;
        const startAngle = index * segmentAngle;
        const endAngle = startAngle + segmentAngle;
        const path = arcPath(cx, cy, startAngle, endAngle, innerRadius, OUTER_RADIUS);

        return (
          <path
            key={accord}
            d={path}
            fill={ACCORD_COLORS[accord]}
            fillOpacity={opacity}
            stroke="rgba(255,255,255,0.6)"
            strokeWidth={2}
          />
        );
      })}
      <circle cx={cx} cy={cy} r={55} fill="#FDFDFB" stroke="#E4E0D4" />
      <text
        x={cx}
        y={cy - 4}
        textAnchor="middle"
        fill="#2B2B2B"
        fontSize="16"
        fontWeight={600}
      >
        SCENTENCE
      </text>
      <text
        x={cx}
        y={cy + 16}
        textAnchor="middle"
        fill="#7B7B7B"
        fontSize="11"
        letterSpacing="0.12em"
      >
        ACCORDS
      </text>
    </svg>
  );
}
