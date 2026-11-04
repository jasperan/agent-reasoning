"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface Strategy {
  key: string;
  label: string;
  color: string;
  description: string;
}

const STRATEGIES: Strategy[] = [
  { key: "standard",           label: "Standard",           color: "var(--fg-2)", description: "Direct generation (baseline)" },
  { key: "cot",                label: "CoT",                color: "var(--fg-2)", description: "Chain-of-Thought reasoning" },
  { key: "tot",                label: "ToT",                color: "var(--fg-2)", description: "Tree of Thoughts exploration" },
  { key: "react",              label: "ReAct",              color: "var(--fg-2)", description: "Reason + Act with tools" },
  { key: "reflection",         label: "Reflection",         color: "var(--fg-2)", description: "Draft \u2192 Critique \u2192 Refine" },
  { key: "consistency",        label: "Consistency",        color: "var(--fg-2)", description: "Self-Consistency voting" },
  { key: "decomposed",         label: "Decomposed",         color: "var(--fg-2)", description: "Problem decomposition" },
  { key: "least_to_most",      label: "Least-to-Most",      color: "var(--fg-2)", description: "Progressive subproblem solving" },
  { key: "recursive",          label: "Recursive",          color: "var(--fg-2)", description: "Recursive LM (RLM)" },
  { key: "refinement",         label: "Refinement",         color: "var(--fg-2)", description: "Score-based iterative refinement" },
  { key: "complex_refinement", label: "Complex Refine",     color: "var(--fg-2)", description: "5-stage optimization pipeline" },
  { key: "debate",             label: "Debate",             color: "var(--fg-2)", description: "Adversarial debate synthesis" },
  { key: "mcts",               label: "MCTS",               color: "var(--fg-2)", description: "Monte Carlo Tree Search" },
  { key: "analogical",         label: "Analogical",         color: "var(--fg-2)", description: "Reasoning by analogy" },
  { key: "socratic",           label: "Socratic",           color: "var(--fg-2)", description: "Question-driven discovery" },
  { key: "meta",               label: "Meta",               color: "var(--fg-2)", description: "Meta-cognitive orchestration" },
];

const EXAMPLES = [
  "gemma3:4b+cot",
  "llama3+react",
  "qwen3:9b+debate",
  "gemma3+meta",
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const MONO = "var(--font-mono), monospace";

function parseModelStrategy(input: string): { baseModel: string; strategy: string } {
  const trimmed = input.trim();
  const plusIdx = trimmed.lastIndexOf("+");
  if (plusIdx === -1 || plusIdx === 0 || plusIdx === trimmed.length - 1) {
    return { baseModel: trimmed || "...", strategy: "" };
  }
  return {
    baseModel: trimmed.slice(0, plusIdx),
    strategy: trimmed.slice(plusIdx + 1),
  };
}

function monoLabel(color: string, mb?: number): React.CSSProperties {
  return {
    fontFamily: MONO,
    fontSize: "12px",
    color,
    fontWeight: 600,
    marginBottom: mb ?? 0,
  };
}

/* ------------------------------------------------------------------ */
/*  Flow animation phases                                              */
/* ------------------------------------------------------------------ */

type FlowPhase =
  | "idle"
  | "to_interceptor"
  | "at_interceptor"
  | "to_agent"
  | "at_agent"
  | "to_ollama"
  | "at_ollama"
  | "to_response"
  | "done";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ArchitectureWidget() {
  /* --- Hydration guard -------------------------------------------- */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* --- State ------------------------------------------------------ */
  const [input, setInput] = useState("gemma3:4b+cot");
  const [flowPhase, setFlowPhase] = useState<FlowPhase>("idle");
  const [flowColor, setFlowColor] = useState("var(--accent-2)");

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const parsed = parseModelStrategy(input);
  const matchedStrategy = STRATEGIES.find((s) => s.key === parsed.strategy);

  /* --- Timers cleanup -------------------------------------------- */
  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  /* --- Start flow animation -------------------------------------- */
  const startFlow = useCallback(() => {
    clearTimers();
    const color = matchedStrategy?.color ?? "var(--fg-2)";
    setFlowColor(color);
    setFlowPhase("idle");

    const phases: FlowPhase[] = [
      "to_interceptor",
      "at_interceptor",
      "to_agent",
      "at_agent",
      "to_ollama",
      "at_ollama",
      "to_response",
      "done",
    ];

    const delays = [100, 600, 1100, 1600, 2200, 2800, 3400, 4200];

    phases.forEach((phase, i) => {
      const t = setTimeout(() => setFlowPhase(phase), delays[i]);
      timersRef.current.push(t);
    });
  }, [matchedStrategy, clearTimers]);

  /* --- Example pill click ---------------------------------------- */
  const handleExample = useCallback(
    (example: string) => {
      setInput(example);
      clearTimers();
      setFlowPhase("idle");
    },
    [clearTimers],
  );

  /* --- Reset ----------------------------------------------------- */
  const reset = useCallback(() => {
    clearTimers();
    setFlowPhase("idle");
  }, [clearTimers]);

  /* --- SSR placeholder ------------------------------------------- */
  if (!mounted) {
    return (
      <div className="widget-shell">
        <div style={{ height: 160 }} />
      </div>
    );
  }

  /* --- Derived values -------------------------------------------- */
  const isFlowing = flowPhase !== "idle" && flowPhase !== "done";
  const isDone = flowPhase === "done";
  const hasMatch = !!matchedStrategy;

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-shell">

      {/* ---- Input Section ---- */}
      <div style={{ marginBottom: 24 }}>
        <div style={monoLabel("var(--fg-2)", 8)}>Model + Strategy Input</div>
        <div
          style={{
            display: "flex",
            gap: 10,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              if (flowPhase !== "idle") reset();
            }}
            placeholder='e.g. gemma3:4b+cot'
            style={{
              fontFamily: MONO,
              fontSize: "14px",
              background: "rgba(0,0,0,0.4)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 8,
              padding: "8px 14px",
              color: "var(--fg)",
              outline: "none",
              minWidth: 220,
              flex: 1,
              maxWidth: 320,
            }}
          />
          <button
            className="btn-mono"
            onClick={startFlow}
            disabled={isFlowing}
            style={{
              borderColor: isFlowing ? "rgba(255,255,255,0.04)" : "rgba(125,148,171,0.4)",
              color: isFlowing ? "var(--fg-3)" : "var(--accent-2)",
              cursor: isFlowing ? "not-allowed" : "pointer",
            }}
          >
            {isFlowing ? "Routing..." : "Route Query"}
          </button>
          {(isFlowing || isDone) && (
            <button className="btn-mono" onClick={reset}>
              Reset
            </button>
          )}
        </div>

        {/* ---- Example Pills ---- */}
        <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
          <span style={{ ...monoLabel("var(--fg-3)"), lineHeight: "28px", marginRight: 2 }}>
            Examples:
          </span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => handleExample(ex)}
              style={{
                fontFamily: MONO,
                fontSize: "12px",
                padding: "4px 10px",
                borderRadius: 12,
                border: `1px solid ${input === ex ? "rgba(125,148,171,0.4)" : "rgba(255,255,255,0.08)"}`,
                background: input === ex ? "rgba(125,148,171,0.08)" : "transparent",
                color: input === ex ? "var(--accent-2)" : "var(--fg-2)",
                cursor: "pointer",
                transition: "background-color 140ms var(--ease), border-color 140ms var(--ease), color 140ms var(--ease)",
              }}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* ---- Parse Result ---- */}
      <div
        className="code-block"
        style={{
          marginBottom: 24,
          display: "grid",
          gridTemplateColumns: "auto 1fr",
          gap: "4px 16px",
          alignItems: "baseline",
        }}
      >
        <span style={{ color: "var(--fg-3)" }}>input:</span>
        <span style={{ color: "var(--fg)" }}>&quot;{input}&quot;</span>

        <span style={{ color: "var(--fg-3)" }}>base_model:</span>
        <span style={{ color: "var(--accent-2)" }}>&quot;{parsed.baseModel}&quot;</span>

        <span style={{ color: "var(--fg-3)" }}>strategy:</span>
        <span style={{ color: hasMatch ? matchedStrategy!.color : "var(--negative)" }}>
          &quot;{parsed.strategy || "none"}&quot;
          {parsed.strategy && !hasMatch && (
            <span style={{ color: "var(--negative)", marginLeft: 8, fontSize: "12px" }}>
              (unknown strategy)
            </span>
          )}
        </span>

        <span style={{ color: "var(--fg-3)" }}>agent:</span>
        <span style={{ color: hasMatch ? matchedStrategy!.color : "var(--fg-2)" }}>
          {hasMatch ? matchedStrategy!.label + "Agent" : "StandardAgent (fallback)"}
        </span>
      </div>

      {/* ---- Flow Diagram ---- */}
      <div style={monoLabel("var(--fg-2)", 10)}>Data Flow</div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
          marginBottom: 28,
          overflowX: "auto",
          paddingBottom: 4,
        }}
      >
        <FlowBox
          label="User Query"
          sublabel="prompt text"
          borderColor="var(--fg-2)"
          active={flowPhase === "idle" || flowPhase === "to_interceptor"}
        />
        <FlowArrow active={flowPhase === "to_interceptor"} color={flowColor} />

        <FlowBox
          label="Interceptor"
          sublabel="parse model+strategy"
          borderColor="var(--accent-2)"
          active={
            flowPhase === "at_interceptor" ||
            flowPhase === "to_agent"
          }
        />
        <FlowArrow active={flowPhase === "to_agent"} color={flowColor} />

        <FlowBox
          label={hasMatch ? matchedStrategy!.label + "Agent" : "StandardAgent"}
          sublabel={hasMatch ? matchedStrategy!.description : "Direct generation"}
          borderColor={hasMatch ? matchedStrategy!.color : "var(--fg-2)"}
          active={
            flowPhase === "at_agent" ||
            flowPhase === "to_ollama"
          }
        />
        <FlowArrow active={flowPhase === "to_ollama"} color={flowColor} />

        <FlowBox
          label="Ollama"
          sublabel="localhost:11434"
          borderColor="var(--fg-3)"
          active={
            flowPhase === "at_ollama" ||
            flowPhase === "to_response"
          }
        />
        <FlowArrow active={flowPhase === "to_response"} color={flowColor} />

        <FlowBox
          label="Response"
          sublabel="streamed chunks"
          borderColor={isDone ? "var(--positive)" : "var(--fg-2)"}
          active={isDone}
        />
      </div>

      {/* ---- Animated Dot Bar ---- */}
      {isFlowing && (
        <div style={{ marginBottom: 24, position: "relative", height: 6 }}>
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 6,
              borderRadius: 3,
              background: "rgba(255,255,255,0.04)",
            }}
          />
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              height: 6,
              borderRadius: 3,
              background: flowColor,
              opacity: 0.6,
              transition: "width 0.5s ease-out",
              width: flowProgressWidth(flowPhase),
            }}
          />
          <div
            style={{
              position: "absolute",
              top: -3,
              width: 12,
              height: 12,
              borderRadius: "50%",
              background: flowColor,
              boxShadow: `0 0 12px ${flowColor}`,
              transition: "left 0.5s ease-out",
              left: flowDotLeft(flowPhase),
            }}
          />
        </div>
      )}

      {/* ---- Agent Map Grid ---- */}
      <div style={monoLabel("var(--fg-2)", 10)}>Agent Map &mdash; 16 Strategies</div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 8,
          marginBottom: 24,
        }}
      >
        {STRATEGIES.map((s) => {
          const isMatch = matchedStrategy?.key === s.key;
          const isActiveFlow = isMatch && (flowPhase === "at_agent" || flowPhase === "to_ollama");
          return (
            <div
              key={s.key}
              style={{
                background: isMatch ? "rgba(224,162,83,0.06)" : "transparent",
                border: `1px solid ${
                  isMatch ? "var(--accent)" : "rgba(255,255,255,0.06)"
                }`,
                borderRadius: 6,
                padding: "8px 10px",
                transition:
                  "background-color 140ms var(--ease), border-color 140ms var(--ease)",
                cursor: "default",
                position: "relative",
              }}
            >
              {isActiveFlow && (
                <span
                  style={{
                    position: "absolute",
                    top: 8,
                    right: 8,
                    width: 4,
                    height: 4,
                    borderRadius: 2,
                    background: "var(--accent)",
                  }}
                />
              )}
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: "12px",
                  fontWeight: 600,
                  color: isMatch ? s.color : "var(--fg-2)",
                  marginBottom: 2,
                  position: "relative",
                }}
              >
                {s.label}
              </div>
              <div
                style={{
                  fontSize: "11px",
                  color: isMatch ? "rgba(255,255,255,0.6)" : "var(--fg-3)",
                  lineHeight: 1.3,
                  position: "relative",
                }}
              >
                {s.description}
              </div>
            </div>
          );
        })}
      </div>

      {/* ---- Ollama Connection ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 14px",
          background: "rgba(0,0,0,0.3)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 8,
          marginBottom: 16,
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background:
              flowPhase === "at_ollama" || flowPhase === "to_response"
                ? "var(--positive)"
                : "var(--fg-3)",
            transition: "background-color 140ms var(--ease)",
          }}
        />
        <span
          style={{
            fontFamily: MONO,
            fontSize: "12px",
            color: "var(--fg-2)",
          }}
        >
          Ollama &middot; http://localhost:11434
        </span>
        <span
          style={{
            fontFamily: MONO,
            fontSize: "11px",
            color: "var(--fg-3)",
            marginLeft: "auto",
          }}
        >
          {flowPhase === "at_ollama"
            ? "Generating..."
            : flowPhase === "to_response" || isDone
            ? "Streaming response"
            : "Waiting for request"}
        </span>
      </div>

      {/* ---- Architecture Labels ---- */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 12,
        }}
      >
        <ArchLabel
          title="ReasoningInterceptor"
          desc="Drop-in Ollama replacement. Parses model+strategy naming convention and routes to the correct agent."
        />
        <ArchLabel
          title="AGENT_MAP"
          desc="Registry mapping strategy keys to agent classes. Single source of truth for all 16 reasoning strategies."
        />
        <ArchLabel
          title="BaseAgent"
          desc="Abstract base class providing OllamaClient connection, streaming interface, and colored logging."
        />
        <ArchLabel
          title="OllamaClient"
          desc="HTTP wrapper for Ollama API. Handles streaming and non-streaming responses with configurable parameters."
        />
      </div>

    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-Components                                                     */
/* ------------------------------------------------------------------ */

function FlowBox({
  label,
  sublabel,
  borderColor,
  active,
}: {
  label: string;
  sublabel: string;
  borderColor: string;
  active: boolean;
}) {
  return (
    <div
      style={{
        minWidth: 110,
        padding: "10px 12px",
        background: active ? "rgba(255,255,255,0.04)" : "transparent",
        border: `1px solid ${active ? borderColor : "rgba(255,255,255,0.08)"}`,
        borderRadius: 6,
        textAlign: "center",
        transition:
          "background-color 160ms var(--ease), border-color 160ms var(--ease)",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          fontFamily: MONO,
          fontSize: "12px",
          fontWeight: 500,
          color: active ? borderColor : "var(--fg-2)",
          marginBottom: 2,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "11px",
          color: "var(--fg-3)",
        }}
      >
        {sublabel}
      </div>
    </div>
  );
}

function FlowArrow({ active, color }: { active: boolean; color: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: "0 2px",
        flexShrink: 0,
      }}
    >
      <svg width="32" height="16" viewBox="0 0 32 16">
        <line
          x1="0"
          y1="8"
          x2="24"
          y2="8"
          stroke={active ? color : "rgba(255,255,255,0.1)"}
          strokeWidth="2"
          style={{ transition: "stroke 0.3s" }}
        />
        <polygon
          points="24,3 32,8 24,13"
          fill={active ? color : "rgba(255,255,255,0.1)"}
          style={{ transition: "fill 0.3s" }}
        />
        {active && (
          <circle r="3" fill={color} opacity="0.9">
            <animateMotion dur="0.5s" repeatCount="indefinite" path="M0,8 L24,8" />
          </circle>
        )}
      </svg>
    </div>
  );
}

function ArchLabel({ title, desc }: { title: string; desc: string }) {
  return (
    <div
      style={{
        padding: "10px 14px",
        border: "1px solid var(--line)",
        borderRadius: 6,
      }}
    >
      <div
        style={{
          fontFamily: MONO,
          fontSize: "12px",
          color: "var(--fg)",
          marginBottom: 4,
        }}
      >
        {title}
      </div>
      <div style={{ fontSize: "12px", color: "var(--fg-2)", lineHeight: 1.5 }}>
        {desc}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Utilities                                                          */
/* ------------------------------------------------------------------ */


function flowProgressWidth(phase: FlowPhase): string {
  switch (phase) {
    case "to_interceptor":
      return "10%";
    case "at_interceptor":
      return "25%";
    case "to_agent":
      return "40%";
    case "at_agent":
      return "55%";
    case "to_ollama":
      return "70%";
    case "at_ollama":
      return "85%";
    case "to_response":
      return "95%";
    case "done":
      return "100%";
    default:
      return "0%";
  }
}

function flowDotLeft(phase: FlowPhase): string {
  switch (phase) {
    case "to_interceptor":
      return "8%";
    case "at_interceptor":
      return "23%";
    case "to_agent":
      return "38%";
    case "at_agent":
      return "53%";
    case "to_ollama":
      return "68%";
    case "at_ollama":
      return "83%";
    case "to_response":
      return "93%";
    case "done":
      return "98%";
    default:
      return "0%";
  }
}
