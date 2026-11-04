"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Static data — deterministic so SSR / CSR always match             */
/* ------------------------------------------------------------------ */

interface Sample {
  id: number;
  reasoning: string;
  answer: number;
}

const SAMPLE_POOL: Sample[][] = [
  /* k = 3 */
  [
    { id: 1, reasoning: "3 fields x 4 rows = 12 rows total, 12 x 7 = 84 stalks", answer: 84 },
    { id: 2, reasoning: "Each field has 4 x 7 = 28 stalks, 3 x 28 = 84", answer: 84 },
    { id: 3, reasoning: "3 x 4 x 7... 12 x 7, I think 82", answer: 82 },
  ],
  /* k = 4 */
  [
    { id: 1, reasoning: "3 fields x 4 rows = 12 rows total, 12 x 7 = 84 stalks", answer: 84 },
    { id: 2, reasoning: "Each field has 4 x 7 = 28 stalks, 3 x 28 = 84", answer: 84 },
    { id: 3, reasoning: "3 x 4 x 7 = 84", answer: 84 },
    { id: 4, reasoning: "3 fields x 4 rows = 12, then 12 x 7... I think 82", answer: 82 },
  ],
  /* k = 5 (default) */
  [
    { id: 1, reasoning: "3 fields x 4 rows = 12 rows total, 12 x 7 = 84 stalks", answer: 84 },
    { id: 2, reasoning: "Each field has 4 x 7 = 28 stalks, 3 x 28 = 84", answer: 84 },
    { id: 3, reasoning: "3 x 4 x 7 = 84", answer: 84 },
    { id: 4, reasoning: "3 fields x 4 rows = 12, then 12 x 7... I think 82", answer: 82 },
    { id: 5, reasoning: "4 x 7 = 28 per field, 28 x 3 = 84", answer: 84 },
  ],
  /* k = 6 */
  [
    { id: 1, reasoning: "3 fields x 4 rows = 12 rows total, 12 x 7 = 84 stalks", answer: 84 },
    { id: 2, reasoning: "Each field has 4 x 7 = 28 stalks, 3 x 28 = 84", answer: 84 },
    { id: 3, reasoning: "3 x 4 x 7 = 84", answer: 84 },
    { id: 4, reasoning: "3 fields x 4 rows = 12, then 12 x 7... I think 82", answer: 82 },
    { id: 5, reasoning: "4 x 7 = 28 per field, 28 x 3 = 84", answer: 84 },
    { id: 6, reasoning: "3 x 4 = 12, 12 x 7... maybe 88?", answer: 88 },
  ],
  /* k = 7 */
  [
    { id: 1, reasoning: "3 fields x 4 rows = 12 rows total, 12 x 7 = 84 stalks", answer: 84 },
    { id: 2, reasoning: "Each field has 4 x 7 = 28 stalks, 3 x 28 = 84", answer: 84 },
    { id: 3, reasoning: "3 x 4 x 7 = 84", answer: 84 },
    { id: 4, reasoning: "3 fields x 4 rows = 12, then 12 x 7... I think 82", answer: 82 },
    { id: 5, reasoning: "4 x 7 = 28 per field, 28 x 3 = 84", answer: 84 },
    { id: 6, reasoning: "3 x 4 = 12, 12 x 7... maybe 88?", answer: 88 },
    { id: 7, reasoning: "Fields: 3, rows per field: 4, stalks: 7. 3 x 28 = 84", answer: 84 },
  ],
];

function getSamples(k: number): Sample[] {
  return SAMPLE_POOL[k - 3] ?? SAMPLE_POOL[2];
}

/* The majority answer carries the accent; the dissent stays neutral. */
function answerColor(_answer: number, isWinner: boolean): string {
  return isWinner ? "var(--accent)" : "var(--fg-3)";
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ConsistencyWidget() {
  const [k, setK] = useState(5);
  const [visibleSamples, setVisibleSamples] = useState<Sample[]>([]);
  const [showVoting, setShowVoting] = useState(false);
  const [sampling, setSampling] = useState(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  /* Clean up timers on unmount or re-sample */
  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  /* Reset when k changes */
  const handleKChange = useCallback(
    (newK: number) => {
      clearTimers();
      setK(newK);
      setVisibleSamples([]);
      setShowVoting(false);
      setSampling(false);
    },
    [clearTimers],
  );

  /* "Sample" button handler — stagger sample cards in, then show voting */
  const handleSample = useCallback(() => {
    clearTimers();
    setVisibleSamples([]);
    setShowVoting(false);
    setSampling(true);

    const samples = getSamples(k);
    samples.forEach((sample, i) => {
      const t = setTimeout(() => {
        setVisibleSamples((prev) => [...prev, sample]);
      }, (i + 1) * 320);
      timersRef.current.push(t);
    });

    /* After all samples, show the voting section */
    const tallyDelay = (samples.length + 1) * 320 + 200;
    const t2 = setTimeout(() => {
      setShowVoting(true);
      setSampling(false);
    }, tallyDelay);
    timersRef.current.push(t2);
  }, [k, clearTimers]);

  /* Compute vote tally from visible samples */
  const tally: Record<number, number> = {};
  visibleSamples.forEach((s) => {
    tally[s.answer] = (tally[s.answer] ?? 0) + 1;
  });

  const sortedAnswers = Object.entries(tally)
    .map(([ans, count]) => ({ answer: Number(ans), count }))
    .sort((a, b) => b.count - a.count);

  const winnerAnswer = sortedAnswers[0]?.answer ?? 0;
  const totalVotes = visibleSamples.length;
  const winnerCount = sortedAnswers[0]?.count ?? 0;
  const confidence = totalVotes > 0 ? Math.round((winnerCount / totalVotes) * 100) : 0;
  const maxCount = sortedAnswers[0]?.count ?? 1;

  return (
    <div className="widget-shell">

      {/* ---- Problem Statement ---- */}
      <div
        style={{
          background: "rgba(0,0,0,0.35)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 8,
          padding: "0.85rem 1rem",
          marginBottom: "1.25rem",
          lineHeight: 1.7,
        }}
      >
        <span style={{ color: "var(--fg-2)", fontSize: "12px", fontFamily: "var(--font-mono), monospace" }}>
          Problem:
        </span>
        <p style={{ margin: "0.35rem 0 0", color: "var(--fg)", fontSize: "14px" }}>
          A farmer has <strong>3</strong> fields. Each field has{" "}
          <strong>4</strong> rows of corn with{" "}
          <strong>7</strong> stalks per row. How many corn stalks total?
        </p>
      </div>

      {/* ---- Controls Row ---- */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
          marginBottom: "1.25rem",
        }}
      >
        {/* k slider */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: "1 1 160px" }}>
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "12px",
              color: "var(--fg-2)",
              whiteSpace: "nowrap",
            }}
          >
            k =
          </span>
          <input
            type="range"
            min={3}
            max={7}
            value={k}
            onChange={(e) => handleKChange(Number(e.target.value))}
            style={{ flex: 1 }}
          />
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "13px",
              color: "var(--fg)",
              minWidth: 18,
              textAlign: "center",
            }}
          >
            {k}
          </span>
        </div>

        {/* Temperature badge */}
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "12px",
            color: "var(--fg-3)",
          }}
        >
          T = 0.7
        </span>

        {/* Sample button */}
        <button
          className="btn-mono"
          onClick={handleSample}
          disabled={sampling}
          style={{
            borderColor: sampling ? "var(--line)" : "var(--accent)",
            color: sampling ? "var(--fg-3)" : "var(--accent)",
            cursor: sampling ? "wait" : "pointer",
          }}
        >
          {sampling ? "Sampling..." : "Sample"}
        </button>
      </div>

      {/* ---- Sample Cards Grid ---- */}
      {visibleSamples.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: "0.65rem",
            marginBottom: "1.25rem",
          }}
        >
          {visibleSamples.map((sample, idx) => {
            const isWinner = showVoting && sample.answer === winnerAnswer;
            return (
              <div
                key={`${k}-${sample.id}`}
                className="animate-slide-in"
                style={{
                  animationDelay: `${idx * 0.06}s`,
                  background: "rgba(0,0,0,0.3)",
                  border: `1px solid ${isWinner ? "rgba(224,162,83,0.35)" : "rgba(255,255,255,0.06)"}`,
                  borderRadius: 8,
                  padding: "0.7rem 0.8rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.45rem",
                  transition: "border-color 0.4s",
                }}
              >
                {/* Header row: badge + answer dot */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span
                    style={{
                      fontFamily: "var(--font-mono), monospace",
                      fontSize: "11px",
                      color: "var(--fg-2)",
                      background: "rgba(255,255,255,0.06)",
                      borderRadius: 4,
                      padding: "0.1rem 0.4rem",
                    }}
                  >
                    Sample {sample.id}
                  </span>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: answerColor(sample.answer, isWinner),
                      flexShrink: 0,
                    }}
                  />
                </div>

                {/* Reasoning */}
                <p
                  style={{
                    fontFamily: "var(--font-mono), monospace",
                    fontSize: "12px",
                    color: "var(--fg-2)",
                    lineHeight: 1.55,
                    margin: 0,
                  }}
                >
                  {sample.reasoning}
                </p>

                {/* Final answer */}
                <div
                  style={{
                    fontFamily: "var(--font-mono), monospace",
                    fontSize: "12px",
                    color: isWinner ? "var(--accent)" : "var(--fg-2)",
                    borderTop: "1px solid rgba(255,255,255,0.06)",
                    paddingTop: "0.35rem",
                    marginTop: "auto",
                  }}
                >
                  Final Answer: {sample.answer}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ---- Voting Tally ---- */}
      {showVoting && (
        <div className="animate-fade-in" style={{ marginTop: "0.25rem" }}>
          {/* Section heading */}
          <div
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "12px",
              color: "var(--fg-2)",
              marginBottom: "0.65rem",
            }}
          >
            Majority Vote
          </div>

          {/* Vote bars */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem", marginBottom: "1rem" }}>
            {sortedAnswers.map(({ answer, count }) => {
              const isWin = answer === winnerAnswer;
              const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
              return (
                <div key={answer} style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                  {/* Answer label */}
                  <span
                    style={{
                      fontFamily: "var(--font-mono), monospace",
                      fontSize: "12px",
                      color: isWin ? "var(--fg)" : "var(--fg-3)",
                      minWidth: 28,
                      textAlign: "right",
                    }}
                  >
                    {answer}
                  </span>

                  {/* Bar track */}
                  <div
                    style={{
                      flex: 1,
                      height: 24,
                      background: "rgba(255,255,255,0.04)",
                      borderRadius: 4,
                      overflow: "hidden",
                      position: "relative",
                    }}
                  >
                    <div
                      className="vote-bar"
                      style={{
                        width: `${pct}%`,
                        background: isWin
                          ? "var(--accent)"
                          : "rgba(255,255,255,0.10)",
                        color: isWin ? "#1a1207" : "var(--fg-2)",
                      }}
                    >
                      {count} vote{count !== 1 ? "s" : ""}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Winner result */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              background: "transparent",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 8,
              padding: "12px 16px",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "18px",
                color: "var(--accent)",
              }}
            >
              {winnerAnswer}
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.1rem" }}>
              <span style={{ fontSize: "13px", color: "var(--fg)" }}>Majority Vote Winner</span>
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "12px",
                  color: "var(--fg-2)",
                }}
              >
                {winnerCount}/{totalVotes} samples agree &middot; {confidence}% confidence
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
