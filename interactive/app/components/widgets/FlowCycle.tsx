/**
 * Three stages in a row with a return arrow: the repeating loop that most
 * reasoning strategies are built from. Active stage takes the accent, the
 * others stay neutral.
 */
export function FlowCycle({
  stages,
  activeStage,
  note,
  markerId,
}: {
  stages: { id: string; label: string }[];
  activeStage: string | null;
  note: string;
  markerId: string;
}) {
  const boxW = 84;
  const boxH = 28;
  const gap = 30;
  const top = 22;
  const width = stages.length * boxW + (stages.length - 1) * gap;

  return (
    <svg
      viewBox={`0 0 ${width} ${top + boxH + 46}`}
      style={{ width: width, height: top + boxH + 46, display: "block", flexShrink: 0 }}
      role="img"
      aria-label={`${stages.map((s) => s.label).join(" to ")}, repeating`}
    >
      <defs>
        <marker
          id={markerId}
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="5"
          markerHeight="5"
          orient="auto-start-reverse"
        >
          <path d="M 0 1 L 8 5 L 0 9 z" fill="var(--fg-3)" />
        </marker>
      </defs>

      {stages.map((stage, i) => {
        const x = i * (boxW + gap);
        const isActive = activeStage === stage.id;
        return (
          <g key={stage.id}>
            {i > 0 && (
              <line
                x1={x - gap + 2}
                y1={top + boxH / 2}
                x2={x - 6}
                y2={top + boxH / 2}
                stroke="var(--fg-4)"
                strokeWidth={1}
                markerEnd={`url(#${markerId})`}
              />
            )}
            <rect
              x={x}
              y={top}
              width={boxW}
              height={boxH}
              rx={6}
              fill={isActive ? "rgba(224,162,83,0.08)" : "transparent"}
              stroke={isActive ? "var(--accent)" : "var(--line)"}
              strokeWidth={1}
            />
            <text
              x={x + boxW / 2}
              y={top + boxH / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              fill={isActive ? "var(--accent)" : "var(--fg-2)"}
              fontSize={11}
              fontFamily="var(--font-mono), monospace"
            >
              {stage.label}
            </text>
          </g>
        );
      })}

      {/* return arrow: the loop closes */}
      <path
        d={`M ${width - 6} ${top + boxH} L ${width - 6} ${top + boxH + 24} L 6 ${top + boxH + 24} L 6 ${top + boxH + 6}`}
        fill="none"
        stroke="var(--fg-4)"
        strokeWidth={1}
        markerEnd={`url(#${markerId})`}
      />
      <text
        x={width / 2}
        y={top + boxH + 18}
        textAnchor="middle"
        fill="var(--fg-3)"
        fontSize={11}
        fontFamily="var(--font-mono), monospace"
      >
        {note}
      </text>
    </svg>
  );
}
