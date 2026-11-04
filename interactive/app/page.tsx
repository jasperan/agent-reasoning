"use client";

import { useEffect } from "react";
import {
  CoTChainWidget,
  ToTTreeWidget,
  ReActWidget,
  SelfReflectionWidget,
  ConsistencyWidget,
  DecomposedWidget,
  LeastToMostWidget,
  RefinementWidget,
  DebateWidget,
  MCTSWidget,
  AnalogicalWidget,
  SocraticWidget,
  MetaReasoningWidget,
  StrategyComparisonWidget,
  ArchitectureWidget,
} from "./components/widgets";

const sections = [
  { id: "cot", num: "01", title: "CoT" },
  { id: "tot", num: "02", title: "ToT" },
  { id: "react", num: "03", title: "ReAct" },
  { id: "reflection", num: "04", title: "Reflection" },
  { id: "consistency", num: "05", title: "Consistency" },
  { id: "decomposed", num: "06", title: "Decomposition" },
  { id: "ltm", num: "07", title: "Least-to-most" },
  { id: "refinement", num: "08", title: "Refinement" },
  { id: "debate", num: "09", title: "Debate" },
  { id: "mcts", num: "10", title: "MCTS" },
  { id: "analogical", num: "11", title: "Analogical" },
  { id: "socratic", num: "12", title: "Socratic" },
  { id: "meta", num: "13", title: "Meta" },
  { id: "benchmarks", num: "14", title: "Benchmarks" },
  { id: "architecture", num: "15", title: "Architecture" },
];

export default function Home() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("visible");
        }),
      { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
    );
    document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen">
      {/* ---- Nav ---- */}
      <nav className="sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-6 px-6">
          <a
            href="#top"
            className="shrink-0 text-[15px] font-medium tracking-tight text-foreground"
          >
            Agent<span className="text-muted-foreground">.reason</span>
          </a>
          <div className="relative min-w-0 flex-1">
            <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
              {sections.map((s) => (
                <a key={s.id} href={`#${s.id}`} className="nav-link">
                  <span className="text-fg-4">{s.num}</span>
                  <span>{s.title}</span>
                </a>
              ))}
            </div>
            <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-linear-to-l from-background to-transparent" />
          </div>
        </div>
      </nav>

      {/* ---- Hero ---- */}
      <header id="top" className="border-b border-border">
        <div className="mx-auto grid max-w-5xl grid-cols-1 items-center gap-12 px-6 py-16 md:grid-cols-[minmax(0,1fr)_380px] md:gap-16 md:py-24">
          <div>
            <p className="mb-6 font-mono text-xs text-fg-3">Interactive explorer</p>
            <h1 className="mb-6 text-4xl font-medium leading-[1.05] tracking-[-0.02em] text-foreground md:text-[56px]">
              From next token
              <br />
              to next thought
            </h1>
            <p className="max-w-lg text-lg leading-8 text-muted-foreground">
              Fifteen widgets for the reasoning strategies that turn a
              next-token predictor into an agent: chain of thought, tree
              search, reflection, debate, and eleven more.
            </p>
            <p className="mt-6 font-mono text-xs text-fg-3">
              Every strategy below runs in the page
            </p>
          </div>

          {/* ---- The trace: one chain of thought, numbered ---- */}
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-4 flex items-baseline justify-between font-mono text-xs text-fg-3">
              <span>trace 01 · cot</span>
              <span className="tabular-nums">4 steps</span>
            </div>
            <ol className="space-y-3">
              {[
                ["01", "3 boxes \u00d7 12 apples = 36"],
                ["02", "2 boxes \u00d7 8 oranges = 16"],
                ["03", "36 + 16 = 52"],
                ["04", "Answer: 52 fruits"],
              ].map(([n, text], i) => (
                <li key={n} className="flex items-baseline gap-3">
                  <span className="seq w-6 shrink-0">{n}</span>
                  <span
                    className={
                      i === 3
                        ? "font-mono text-[13px] text-accent"
                        : "font-mono text-[13px] text-fg-2"
                    }
                  >
                    {text}
                  </span>
                </li>
              ))}
            </ol>
            <div className="mt-4 flex items-baseline gap-3 border-t border-border pt-4">
              <span className="seq w-6 shrink-0">—</span>
              <span className="font-mono text-[13px] text-fg-3">
                direct answer: 48 fruits
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ---- Index ---- */}
      <div className="mx-auto max-w-5xl px-6 py-12">
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="flex items-baseline justify-between border-b border-border px-5 py-3">
            <h2 className="font-mono text-xs text-fg-3">Reasoning strategies</h2>
            <span className="font-mono text-xs text-fg-4">15</span>
          </div>
          <div className="-mb-px grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { id: "cot", title: "Chain of Thought", desc: "Step-by-step reasoning" },
              { id: "tot", title: "Tree of Thoughts", desc: "BFS tree exploration" },
              { id: "react", title: "ReAct", desc: "Reason + act with tools" },
              { id: "reflection", title: "Self-Reflection", desc: "Draft, critique, improve" },
              { id: "consistency", title: "Self-Consistency", desc: "Majority vote sampling" },
              { id: "decomposed", title: "Decomposition", desc: "Break into sub-tasks" },
              { id: "ltm", title: "Least-to-Most", desc: "Easy-to-hard progression" },
              { id: "refinement", title: "Refinement Loop", desc: "Score-based iteration" },
              { id: "debate", title: "Adversarial Debate", desc: "Pro and con with a judge" },
              { id: "mcts", title: "MCTS", desc: "Monte Carlo tree search" },
              { id: "analogical", title: "Analogical", desc: "Cross-domain analogy" },
              { id: "socratic", title: "Socratic Method", desc: "Progressive questioning" },
              { id: "meta", title: "Meta-Reasoning", desc: "Classify and route" },
              { id: "benchmarks", title: "Benchmarks", desc: "Strategy comparison" },
              { id: "architecture", title: "Architecture", desc: "System overview" },
            ].map((item, i) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                className="group flex items-baseline gap-3 border-b border-border px-5 py-3 transition-colors hover:bg-white/4"
              >
                <span className="seq w-6 shrink-0 group-hover:text-accent">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-foreground">
                    {item.title}
                  </span>
                  <span className="block text-xs text-fg-3">{item.desc}</span>
                </span>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* ---- Main Content ---- */}
      <main className="mx-auto max-w-5xl px-6 prose-dark">

        {/* ---- Section 01: Chain of Thought ---- */}
        <section id="cot" className="scroll-mt-16 reveal">
          <h2><span className="seq">01</span> Chain-of-Thought Reasoning</h2>
          <p>
            <strong>Chain-of-Thought (CoT)</strong> prompting, introduced by <span className="text-s1">Wei et al. (2022)</span>,
            is the simplest yet most impactful reasoning strategy. Instead of asking a model to jump directly to an answer,
            CoT injects an instruction like <em>&quot;Think step-by-step. Number each step.&quot;</em> This single change can
            dramatically improve accuracy on math, logic, and multi-step reasoning tasks.
          </p>
          <p>
            The key insight: when models externalize their reasoning into numbered steps, they can catch errors mid-chain
            and build on intermediate results rather than attempting to compute everything in a single forward pass.
          </p>
          <CoTChainWidget />
          <p>
            Notice how the step-by-step approach breaks a complex calculation into manageable pieces, while the
            direct approach often produces wrong answers by attempting shortcuts. This is why CoT is the foundation
            upon which more advanced strategies build.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 02: Tree of Thoughts ---- */}
        <section id="tot" className="scroll-mt-16 reveal">
          <h2><span className="seq">02</span> Tree of Thoughts</h2>
          <p>
            <strong>Tree of Thoughts (ToT)</strong>, proposed by <span className="text-s2">Yao et al. (2023)</span>,
            extends Chain-of-Thought from a single linear chain into a <em>tree</em> of possible reasoning paths.
            At each depth level, the model generates multiple candidate thoughts, scores each one, prunes
            the weakest, and continues exploring only the most promising branches.
          </p>
          <p>
            This breadth-first search over the reasoning space is particularly powerful for complex puzzles
            and strategy problems where the first approach isn&apos;t always the best. The scoring mechanism
            acts as a learned heuristic, guiding the search toward high-quality solutions.
          </p>
          <ToTTreeWidget />
          <p>
            Observe how low-scoring branches get pruned early, saving computation. The best path emerges
            not from a single chain of thought, but from systematic exploration and evaluation of alternatives.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 03: ReAct ---- */}
        <section id="react" className="scroll-mt-16 reveal">
          <h2><span className="seq">03</span> ReAct: Reason + Act</h2>
          <p>
            <strong>ReAct</strong>, introduced by <span className="text-s2">Yao et al. (2022)</span>,
            interleaves internal reasoning with external tool use. The model alternates between
            <span className="text-s2"> Thought</span> (internal reasoning),{" "}
            <span className="text-s1"> Action</span> (calling a tool), and{" "}
            <span className="text-s3"> Observation</span> (reading the tool&apos;s response).
          </p>
          <p>
            This is what gives AI models &quot;agency&quot; — the ability to interact with the world rather than
            relying solely on their training data. With tools like <code>web_search</code>, <code>calculate</code>,
            and <code>search</code>, a model can fact-check claims, perform precise arithmetic, and retrieve
            up-to-date information.
          </p>
          <ReActWidget />
          <p>
            The ReAct loop continues until the model determines it has enough information to answer.
            Each observation feeds into the next thought, creating a feedback loop between reasoning and evidence gathering.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 04: Self-Reflection ---- */}
        <section id="reflection" className="scroll-mt-16 reveal">
          <h2><span className="seq">04</span> Self-Reflection</h2>
          <p>
            <strong>Self-Reflection</strong>, based on <span className="text-s3">Shinn et al.&apos;s (2023) Reflexion</span>,
            implements a <em>Draft → Critique → Improve</em> loop. The model generates an initial response,
            then acts as its own critic to identify weaknesses, and finally produces an improved version.
          </p>
          <p>
            The loop continues until the critique finds the response satisfactory (marked &quot;CORRECT&quot;)
            or a maximum number of turns is reached. This mimics the human writing process of drafting,
            reviewing, and revising — which consistently produces higher-quality output than single-shot generation.
          </p>
          <SelfReflectionWidget />
          <p>
            Each iteration shows measurable improvement. The model learns from its own feedback,
            addressing specific weaknesses identified in each critique cycle.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 05: Self-Consistency ---- */}
        <section id="consistency" className="scroll-mt-16 reveal">
          <h2><span className="seq">05</span> Self-Consistency Voting</h2>
          <p>
            <strong>Self-Consistency</strong>, from <span className="text-s3">Wang et al. (2022)</span>,
            takes a statistical approach to reasoning. Instead of relying on a single chain of thought,
            it generates <em>k</em> independent reasoning paths using temperature sampling, extracts
            the final answer from each, and takes a majority vote.
          </p>
          <p>
            The insight is elegant: if multiple diverse reasoning paths converge on the same answer,
            that answer is more likely to be correct. Wrong answers tend to be wrong in <em>different</em> ways,
            while correct answers cluster together.
          </p>
          <ConsistencyWidget />
          <p>
            Increasing k improves reliability but costs more LLM calls. The sweet spot depends on
            the task difficulty and acceptable error rate. For high-stakes decisions, more samples
            provide stronger confidence guarantees.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 06: Decomposition ---- */}
        <section id="decomposed" className="scroll-mt-16 reveal">
          <h2><span className="seq">06</span> Problem Decomposition</h2>
          <p>
            <strong>Decomposed Reasoning</strong>, based on <span className="text-s4">Khot et al. (2022)</span>,
            tackles complex problems by breaking them into manageable sub-tasks. Each sub-task is solved
            sequentially, with the accumulated context from prior solutions informing subsequent ones.
          </p>
          <p>
            This mirrors how humans approach complex projects — by creating a task list, working through
            items in order, and building up to a complete solution. The final synthesis step combines
            all sub-task results into a coherent answer.
          </p>
          <DecomposedWidget />
          <p>
            The power of decomposition lies in reducing cognitive load per step. No single LLM call
            needs to handle the entire problem — each sub-task is focused and manageable.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 07: Least-to-Most ---- */}
        <section id="ltm" className="scroll-mt-16 reveal">
          <h2><span className="seq">07</span> Least-to-Most Prompting</h2>
          <p>
            <strong>Least-to-Most</strong>, from <span className="text-s4">Zhou et al. (2022)</span>,
            is a refinement of decomposition that explicitly orders sub-problems from <em>easiest to hardest</em>.
            Each easier solution becomes a stepping stone for the harder problems that follow.
          </p>
          <p>
            This progressive approach is particularly effective for problems where humans commonly make
            scaling errors — jumping to conclusions without building up from fundamentals.
          </p>
          <LeastToMostWidget />
          <p>
            The staircase pattern reveals how complex questions often have surprisingly simple answers
            when approached from the right foundation. The linear scaling fallacy is a classic example
            of what happens when you skip the intermediate steps.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 08: Refinement Loop ---- */}
        <section id="refinement" className="scroll-mt-16 reveal">
          <h2><span className="seq">08</span> Iterative Refinement</h2>
          <p>
            The <strong>Refinement Loop</strong> implements a <em>Generator → Critic → Refiner</em> cycle
            with quantitative scoring. A critic evaluates each draft on a 0.0–1.0 scale and provides
            specific feedback. The loop continues until the score exceeds a configurable threshold.
          </p>
          <p>
            Unlike Self-Reflection (which uses binary pass/fail), the Refinement Loop uses continuous
            scoring, enabling fine-grained quality control. You can set the threshold high for
            production content or lower for quick drafts.
          </p>
          <RefinementWidget />
          <p>
            The score trend reveals the diminishing returns of additional iterations — early iterations
            produce large quality jumps, while later ones offer marginal improvements. The threshold
            lets you trade off quality against computation cost.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 09: Adversarial Debate ---- */}
        <section id="debate" className="scroll-mt-16 reveal">
          <h2><span className="seq">09</span> Adversarial Debate</h2>
          <p>
            <strong>Adversarial Debate</strong>, inspired by <span className="text-s6">Irving et al. (2018)</span>,
            pits two sides against each other with a judge evaluating each round. A <em>PRO</em> side
            argues for the proposition while a <em>CON</em> side argues against it, with context
            building across rounds.
          </p>
          <p>
            This strategy excels at generating nuanced, balanced analysis on controversial topics.
            By forcing the model to construct the strongest possible arguments for <em>both</em> sides,
            it avoids the one-sided responses that plague standard generation.
          </p>
          <DebateWidget />
          <p>
            The judge&apos;s round-by-round scoring reveals which arguments land and which fall flat.
            The final synthesis captures the strongest points from both sides, producing a more
            thoughtful conclusion than either side alone.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 10: MCTS ---- */}
        <section id="mcts" className="scroll-mt-16 reveal">
          <h2><span className="seq">10</span> Monte Carlo Tree Search</h2>
          <p>
            <strong>MCTS</strong>, based on <span className="text-s6">Browne et al. (2012)</span>,
            applies the same algorithm that powered AlphaGo to language model reasoning. The four-phase
            cycle — <em>Selection → Expansion → Simulation → Backpropagation</em> — explores the
            reasoning space strategically using the UCB1 formula to balance exploration vs exploitation.
          </p>
          <p>
            UCB1 = wins/visits + C &times; &radic;(ln(parent_visits)/visits) ensures that promising
            branches get more attention while underexplored branches aren&apos;t forgotten. The exploration
            constant C controls this trade-off.
          </p>
          <MCTSWidget />
          <p>
            Watch how the tree grows organically as simulations accumulate. Nodes with high win rates
            attract more visits, while the exploration bonus ensures new branches get a fair evaluation.
            This mirrors how strategic reasoning works — building confidence through repeated evaluation.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 11: Analogical ---- */}
        <section id="analogical" className="scroll-mt-16 reveal">
          <h2><span className="seq">11</span> Analogical Reasoning</h2>
          <p>
            <strong>Analogical Reasoning</strong>, rooted in <span className="text-s6">Gentner&apos;s (1983)</span> structure-mapping
            theory, solves novel problems by finding structurally similar solved problems from other domains
            and transferring the solution approach. It proceeds in three phases: <em>Identify structure → Generate analogies → Transfer solution</em>.
          </p>
          <p>
            This is how some of humanity&apos;s greatest innovations emerged — airplanes from birds,
            Velcro from burrs, neural networks from brains. The model extracts structural elements
            from the problem, searches for analogous systems, and maps solutions across domains.
          </p>
          <AnalogicalWidget />
          <p>
            The mapping between domains reveals deep structural parallels that aren&apos;t obvious at first glance.
            Cross-domain transfer often produces more creative solutions than staying within a single field.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 12: Socratic ---- */}
        <section id="socratic" className="scroll-mt-16 reveal">
          <h2><span className="seq">12</span> Socratic Method</h2>
          <p>
            The <strong>Socratic Method</strong>, based on <span className="text-s6">Paul &amp; Elder&apos;s (2007)</span> critical
            thinking framework, builds understanding through progressive questioning. The model generates
            probing questions, answers them to extract insights, and synthesizes everything into a
            comprehensive conclusion.
          </p>
          <p>
            This approach is particularly powerful for deep philosophical questions and topics where
            the answer emerges from examining assumptions, implications, and edge cases rather than
            retrieving facts.
          </p>
          <SocraticWidget />
          <p>
            Each question narrows the solution space while each answer contributes a building block
            to the final synthesis. The method mirrors how the best teachers guide students — not by
            giving answers, but by asking the right questions.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 13: Meta-Reasoning ---- */}
        <section id="meta" className="scroll-mt-16 reveal">
          <h2><span className="seq">13</span> Meta-Reasoning Router</h2>
          <p>
            The <strong>Meta-Reasoning Agent</strong> is the orchestrator — it analyzes incoming queries,
            classifies them by type (math, logic, creative, factual, controversial, planning, philosophical),
            and routes each query to the optimal reasoning strategy. This eliminates the need to manually
            select a strategy for every question.
          </p>
          <p>
            Think of it as a dispatcher that understands which tool is right for which job. A math
            problem goes to Chain-of-Thought, a controversial question goes to Debate, a factual
            query goes to ReAct for live tool use.
          </p>
          <MetaReasoningWidget />
          <p>
            The confidence score indicates how certain the classifier is about its routing decision.
            In practice, some queries are ambiguous — a question about &quot;the ethics of AI in healthcare&quot;
            could be philosophical, controversial, or planning depending on the context.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 14: Benchmarks ---- */}
        <section id="benchmarks" className="scroll-mt-16 reveal">
          <h2><span className="seq">14</span> Strategy Benchmarks</h2>
          <p>
            How do these strategies actually perform? The benchmark suite evaluates all strategies across
            standard datasets: <strong>GSM8K</strong> (math reasoning), <strong>MMLU</strong> (broad knowledge),
            and <strong>ARC-Challenge</strong> (science reasoning). Results vary significantly by task type —
            no single strategy dominates everywhere.
          </p>
          <p>
            The LLM calls metric reveals the computational cost of each strategy. Tree of Thoughts and
            Self-Consistency are powerful but expensive, while Chain-of-Thought offers the best
            accuracy-per-call ratio for most tasks.
          </p>
          <StrategyComparisonWidget />
          <p>
            These benchmarks highlight a fundamental truth: <em>the best strategy depends on the task</em>.
            Math benefits from structured step-by-step reasoning. Knowledge retrieval benefits from
            tool access. Nuanced analysis benefits from debate. The Meta-Reasoning Router exists
            precisely to automate this selection.
          </p>
          <div className="section-divider" />
        </section>

        {/* ---- Section 15: Architecture ---- */}
        <section id="architecture" className="scroll-mt-16 reveal">
          <h2><span className="seq">15</span> System Architecture</h2>
          <p>
            Under the hood, the agent-reasoning system uses a simple but powerful routing pattern.
            The <strong>ReasoningInterceptor</strong> parses the <code>model+strategy</code> naming convention
            (e.g., <code>gemma3:4b+tot</code>), splits it into a base model and strategy identifier,
            and routes to the corresponding agent via the <strong>AGENT_MAP</strong> registry.
          </p>
          <p>
            This design makes the system a drop-in replacement for any Ollama-compatible client.
            Just change your model name from <code>gemma3</code> to <code>gemma3+tot</code>, and
            your queries automatically flow through the Tree of Thoughts reasoning engine.
          </p>
          <ArchitectureWidget />
          <p>
            The architecture is intentionally simple: one interceptor, one agent map, one client wrapper.
            Every agent inherits from <code>BaseAgent</code> and implements the same <code>stream(query)</code> interface.
            This uniformity means adding a new reasoning strategy is as easy as writing a single Python class
            and registering it in the map.
          </p>
        </section>

        {/* ---- Conclusion ---- */}
        <section className="scroll-mt-16 reveal mt-16 mb-24">
          <h2>Conclusion</h2>
          <p>
            The journey from <span className="text-s1">token prediction</span> to{" "}
            <span className="text-s2">structured reasoning</span>{" "}is not about replacing models —
            it&apos;s about wrapping them in <span className="text-s4">cognitive architectures</span>{" "}that
            guide their thinking process. Each strategy we&apos;ve explored addresses a different failure mode
            of raw generation:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 my-8">
            {[
              { label: "CoT", desc: "Externalizes intermediate reasoning" },
              { label: "ToT / ReAct", desc: "Explores alternatives and uses tools" },
              { label: "Reflection / Consistency", desc: "Self-corrects and validates" },
              { label: "Decomposition", desc: "Divides and conquers complexity" },
              { label: "Refinement", desc: "Iterates toward quality targets" },
              { label: "Debate / MCTS / Socratic", desc: "Challenges assumptions deeply" },
            ].map((item) => (
              <div
                key={item.label}
                className="bg-card border border-border rounded-lg p-4"
              >
                <div className="text-sm font-medium mb-1 text-foreground">
                  {item.label}
                </div>
                <div className="text-xs text-muted-foreground">{item.desc}</div>
              </div>
            ))}
          </div>
          <p>
            The <span className="text-s7">Meta-Reasoning Router</span> ties it all together,
            automatically selecting the right strategy for each query. And the{" "}
            <span className="text-s7">architecture</span> makes it a drop-in enhancement —
            just append <code>+strategy</code> to your model name.
          </p>
          <p>
            The reasoning layer is where AI becomes more than a text generator. It becomes a thinker.
          </p>
        </section>
      </main>

      {/* ---- Footer ---- */}
      <footer className="border-t border-border py-8 text-center text-sm text-muted-foreground">
        <p className="font-mono text-xs mb-2">
          Agent Reasoning — Interactive Explorer
        </p>
        <p className="text-xs">
          Built with Next.js, React 19, and Tailwind CSS.{" "}
          <a href="https://github.com/jasperan/agent-reasoning" className="text-s2 hover:underline">
            View on GitHub
          </a>
        </p>
      </footer>
    </div>
  );
}
