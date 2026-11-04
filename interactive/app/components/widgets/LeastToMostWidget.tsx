"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface SubProblem {
  level: number;
  difficulty: "Easy" | "Medium" | "Hard" | "Hardest";
  question: string;
  answer: string;
}

const PROBLEM =
  "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?";

const SUB_PROBLEMS: SubProblem[] = [
  {
    level: 1,
    difficulty: "Easy",
    question: "How many widgets does 1 machine make in 5 minutes?",
    answer: "1 widget",
  },
  {
    level: 2,
    difficulty: "Medium",
    question: "What is the rate per machine?",
    answer: "1 widget per 5 minutes",
  },
  {
    level: 3,
    difficulty: "Hard",
    question: "How many widgets do 100 machines make in 5 minutes?",
    answer: "100 widgets",
  },
  {
    level: 4,
    difficulty: "Hardest",
    question: "So how long for 100 machines to make 100 widgets?",
    answer: "5 minutes",
  },
];

/* ------------------------------------------------------------------ */
/*  Color helpers                                                      */
/* ------------------------------------------------------------------ */

/** One hue for the whole staircase: only the final answer takes the accent. */
function stepColor(level: number): { text: string } {
  return { text: level > 1 ? "var(--fg-2)" : "var(--fg-3)" };
}

function difficultyBadge(difficulty: SubProblem["difficulty"]): {
  color: string;
} {
  switch (difficulty) {
    case "Easy":
    case "Medium":
      return { color: "var(--fg-3)" };
    default:
      return { color: "var(--fg-2)" };
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function LeastToMostWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [visibleSteps, setVisibleSteps] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const totalSteps = SUB_PROBLEMS.length;

  /* --- Helpers ---------------------------------------------------- */
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearTimer();
    setVisibleSteps(0);
    setIsRunning(false);
    setShowComparison(false);
  }, [clearTimer]);

  const revealNext = useCallback(() => {
    setVisibleSteps((prev) => {
      const next = prev + 1;
      if (next >= totalSteps) {
        setIsRunning(false);
        setShowComparison(true);
        return next;
      }
      timerRef.current = setTimeout(() => revealNext(), 500);
      return next;
    });
  }, [totalSteps]);

  const solve = useCallback(() => {
    reset();
    setIsRunning(true);
    timerRef.current = setTimeout(() => revealNext(), 350);
  }, [reset, revealNext]);

  /* Cleanup on unmount */
  useEffect(() => clearTimer, [clearTimer]);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-shell">

      {/* ---- Problem ---- */}
      <div
        className="rounded-lg p-4 mb-6"
        style={{
          background: "rgba(125,148,171,0.06)",
          border: "1px solid rgba(125,148,171,0.15)",
        }}
      >
        <span
          className="block mb-1"
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "12px",
            color: "var(--accent-2)",
            fontWeight: 600,
          }}
        >
          Problem
        </span>
        <p style={{ color: "var(--fg)", margin: 0, lineHeight: 1.7 }}>
          {PROBLEM}
        </p>
      </div>

      {/* ---- Approach label ---- */}
      <div
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "12px",
          color: "var(--fg-2)",
          marginBottom: "0.5rem",
        }}
      >
        Decompose: easy &rarr; hard, solve progressively
      </div>

      {/* ---- Controls ---- */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          className="btn-mono"
          onClick={solve}
          disabled={isRunning}
          style={{
            background: isRunning ? "transparent" : "rgba(125,148,171,0.12)",
            borderColor: isRunning
              ? "rgba(255,255,255,0.08)"
              : "rgba(125,148,171,0.35)",
            color: isRunning ? "var(--fg-2)" : "var(--accent-2)",
            cursor: isRunning ? "not-allowed" : "pointer",
          }}
        >
          {isRunning ? "Solving\u2026" : "Solve"}
        </button>

        <button className="btn-mono" onClick={reset}>
          Reset
        </button>

        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "12px",
            color: "var(--fg-2)",
          }}
        >
          {visibleSteps}/{totalSteps} sub-problems
        </span>
      </div>

      {/* ---- Staircase visualization ---- */}
      <div
        style={{
          position: "relative",
        }}
      >
        {/* Placeholder when idle */}
        {visibleSteps === 0 && !isRunning && (
          <div
            className="flex items-baseline gap-3 border-t py-3"
            style={{ borderColor: "var(--line)" }}
          >
            <span className="seq w-6 shrink-0">—</span>
            <span
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "12px",
                color: "var(--fg-3)",
              }}
            >
              Press &ldquo;Solve&rdquo; to decompose and solve step by step
            </span>
          </div>
        )}

        {/* Vertical staircase layout: each step indented further right */}
        {(visibleSteps > 0 || isRunning) && (
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {SUB_PROBLEMS.map((sub, i) => {
              const visible = i < visibleSteps;
              const colors = stepColor(sub.level);
              const badge = difficultyBadge(sub.difficulty);
              const isFinal = i === totalSteps - 1;

              return (
                <div key={`step-${i}`}>
                  {/* Step card */}
                  <div
                    className={visible ? "animate-fade-in" : ""}
                    style={{
                      opacity: visible ? 1 : 0,
                      transform: visible
                        ? "translateY(0)"
                        : "translateY(16px)",
                      transition:
                        "opacity 0.45s ease-out, transform 0.45s ease-out",
                      marginLeft: i * 24,
                      background: "transparent",
                      border: `1px solid ${
                        isFinal && visible ? "var(--line-strong)" : "var(--line)"
                      }`,
                      borderRadius: 8,
                      padding: "12px 16px",
                      position: "relative",
                    }}
                  >
                    {/* Top row: level + difficulty badge */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 6,
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--font-mono), monospace",
                          fontSize: "11px",
                          color: colors.text,
                          fontWeight: 600,
                        }}
                      >
                        Level {sub.level}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          fontFamily: "var(--font-mono), monospace",
                          color: badge.color,
                        }}
                      >
                        {sub.difficulty}
                      </span>
                    </div>

                    {/* Sub-question */}
                    <p
                      style={{
                        color: "var(--fg)",
                        margin: "0 0 4px",
                        fontSize: "13px",
                        lineHeight: 1.55,
                      }}
                    >
                      {sub.question}
                    </p>

                    {/* Answer */}
                    {visible && (
                      <div
                        className="animate-fade-in"
                        style={{
                          display: "flex",
                          alignItems: "baseline",
                          gap: 6,
                          marginTop: 6,
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "var(--font-mono), monospace",
                            fontSize: "12px",
                            color: "var(--fg-2)",
                            fontWeight: 600,
                          }}
                        >
                          &rarr;
                        </span>
                        <span
                          style={{
                            fontFamily: "var(--font-mono), monospace",
                            fontSize: "13px",
                            color: isFinal ? "var(--accent)" : "var(--fg)",
                          }}
                        >
                          {sub.answer}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Arrow connector between steps */}
                  {i < totalSteps - 1 && (
                    <div
                      style={{
                        marginLeft: i * 24 + 20,
                        height: 28,
                        opacity: visible ? 1 : 0,
                        transition: "opacity 0.3s",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      {mounted && (
                        <>
                          <svg
                            width="20"
                            height="28"
                            viewBox="0 0 20 28"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            {/* Diagonal arrow going down-right to mimic staircase */}
                            <line
                              x1="4"
                              y1="2"
                              x2="16"
                              y2="18"
                              stroke={stepColor(sub.level).text}
                              strokeWidth="1.5"
                              opacity={0.5}
                            />
                            <path
                              d="M12 15 L16 20 L10 18"
                              stroke={stepColor(sub.level + 1).text}
                              strokeWidth="1.5"
                              fill="none"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              opacity={0.6}
                            />
                          </svg>
                          <span
                            style={{
                              fontFamily: "var(--font-mono), monospace",
                              fontSize: "11px",
                              color: "var(--fg-2)",
                              opacity: 0.5,
                            }}
                          >
                            feeds into
                          </span>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ---- Progress bar ---- */}
      <div className="mt-6 flex items-center gap-3">
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "12px",
            color: "var(--fg-2)",
          }}
        >
          {visibleSteps}/{totalSteps}
        </span>
        <div
          style={{
            flex: 1,
            height: 4,
            borderRadius: 2,
            background: "rgba(255,255,255,0.06)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${(visibleSteps / totalSteps) * 100}%`,
              height: "100%",
              borderRadius: 2,
              background:
                visibleSteps === totalSteps
                  ? "var(--accent-2)"
                  : "rgba(125,148,171,0.5)",
              transition: "width 0.35s ease-out",
            }}
          />
        </div>
      </div>

      {/* ---- Comparison note (wrong answer) ---- */}
      {showComparison && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: "1rem",
            display: "flex",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          {/* Correct answer highlight */}
          <div
            style={{
              flex: 1,
              minWidth: 200,
              padding: "0.75rem 1rem",
              background: "rgba(76,195,138,0.04)",
              border: "1px solid rgba(76,195,138,0.15)",
              borderRadius: 8,
            }}
          >
            <span
              style={{
                display: "block",
                fontFamily: "var(--font-mono), monospace",
                fontSize: "11px",
                color: "var(--positive)",
                fontWeight: 600,
                marginBottom: 4,
              }}
            >
              &#10003; Least-to-Most Answer
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "13px",
                color: "var(--fg)",
                fontWeight: 600,
              }}
            >
              5 minutes
            </span>
            <p
              style={{
                margin: "6px 0 0",
                fontSize: "12px",
                color: "var(--fg-2)",
                lineHeight: 1.55,
              }}
            >
              Each machine independently makes 1 widget in 5 minutes. With 100
              machines working in parallel, 100 widgets are produced in the same
              5 minutes.
            </p>
          </div>

          {/* Wrong answer */}
          <div
            style={{
              flex: 1,
              minWidth: 200,
              padding: "0.75rem 1rem",
              background: "rgba(229,72,77,0.04)",
              border: "1px solid rgba(229,72,77,0.15)",
              borderRadius: 8,
            }}
          >
            <span
              style={{
                display: "block",
                fontFamily: "var(--font-mono), monospace",
                fontSize: "11px",
                color: "var(--negative)",
                fontWeight: 600,
                marginBottom: 4,
              }}
            >
              &#10007; Common Wrong Answer
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "13px",
                color: "var(--fg)",
                fontWeight: 600,
              }}
            >
              100 minutes
            </span>
            <p
              style={{
                margin: "6px 0 0",
                fontSize: "12px",
                color: "var(--fg-2)",
                lineHeight: 1.55,
              }}
            >
              Linear scaling fallacy &mdash; assuming time scales linearly
              with quantity, ignoring that machines work in parallel.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
