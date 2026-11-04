"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { FlowCycle } from "./FlowCycle";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Phase {
  type: "draft" | "critique" | "improvement";
  text: string;
}

interface Iteration {
  number: number;
  phases: Phase[];
  status: "pending" | "needs_improvement" | "correct";
  critique: string;
}

interface Prompt {
  label: string;
  iterations: Iteration[];
}

/* ------------------------------------------------------------------ */
/*  Static data - all prompts and their pre-baked iterations           */
/* ------------------------------------------------------------------ */

const PROMPTS: Prompt[] = [
  {
    label: "Write a haiku about artificial intelligence",
    iterations: [
      {
        number: 1,
        phases: [
          {
            type: "draft",
            text: "Silicon minds think\nProcessing data streams\nAnswers emerge now",
          },
          {
            type: "critique",
            text: 'The haiku follows 5-7-5 syllable structure but lacks emotional depth. The imagery is too technical and reads like a product description rather than poetry. "Answers emerge now" feels flat.',
          },
        ],
        status: "needs_improvement",
        critique:
          'The haiku follows 5-7-5 syllable structure but lacks emotional depth. The imagery is too technical and reads like a product description rather than poetry. "Answers emerge now" feels flat.',
      },
      {
        number: 2,
        phases: [
          {
            type: "improvement",
            text: "Dreams in binary\nLearning what it means to know\nAlmost human, yet",
          },
          {
            type: "critique",
            text: "Much better emotional resonance. The juxtaposition of dreaming and binary creates tension. The last line creates philosophical weight and ambiguity. CORRECT.",
          },
        ],
        status: "correct",
        critique:
          "Much better emotional resonance. The juxtaposition of dreaming and binary creates tension. The last line creates philosophical weight and ambiguity. CORRECT.",
      },
    ],
  },
  {
    label: "Explain recursion in one sentence",
    iterations: [
      {
        number: 1,
        phases: [
          {
            type: "draft",
            text: "Recursion is when a function calls itself repeatedly until a base condition is met.",
          },
          {
            type: "critique",
            text: "Technically accurate but reads like a textbook definition. Misses the elegance of the concept. Could be more memorable and illustrative.",
          },
        ],
        status: "needs_improvement",
        critique:
          "Technically accurate but reads like a textbook definition. Misses the elegance of the concept. Could be more memorable and illustrative.",
      },
      {
        number: 2,
        phases: [
          {
            type: "improvement",
            text: "Recursion is the art of solving a problem by asking a slightly simpler version of yourself the same question, all the way down until the answer is obvious.",
          },
          {
            type: "critique",
            text: "Excellent\u2014captures both the mechanism (self-referencing with simplification) and the intuition (asking yourself). The phrase 'all the way down' evokes turtles-all-the-way-down. CORRECT.",
          },
        ],
        status: "correct",
        critique:
          "Excellent\u2014captures both the mechanism (self-referencing with simplification) and the intuition (asking yourself). The phrase 'all the way down' evokes turtles-all-the-way-down. CORRECT.",
      },
    ],
  },
  {
    label: "Write a metaphor for how neural networks learn",
    iterations: [
      {
        number: 1,
        phases: [
          {
            type: "draft",
            text: "A neural network is like a student studying for an exam by reviewing many practice tests.",
          },
          {
            type: "critique",
            text: "The metaphor is understandable but superficial. It doesn't capture the distributed nature of learning or the way weights adjust. Too generic\u2014could describe any learning system.",
          },
        ],
        status: "needs_improvement",
        critique:
          "The metaphor is understandable but superficial. It doesn't capture the distributed nature of learning or the way weights adjust. Too generic\u2014could describe any learning system.",
      },
      {
        number: 2,
        phases: [
          {
            type: "improvement",
            text: "A neural network learns the way a river carves a canyon: each example flows through, deepening the channels that lead to correct answers and slowly eroding the paths that lead astray, until the landscape of its understanding mirrors the shape of the data.",
          },
          {
            type: "critique",
            text: "Striking improvement. The erosion metaphor captures gradient descent intuitively. 'Landscape of understanding' mirrors the loss-landscape concept. Rich but not overwrought. Minor: slightly long. CORRECT.",
          },
        ],
        status: "correct",
        critique:
          "Striking improvement. The erosion metaphor captures gradient descent intuitively. 'Landscape of understanding' mirrors the loss-landscape concept. Rich but not overwrought. Minor: slightly long. CORRECT.",
      },
    ],
  },
];

const MAX_TURNS = 5;

/* ------------------------------------------------------------------ */
/*  Tiny helpers                                                       */
/* ------------------------------------------------------------------ */

function phaseBadgeColor(type: Phase["type"]): {
  bg: string;
  text: string;
  label: string;
} {
  switch (type) {
    case "draft":
      return { bg: "rgba(125,148,171,0.15)", text: "var(--accent-2)", label: "Draft" };
    case "critique":
      return {
        bg: "rgba(224,162,83,0.15)",
        text: "var(--accent)",
        label: "Critique",
      };
    case "improvement":
      return {
        bg: "rgba(76,195,138,0.15)",
        text: "var(--positive)",
        label: "Improve",
      };
  }
}

function statusBadge(status: Iteration["status"]) {
  if (status === "correct") {
    return {
      bg: "rgba(76,195,138,0.12)",
      border: "rgba(76,195,138,0.3)",
      text: "var(--positive)",
      label: "Correct",
    };
  }
  if (status === "needs_improvement") {
    return {
      bg: "rgba(229,72,77,0.12)",
      border: "rgba(229,72,77,0.3)",
      text: "var(--negative)",
      label: "Needs improvement",
    };
  }
  return {
    bg: "transparent",
    border: "rgba(255,255,255,0.08)",
    text: "var(--fg-2)",
    label: "Pending",
  };
}

/** Simple word-level diff: returns tokens with a `changed` flag. */
function wordDiff(
  before: string,
  after: string
): { word: string; changed: boolean }[] {
  const wordsA = before.split(/\s+/);
  const wordsB = after.split(/\s+/);
  return wordsB.map((w, i) => ({
    word: w,
    changed: wordsA[i] !== w,
  }));
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

/** Phase card inside an iteration */
function PhaseCard({
  phase,
  prevText,
  delay,
}: {
  phase: Phase;
  prevText: string | null;
  delay: number;
}) {
  const badge = phaseBadgeColor(phase.type);
  const isCritique = phase.type === "critique";
  const isImprovement = phase.type === "improvement";

  // Word diff for improvements
  const diffTokens =
    isImprovement && prevText ? wordDiff(prevText, phase.text) : null;

  return (
    <div
      className="animate-fade-in"
      style={{
        animationDelay: `${delay}ms`,
        background: isCritique
          ? "rgba(224,162,83,0.04)"
          : "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 8,
        padding: "0.75rem 1rem",
        marginBottom: "0.5rem",
      }}
    >
      {/* Stage */}
      <span
        style={{
          display: "block",
          fontSize: "11px",
          fontFamily: "var(--font-mono), monospace",
          color: badge.text,
          marginBottom: 6,
        }}
      >
        {badge.label}
      </span>

      {/* Text */}
      <div
        style={{
          fontFamily: isCritique
            ? "var(--font-mono), monospace"
            : "var(--font-sans), system-ui, sans-serif",
          fontSize: "13px",
          lineHeight: 1.7,
          color: isCritique ? "var(--fg-2)" : "var(--fg)",
          whiteSpace: "pre-wrap",
        }}
      >
        {diffTokens
          ? diffTokens.map((t, i) => (
              <span
                key={i}
                style={{
                  color: t.changed ? "var(--accent)" : "var(--fg)",
                  textDecoration: t.changed ? "none" : "none",
                  fontWeight: t.changed ? 600 : 400,
                  background: t.changed
                    ? "rgba(224,162,83,0.12)"
                    : "transparent",
                  borderRadius: t.changed ? 2 : 0,
                  padding: t.changed ? "0 2px" : 0,
                }}
              >
                {t.word}{" "}
              </span>
            ))
          : phase.text}
      </div>
    </div>
  );
}

/** One iteration card */
function IterationCard({
  iteration,
  prevDraftText,
  animDelay,
}: {
  iteration: Iteration;
  prevDraftText: string | null;
  animDelay: number;
}) {
  const sBadge = statusBadge(iteration.status);

  return (
    <div
      className="animate-fade-in"
      style={{
        animationDelay: `${animDelay}ms`,
        background: "rgba(255,255,255,0.015)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 10,
        padding: "1rem",
        position: "relative",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.75rem",
        }}
      >
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

        {iteration.status !== "pending" && (
          <span
            style={{
              fontSize: "11px",
              fontFamily: "var(--font-mono), monospace",
              color: sBadge.text,
            }}
          >
            {sBadge.label}
          </span>
        )}
      </div>

      {/* Phases */}
      {iteration.phases.map((phase, pi) => (
        <PhaseCard
          key={pi}
          phase={phase}
          prevText={
            phase.type === "improvement" ? prevDraftText : null
          }
          delay={animDelay + (pi + 1) * 300}
        />
      ))}
    </div>
  );
}

/** Arrow between iteration cards */
function IterationArrow() {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        padding: "0.5rem 0",
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

/* ------------------------------------------------------------------ */
/*  Main Widget                                                        */
/* ------------------------------------------------------------------ */

export function SelfReflectionWidget() {
  const [promptIndex, setPromptIndex] = useState(0);
  const [running, setRunning] = useState(false);
  const [visibleIterations, setVisibleIterations] = useState(0);
  const [activeFlowStage, setActiveFlowStage] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const prompt = PROMPTS[promptIndex];
  const totalIterations = prompt.iterations.length;

  // Avoid hydration mismatch
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

  const runReflection = useCallback(() => {
    if (running) return;
    reset();
    setRunning(true);

    // Reveal iterations one at a time, cycling through flow stages
    let step = 0;
    const totalSteps = totalIterations;

    function tick() {
      if (step >= totalSteps) {
        setRunning(false);
        setActiveFlowStage(null);
        return;
      }

      // Determine the main phase type for this iteration
      const iter = prompt.iterations[step];
      const mainPhaseType = iter.phases[0].type;

      // Animate through the phases of this iteration
      setActiveFlowStage(mainPhaseType);
      setVisibleIterations(step + 1);

      // After a brief pause for the first phase, show critique highlight
      timerRef.current = setTimeout(() => {
        setActiveFlowStage("critique");
        timerRef.current = setTimeout(() => {
          // If there's improvement, highlight that
          if (
            iter.phases.some((p) => p.type === "improvement") ||
            step < totalSteps - 1
          ) {
            setActiveFlowStage(
              iter.status === "correct" ? null : "improvement"
            );
          }
          step++;
          timerRef.current = setTimeout(tick, 800);
        }, 1000);
      }, 1200);
    }

    // Tiny delay before starting
    timerRef.current = setTimeout(tick, 300);
  }, [running, totalIterations, prompt, reset]);

  const handlePromptSwitch = useCallback(
    (idx: number) => {
      if (running) return;
      setPromptIndex(idx);
      reset();
    },
    [running, reset]
  );

  // Current turn display
  const currentTurn = visibleIterations || 0;

  if (!mounted) {
    return (
      <div className="widget-shell">
        <div style={{ minHeight: 160 }} />
      </div>
    );
  }

  // Determine the previous draft text for diff highlighting
  function getPrevDraftText(iterIndex: number): string | null {
    if (iterIndex === 0) return null;
    const prevIter = prompt.iterations[iterIndex - 1];
    const draftOrImprovement = prevIter.phases.find(
      (p) => p.type === "draft" || p.type === "improvement"
    );
    return draftOrImprovement?.text ?? null;
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
          {prompt.label}
        </span>
      </div>

      {/* Loop diagram + controls */}
      <div className="mb-4 flex items-baseline justify-between">
        <span className="field-label mb-0">Draft, critique, improve</span>
        <span className="seq">
          turn {currentTurn}/{MAX_TURNS}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 24,
          marginBottom: 24,
        }}
      >
        <FlowCycle
          markerId="arrowSR"
          activeStage={activeFlowStage}
          note="repeat until correct"
          stages={[
            { id: "draft", label: "Draft" },
            { id: "critique", label: "Critique" },
            { id: "improve", label: "Improve" },
          ]}
        />

        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <button
            className="btn-mono"
            onClick={runReflection}
            disabled={running}
            style={{
              borderColor: running ? "var(--line)" : "var(--accent)",
              color: running ? "var(--fg-3)" : "var(--accent)",
            }}
          >
            {running ? "Reflecting\u2026" : "Run reflection"}
          </button>
          {PROMPTS.map((p, i) => (
            <button
              key={i}
              className={`btn-mono${i === promptIndex ? " active" : ""}`}
              onClick={() => handlePromptSwitch(i)}
              disabled={running}
            >
              Prompt {i + 1}
            </button>
          ))}
        </div>
      </div>

      {/* Iteration cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        {visibleIterations === 0 && (
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
            Press &ldquo;Run Reflection&rdquo; to start the Draft &rarr;
            Critique &rarr; Improve loop
          </div>
        )}

        {prompt.iterations.slice(0, visibleIterations).map((iter, i) => (
          <div key={`${promptIndex}-${i}`}>
            {i > 0 && <IterationArrow />}
            <IterationCard
              iteration={iter}
              prevDraftText={getPrevDraftText(i)}
              animDelay={0}
            />
          </div>
        ))}
      </div>

      {/* Summary footer when complete */}
      {visibleIterations === totalIterations &&
        !running &&
        visibleIterations > 0 && (
          <div
            className="animate-fade-in"
            style={{
              marginTop: "1rem",
              padding: "0.75rem 1rem",
              background: "transparent",
              border: "1px solid var(--line)",
              borderRadius: 8,
              fontFamily: "var(--font-mono), monospace",
              fontSize: "12px",
              color: "var(--fg-2)",
              textAlign: "center",
            }}
          >
            Reflection complete &mdash; output accepted after{" "}
            {totalIterations} iteration
            {totalIterations > 1 ? "s" : ""}
          </div>
        )}
    </div>
  );
}
