"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { FlowCycle } from "./FlowCycle";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface IterationData {
  number: number;
  role: "generator" | "critic" | "refiner";
  draft: string;
  score: number;
  feedback: string;
}

/* ------------------------------------------------------------------ */
/*  Static data                                                        */
/* ------------------------------------------------------------------ */

const ITERATIONS: IterationData[] = [
  {
    number: 1,
    role: "generator",
    draft:
      "Quantum entanglement is a phenomenon where two particles become correlated such that the quantum state of one particle instantaneously influences the state of the other, regardless of the distance separating them.",
    score: 0.45,
    feedback: "Too abstract, needs analogy. Uses jargon like 'correlated' and 'quantum state' that a 10-year-old won't understand.",
  },
  {
    number: 2,
    role: "refiner",
    draft:
      "Imagine you have two special socks that are always opposites. If one sock turns red, the other instantly turns blue \u2014 even if your friend took it to the moon! That\u2019s kind of how quantum entanglement works: two tiny particles are connected so that what happens to one affects the other, no matter how far apart they are.",
    score: 0.72,
    feedback: "Better! The sock analogy helps, but 'particles' is still a bit vague. Needs simpler words and a more playful tone.",
  },
  {
    number: 3,
    role: "refiner",
    draft:
      "Imagine you and your friend each have a magic dice. You can be anywhere in the whole universe \u2014 even on different planets! When you roll yours and get a 6, your friend\u2019s dice magically shows a 6 at the exact same moment. Nobody sent a message, nobody peeked \u2014 they\u2019re just connected like magic. Scientists call this 'quantum entanglement', and it\u2019s one of the coolest tricks in nature!",
    score: 0.91,
    feedback: "Excellent! Clear, engaging, and age-appropriate. The magic dice analogy is intuitive and the excited tone matches a 10-year-old\u2019s curiosity.",
  },
  {
    number: 4,
    role: "refiner",
    draft:
      "Imagine you and your best friend each have a magic dice. You could be on opposite sides of the Earth \u2014 or even different galaxies! When you roll yours and get a 6, your friend\u2019s dice instantly lands on 6 too. No phone call, no Wi-Fi, no trick \u2014 they just always match, like they\u2019re sharing a secret. Scientists discovered this real-life magic and named it 'quantum entanglement'. It\u2019s one of nature\u2019s most amazing surprises, and even grown-up scientists think it\u2019s wild!",
    score: 0.96,
    feedback: "Outstanding! Even more polished: relatable references (Wi-Fi, phone call), delightful closing, and perfectly tuned for a 10-year-old audience.",
  },
];

const TASK = "Explain quantum entanglement to a 10-year-old";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** A score is a number, not a colour: only a passing score takes the accent. */
function scoreColor(score: number, threshold: number): string {
  return score >= threshold ? "var(--accent)" : "var(--fg-3)";
}

function roleBadge(role: IterationData["role"]): {
  bg: string;
  text: string;
  label: string;
} {
  switch (role) {
    case "generator":
      return {
        bg: "transparent",
        text: "var(--accent-2)",
        label: "Generator",
      };
    case "critic":
      return {
        bg: "transparent",
        text: "var(--accent)",
        label: "Critic",
      };
    case "refiner":
      return {
        bg: "transparent",
        text: "var(--fg-2)",
        label: "Refiner",
      };
  }
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

/** Role badges row */
function RoleBadges() {
  const roles: IterationData["role"][] = ["generator", "critic", "refiner"];
  return (
    <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
      {roles.map((r) => {
        const b = roleBadge(r);
        return (
          <div
            key={r}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              background: b.bg,
              border: `1px solid ${b.text}33`,
              borderRadius: 999,
              padding: "0.25rem 0.7rem",
              fontSize: "11px",
              fontFamily: "var(--font-mono), monospace",
              fontWeight: 600,
              color: b.text,
            }}
          >
            {b.label}
          </div>
        );
      })}
    </div>
  );
}

/** Small sparkline SVG showing score progression */
function Sparkline({
  scores,
  threshold,
}: {
  scores: number[];
  threshold: number;
}) {
  if (scores.length === 0) return null;

  const w = 320;
  const h = 96;
  const padX = 24;
  const padY = 20;
  const innerW = w - padX * 2;
  const innerH = h - padY * 2;

  const points = scores.map((s, i) => ({
    x: padX + (scores.length === 1 ? innerW / 2 : (i / (scores.length - 1)) * innerW),
    y: padY + (1 - s) * innerH,
  }));

  const polyline = points.map((p) => `${p.x},${p.y}`).join(" ");
  const thresholdY = padY + (1 - threshold) * innerH;

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      style={{ width: w, height: h, display: "block" }}
    >
      {/* Threshold line */}
      <line
        x1={padX}
        y1={thresholdY}
        x2={w - padX}
        y2={thresholdY}
        stroke="var(--accent)"
        strokeWidth={1}
        strokeDasharray="4 3"
        opacity={0.6}
      />
      <text
        x={w - padX}
        y={thresholdY - 5}
        textAnchor="end"
        fill="var(--accent)"
        fontSize={11}
        fontFamily="var(--font-mono), monospace"
      >
        threshold {threshold.toFixed(2)}
      </text>

      {/* Score line */}
      <polyline
        fill="none"
        stroke="var(--fg-2)"
        strokeWidth={1.5}
        points={polyline}
        strokeLinejoin="round"
      />

      {/* Dots */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={3}
          fill={scoreColor(scores[i], threshold)}
        />
      ))}

      {/* Score labels */}
      {points.map((p, i) => (
        <text
          key={`lbl-${i}`}
          x={p.x}
          y={p.y - 7}
          textAnchor="middle"
          fill="var(--fg-2)"
          fontSize={11}
          fontFamily="var(--font-mono), monospace"
          fontWeight={600}
        >
          {scores[i].toFixed(2)}
        </text>
      ))}
    </svg>
  );
}

/** Arrow between iteration cards */
function IterationArrow() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        padding: "0.35rem 0",
        color: "var(--fg-2)",
        opacity: 0.5,
      }}
    >
      <svg
        width="20"
        height="24"
        viewBox="0 0 20 24"
        fill="none"
        style={{ display: "block" }}
      >
        <path
          d="M10 0 L10 18 M4 14 L10 20 L16 14"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

/** Single iteration card */
function IterationCard({
  iteration,
  threshold,
  animDelay,
}: {
  iteration: IterationData;
  threshold: number;
  animDelay: number;
}) {
  const meetsThreshold = iteration.score >= threshold;
  const badge = iteration.number === 1 ? roleBadge("generator") : roleBadge("refiner");
  const criticBadge = roleBadge("critic");
  const barWidth = Math.round(iteration.score * 100);

  return (
    <div
      className="animate-fade-in"
      style={{
        animationDelay: `${animDelay}ms`,
        background: meetsThreshold
          ? "rgba(76,195,138,0.04)"
          : "rgba(255,255,255,0.015)",
        border: meetsThreshold
          ? "1px solid rgba(76,195,138,0.25)"
          : "1px solid rgba(255,255,255,0.06)",
        borderRadius: 10,
        padding: "1rem",
        position: "relative",
        boxShadow: meetsThreshold
          ? "0 0 20px rgba(76,195,138,0.1), inset 0 0 20px rgba(76,195,138,0.03)"
          : "none",
        transition: "border-color 0.3s, box-shadow 0.3s, background 0.3s",
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.75rem",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "12px",
              fontWeight: 600,
              color: "var(--fg)",
            }}
          >
            Iteration {iteration.number}
          </span>
          <span
            style={{
              fontSize: "11px",
              fontFamily: "var(--font-mono), monospace",
              color: badge.text,
            }}
          >
            {badge.label}
          </span>
        </div>

        {/* Score pill */}
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "13px",
            fontWeight: 700,
            color: iteration.score >= threshold ? "var(--accent)" : "var(--fg-2)",
          }}
        >
          {iteration.score.toFixed(2)}
        </span>
      </div>

      {/* Draft text */}
      <div
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.05)",
          borderRadius: 8,
          padding: "0.7rem 0.85rem",
          marginBottom: "0.65rem",
          fontSize: "13px",
          lineHeight: 1.7,
          color: "var(--fg)",
        }}
      >
        {iteration.draft}
      </div>

      {/* Score bar with threshold */}
      <div style={{ marginBottom: "0.65rem" }}>
        <div
          style={{
            position: "relative",
            height: 4,
            background: "rgba(255,255,255,0.06)",
            borderRadius: 2,
            overflow: "visible",
          }}
        >
          {/* Filled bar */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              height: "100%",
              width: `${barWidth}%`,
              background:
                iteration.score >= threshold ? "var(--accent)" : "var(--fg-3)",
              borderRadius: 2,
              transition: "width 400ms var(--ease)",
            }}
          />
          {/* Threshold marker */}
          <div
            style={{
              position: "absolute",
              top: -4,
              left: `${Math.round(threshold * 100)}%`,
              width: 0,
              height: 12,
              borderLeft: "1px dashed var(--accent)",
              transform: "translateX(-1px)",
              opacity: 0.8,
            }}
          />
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 4,
            fontSize: "11px",
            fontFamily: "var(--font-mono), monospace",
            color: "var(--fg-2)",
          }}
        >
          <span>0.0</span>
          <span style={{ color: "var(--accent-2)", opacity: 0.8 }}>
            threshold: {threshold.toFixed(2)}
          </span>
          <span>1.0</span>
        </div>
      </div>

      {/* Critic feedback */}
      <div
        style={{
          borderTop: "1px solid var(--line)",
          paddingTop: 10,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
            marginBottom: "0.35rem",
          }}
        >
          <span
            style={{
              fontSize: "11px",
              fontFamily: "var(--font-mono), monospace",
              color: criticBadge.text,
            }}
          >
            Critique
          </span>
        </div>
        <div
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "12px",
            lineHeight: 1.6,
            color: "var(--fg-2)",
          }}
        >
          {iteration.feedback}
        </div>
      </div>

      {/* Passed badge */}
      {meetsThreshold && (
        <div
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            fontSize: "11px",
            fontFamily: "var(--font-mono), monospace",
            fontWeight: 700,
            color: "var(--accent)",
          }}
        >
          Passed
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Flow Diagram: Generator -> Critic -> Refiner                       */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/*  Main Widget                                                        */
/* ------------------------------------------------------------------ */

export function RefinementWidget() {
  const [threshold, setThreshold] = useState(0.8);
  const [running, setRunning] = useState(false);
  const [visibleIterations, setVisibleIterations] = useState(0);
  const [activeFlowStage, setActiveFlowStage] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Decide how many iterations to show based on threshold
  const needsExtraIteration = threshold > 0.91;
  const allIterations = needsExtraIteration ? ITERATIONS : ITERATIONS.slice(0, 3);
  const totalIterations = allIterations.length;

  useEffect(() => {
    setMounted(true);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const reset = useCallback(() => {
    setVisibleIterations(0);
    setRunning(false);
    setActiveFlowStage(null);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const runRefinement = useCallback(() => {
    if (running) return;
    reset();
    setRunning(true);

    let step = 0;

    function tick() {
      if (step >= totalIterations) {
        setRunning(false);
        setActiveFlowStage(null);
        return;
      }

      const iter = allIterations[step];

      // Animate role stages
      if (step === 0) {
        setActiveFlowStage("generator");
      } else {
        setActiveFlowStage("refiner");
      }

      timerRef.current = setTimeout(() => {
        setVisibleIterations(step + 1);
        setActiveFlowStage("critic");

        timerRef.current = setTimeout(() => {
          // Check if this iteration passes threshold
          if (iter.score >= threshold) {
            setActiveFlowStage(null);
            step = totalIterations; // Done
            timerRef.current = setTimeout(() => {
              setRunning(false);
            }, 400);
          } else {
            step++;
            timerRef.current = setTimeout(tick, 300);
          }
        }, 700);
      }, 700);
    }

    timerRef.current = setTimeout(tick, 300);
  }, [running, totalIterations, allIterations, threshold, reset]);

  const handleThresholdChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (running) return;
      setThreshold(parseFloat(e.target.value));
      reset();
    },
    [running, reset]
  );

  // Determine which iterations are visible and what scores to show in sparkline
  const visibleIters = allIterations.slice(0, visibleIterations);
  const visibleScores = visibleIters.map((it) => it.score);

  // Find the first iteration that meets threshold (for the completion message)
  const passedIter = visibleIters.find((it) => it.score >= threshold);

  if (!mounted) {
    return (
      <div className="widget-shell">
        <div style={{ minHeight: 160 }} />
      </div>
    );
  }

  return (
    <div className="widget-shell">

      {/* Task prompt */}
      <div
        style={{
          background: "rgba(125,148,171,0.06)",
          border: "1px solid rgba(125,148,171,0.15)",
          borderRadius: 8,
          padding: "0.75rem 1rem",
          marginBottom: "1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <span
          style={{
            fontSize: "11px",
            fontFamily: "var(--font-mono), monospace",
            fontWeight: 600,
            color: "var(--accent-2)",
            whiteSpace: "nowrap",
          }}
        >
          Task
        </span>
        <span
          style={{
            fontSize: "14px",
            color: "var(--fg)",
            lineHeight: 1.5,
          }}
        >
          {TASK}
        </span>
      </div>

      {/* Role badges */}
      <div style={{ marginBottom: "1.25rem" }}>
        <RoleBadges />
      </div>

      {/* Flow diagram + controls */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "1rem",
          marginBottom: "1.25rem",
        }}
      >
        <FlowCycle
          markerId="arrowRW"
          activeStage={activeFlowStage}
          note="until score clears the threshold"
          stages={[
            { id: "generator", label: "Generator" },
            { id: "critic", label: "Critic" },
            { id: "refiner", label: "Refiner" },
          ]}
        />

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 16,
            flex: 1,
            minWidth: 240,
            maxWidth: 420,
          }}
        >
          {/* Threshold slider */}
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "0.4rem",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "12px",
                  color: "var(--fg-2)",
                }}
              >
                Score Threshold
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "12px",
                  color: "var(--fg)",
                }}
              >
                {threshold.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={0.5}
              max={1.0}
              step={0.01}
              value={threshold}
              onChange={handleThresholdChange}
              disabled={running}
              style={{ opacity: running ? 0.5 : 1 }}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "11px",
                fontFamily: "var(--font-mono), monospace",
                color: "var(--fg-2)",
                marginTop: 2,
              }}
            >
              <span>0.50</span>
              <span>1.00</span>
            </div>
          </div>

          {/* Run button */}
          <button
            className="btn-mono"
            onClick={runRefinement}
            disabled={running}
            style={{
              opacity: running ? 0.5 : 1,
              cursor: running ? "not-allowed" : "pointer",
              borderColor: running ? "var(--line)" : "var(--accent)",
              color: running ? "var(--fg-3)" : "var(--accent)",
              maxWidth: 200,
            }}
          >
            {running ? "Refining..." : "Run Refinement"}
          </button>

        </div>
      </div>

      {/* Iteration cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        {visibleIterations === 0 && !running && (
          <div
            style={{
              textAlign: "center",
              padding: "2rem 1rem",
              color: "var(--fg-2)",
              fontFamily: "var(--font-mono), monospace",
              fontSize: "12px",
              opacity: 0.6,
            }}
          >
            Press &ldquo;Run Refinement&rdquo; to start the Generator &rarr;
            Critic &rarr; Refiner loop
          </div>
        )}

        {visibleIters.map((iter, i) => (
          <div key={`iter-${iter.number}`}>
            {i > 0 && <IterationArrow />}
            <IterationCard
              iteration={iter}
              threshold={threshold}
              animDelay={0}
            />
          </div>
        ))}
      </div>

      {/* Score trend */}
      {visibleScores.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <span className="field-label">Score trend</span>
          <div className="panel" style={{ display: "inline-block", padding: "8px 12px" }}>
            <Sparkline scores={visibleScores} threshold={threshold} />
          </div>
        </div>
      )}

      {/* Completion footer */}
      {passedIter && !running && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: 16,
            padding: "12px 16px",
            border: "1px solid var(--line)",
            borderRadius: 8,
            fontFamily: "var(--font-mono), monospace",
            fontSize: "12px",
            color: "var(--fg-2)",
            textAlign: "center",
          }}
        >
          Refinement complete &mdash; score {passedIter.score.toFixed(2)}{" "}
          {"\u2265"} threshold {threshold.toFixed(2)} after{" "}
          {passedIter.number} iteration
          {passedIter.number > 1 ? "s" : ""}
        </div>
      )}

      {/* All iterations exhausted without passing */}
      {visibleIterations === totalIterations &&
        !running &&
        !passedIter &&
        visibleIterations > 0 && (
          <div
            className="animate-fade-in"
            style={{
              marginTop: "1rem",
              padding: "0.75rem 1rem",
              background: "rgba(229,72,77,0.04)",
              border: "1px solid rgba(229,72,77,0.12)",
              borderRadius: 8,
              fontFamily: "var(--font-mono), monospace",
              fontSize: "12px",
              color: "var(--negative)",
              textAlign: "center",
            }}
          >
            Threshold {threshold.toFixed(2)} not reached after{" "}
            {totalIterations} iterations &mdash; best score:{" "}
            {Math.max(...visibleScores).toFixed(2)}
          </div>
        )}
    </div>
  );
}
