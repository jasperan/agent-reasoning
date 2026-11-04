"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface Step {
  label: string;
  text: string;
}

interface Problem {
  id: string;
  title: string;
  question: string;
  steps: Step[];
  directAnswer: string;
  directCorrect: boolean;
}

const PROBLEMS: Problem[] = [
  {
    id: "fruits",
    title: "Fruit Boxes",
    question:
      "If a store has 3 boxes with 12 apples each, and 2 boxes with 8 oranges each, how many total fruits are there?",
    steps: [
      { label: "Step 1", text: "Calculate apples: 3 boxes \u00d7 12 apples = 36 apples" },
      { label: "Step 2", text: "Calculate oranges: 2 boxes \u00d7 8 oranges = 16 oranges" },
      { label: "Step 3", text: "Add totals: 36 + 16 = 52 fruits" },
      { label: "Step 4", text: "Final Answer: 52 fruits" },
    ],
    directAnswer: "48 fruits",
    directCorrect: false,
  },
  {
    id: "trains",
    title: "Train Problem",
    question:
      "Two trains leave stations 300 km apart, heading toward each other at 60 km/h and 90 km/h. How long until they meet?",
    steps: [
      { label: "Step 1", text: "Combined speed: 60 + 90 = 150 km/h" },
      { label: "Step 2", text: "Time = Distance \u00f7 Speed = 300 \u00f7 150" },
      { label: "Step 3", text: "300 \u00f7 150 = 2 hours" },
      { label: "Step 4", text: "Final Answer: 2 hours" },
    ],
    directAnswer: "3 hours",
    directCorrect: false,
  },
  {
    id: "discount",
    title: "Compound Discount",
    question:
      "A jacket costs $120. It\u2019s 25% off, then an extra 10% off the sale price. What is the final price?",
    steps: [
      { label: "Step 1", text: "First discount: $120 \u00d7 0.25 = $30 off \u2192 $90" },
      { label: "Step 2", text: "Second discount: $90 \u00d7 0.10 = $9 off" },
      { label: "Step 3", text: "Final price: $90 \u2212 $9 = $81" },
      { label: "Step 4", text: "Final Answer: $81" },
    ],
    directAnswer: "$78",
    directCorrect: false,
  },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function CoTChainWidget() {
  /* --- State ------------------------------------------------------ */
  const [problemIdx, setProblemIdx] = useState(0);
  const [visibleSteps, setVisibleSteps] = useState(PROBLEMS[0].steps.length);
  const [isRunning, setIsRunning] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const problem = PROBLEMS[problemIdx];
  const totalSteps = problem.steps.length;

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
  }, [clearTimer]);

  const revealNext = useCallback(() => {
    setVisibleSteps((prev) => {
      const next = prev + 1;
      if (next >= totalSteps) {
        setIsRunning(false);
        return next;
      }
      /* schedule the following step */
      timerRef.current = setTimeout(() => revealNext(), 500);
      return next;
    });
  }, [totalSteps]);

  const runCoT = useCallback(() => {
    reset();
    setIsRunning(true);
    /* kick off the first reveal after a brief pause */
    timerRef.current = setTimeout(() => revealNext(), 350);
  }, [reset, revealNext]);

  /* Auto-play on problem change */
  useEffect(() => {
    if (autoPlay) {
      runCoT();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problemIdx, autoPlay]);

  /* Cleanup on unmount */
  useEffect(() => clearTimer, [clearTimer]);

  const handleProblemSwitch = useCallback(
    (idx: number) => {
      if (idx === problemIdx) return;
      clearTimer();
      setVisibleSteps(0);
      setIsRunning(false);
        setProblemIdx(idx);
    },
    [problemIdx, clearTimer],
  );

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-shell">
      {/* ---- Problem selector ---- */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        {PROBLEMS.map((p, i) => (
          <button
            key={p.id}
            onClick={() => handleProblemSwitch(i)}
            className={`btn-mono ${i === problemIdx ? "active" : ""}`}
          >
            {p.title}
          </button>
        ))}
      </div>

      {/* ---- Question ---- */}
      <div className="panel mb-6 px-4 py-3">
        <span className="field-label">Problem</span>
        <p style={{ color: "var(--fg)", margin: 0, fontSize: "14px", lineHeight: 1.6 }}>
          {problem.question}
        </p>
      </div>

      {/* ---- Controls ---- */}
      <div className="mb-6 flex flex-wrap items-center gap-2">
        <button className="btn-mono active" onClick={runCoT} disabled={isRunning}>
          {isRunning ? "Running\u2026" : "Run CoT"}
        </button>
        <button className="btn-mono" onClick={reset}>
          Reset
        </button>
        <button
          className={`btn-mono ml-1 ${autoPlay ? "active" : ""}`}
          aria-pressed={autoPlay}
          onClick={() => setAutoPlay((v) => !v)}
        >
          {autoPlay ? "Auto play on" : "Auto play off"}
        </button>
      </div>

      {/* ---- Chain, one numbered row per step ---- */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_220px]">
        <div>
          <div className="mb-1 flex items-baseline justify-between">
            <span className="field-label mb-0">Chain of thought</span>
            <span className="seq">
              {visibleSteps}/{totalSteps}
            </span>
          </div>
          <ol>
            {problem.steps.map((step, i) => {
              const visible = i < visibleSteps;
              const isFinal = i === totalSteps - 1;
              return (
                <li
                  key={`${problem.id}-${i}`}
                  className="flex gap-3 border-t py-3"
                  style={{
                    borderColor: "var(--line)",
                    opacity: visible ? 1 : 0.3,
                    transition: "opacity 240ms var(--ease)",
                  }}
                >
                  <span className="seq w-6 shrink-0 tabular-nums">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono), monospace",
                      fontSize: "13px",
                      lineHeight: "20px",
                      color: isFinal
                        ? "var(--accent)"
                        : visible
                        ? "var(--fg-2)"
                        : "var(--fg-4)",
                    }}
                  >
                    {step.text}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>

        {/* ---- Same question, answered without the chain ---- */}
        <div>
          <span className="field-label">Direct answer</span>
          <div className="panel px-3 py-3">
            <p
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "13px",
                color: "var(--fg)",
                margin: 0,
                lineHeight: "20px",
              }}
            >
              {problem.directAnswer}
            </p>
            <span
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "11px",
                color: "var(--negative)",
              }}
            >
              incorrect
            </span>
          </div>
          <p style={{ marginTop: 12, fontSize: "12px", lineHeight: 1.6, color: "var(--fg-3)" }}>
            Without step-by-step reasoning the model jumps straight to an
            answer and drops the second box count.
          </p>
        </div>
      </div>
    </div>
  );
}
