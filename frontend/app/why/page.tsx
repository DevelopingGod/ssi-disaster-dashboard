import Link from "next/link";
import Footer from "@/components/Footer";

const differentiators = [
  {
    n: "01",
    title: "Real-Time Intelligence",
    problem: "General LLMs are frozen at their training cutoff — they have no awareness of events that occurred after it.",
    solution:
      "Natural-Disaster.io fetches live GDACS alerts and ReliefWeb humanitarian reports at the moment you ask. There is no cached knowledge — every response reflects what is happening right now.",
  },
  {
    n: "02",
    title: "Grounded Responses, Zero Hallucination",
    problem: "Chatbots generate plausible-sounding statistics and locations with complete confidence, even when they are fabricated.",
    solution:
      "Our agent synthesises only what it actually retrieved. If casualty figures or field reports are absent from the source data, it says so — it never fills the gap with invention.",
  },
  {
    n: "03",
    title: "Geospatial Context",
    problem: "A text answer cannot tell you where an event sits relative to population centres, coastlines, or neighbouring crises.",
    solution:
      "Every retrieved event is plotted on a live Leaflet map. Geography is rendered, not described — giving spatial context that no chatbot can replicate.",
  },
  {
    n: "04",
    title: "Institutional Data Provenance",
    problem: "General LLMs train on a broad mixture of web content, including unverified social media, blogs, and opinion pieces.",
    solution:
      "Every data point originates from GDACS (EU Joint Research Centre), USGS, ReliefWeb, or NASA FIRMS. The chain of authority is explicit and traceable.",
  },
  {
    n: "05",
    title: "Domain-Specific Agent Design",
    problem: "A general chatbot treats “what happened in India last week?” as a language task. It has no concept of event types, severity scales, or geographic precision.",
    solution:
      "The intelligence agent understands disaster semantics: it extracts timeframes, applies geographic filters, distinguishes severity levels, and routes queries to the right data tools automatically.",
  },
  {
    n: "06",
    title: "Built-In Safety Guardrails",
    problem: "Ask a general LLM for evacuation routes during a live disaster and it will produce something — whether or not that guidance is safe or current.",
    solution:
      "Natural-Disaster.io's guardrails block life-safety instructions by design, redirecting users to official civil protection authorities every time. Responsible by architecture, not by policy.",
  },
];

const comparison = [
  { aspect: "Data freshness",       llm: "Training cutoff — weeks to months old",   us: "Live feeds — seconds old" },
  { aspect: "Factual grounding",    llm: "Generated from memory, may hallucinate",   us: "Anchored to retrieved source data" },
  { aspect: "Geospatial output",    llm: "Text description only",                    us: "Interactive live map" },
  { aspect: "Data authority",       llm: "Broad web corpus",                         us: "UN, EU, NASA, USGS" },
  { aspect: "Disaster semantics",   llm: "General language understanding",           us: "Purpose-built disaster routing" },
  { aspect: "Safety guardrails",    llm: "Policy-level, inconsistent",               us: "Architectural — enforced by design" },
  { aspect: "Multilingual queries", llm: "Supported",                                us: "Supported" },
];

export default function WhyPage() {
  return (
    <div
      className="flex flex-col min-h-[calc(100vh-56px)]"
      style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}
    >
      <main className="flex-1">

        {/* Page header */}
        <div
          className="w-full border-b"
          style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
        >
          <div className="max-w-[1400px] mx-auto px-6 py-12">
            <p
              className="text-[0.5625rem] font-mono uppercase tracking-[0.28em] mb-2"
              style={{ color: "var(--text-muted)" }}
            >
              Platform Intelligence
            </p>
            <h1 className="text-3xl font-bold tracking-tight mb-3">
              Why Natural-Disaster.io?
            </h1>
            <p
              className="text-sm max-w-xl leading-relaxed"
              style={{
                color: "var(--text-secondary)",
                fontFamily: "Georgia, 'Times New Roman', serif",
              }}
            >
              Disaster intelligence isn&apos;t a chatbot conversation. Here is why a purpose-built
              agent beats asking a general-purpose LLM.
            </p>
          </div>
        </div>

        <div className="max-w-[1400px] mx-auto px-6 py-16 w-full space-y-20">

          {/* Differentiators */}
          <div>
            <p
              className="text-[0.5625rem] font-mono uppercase tracking-[0.28em] mb-8"
              style={{ color: "var(--text-muted)" }}
            >
              Six Reasons
            </p>
            <div
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px"
              style={{ backgroundColor: "var(--border-c)" }}
            >
              {differentiators.map(({ n, title, problem, solution }) => (
                <div
                  key={n}
                  className="p-8 flex flex-col gap-5"
                  style={{ backgroundColor: "var(--bg-primary)" }}
                >
                  <span
                    className="text-[0.5625rem] font-mono"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {n}
                  </span>
                  <h2
                    className="text-base font-bold tracking-tight leading-snug"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {title}
                  </h2>

                  {/* Problem */}
                  <div>
                    <p
                      className="text-[0.5rem] font-mono uppercase tracking-widest mb-2"
                      style={{ color: "var(--text-muted)" }}
                    >
                      The problem
                    </p>
                    <p
                      className="text-xs leading-relaxed"
                      style={{
                        color: "var(--text-muted)",
                        fontFamily: "Georgia, 'Times New Roman', serif",
                      }}
                    >
                      {problem}
                    </p>
                  </div>

                  {/* Solution */}
                  <div
                    className="border-l-2 pl-4"
                    style={{ borderColor: "var(--accent)" }}
                  >
                    <p
                      className="text-[0.5rem] font-mono uppercase tracking-widest mb-2"
                      style={{ color: "var(--accent)" }}
                    >
                      Our approach
                    </p>
                    <p
                      className="text-xs leading-relaxed"
                      style={{
                        color: "var(--text-secondary)",
                        fontFamily: "Georgia, 'Times New Roman', serif",
                      }}
                    >
                      {solution}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Comparison table */}
          <div>
            <p
              className="text-[0.5625rem] font-mono uppercase tracking-[0.28em] mb-8"
              style={{ color: "var(--text-muted)" }}
            >
              Side-by-Side Comparison
            </p>

            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-c)" }}>
                    <th
                      className="text-left py-3 pr-8 text-[0.5625rem] font-mono uppercase tracking-widest w-48"
                      style={{ color: "var(--text-muted)" }}
                    >
                      Capability
                    </th>
                    <th
                      className="text-left py-3 pr-8 text-[0.5625rem] font-mono uppercase tracking-widest"
                      style={{ color: "var(--text-muted)" }}
                    >
                      General-Purpose LLM
                    </th>
                    <th
                      className="text-left py-3 text-[0.5625rem] font-mono uppercase tracking-widest"
                      style={{ color: "var(--accent)" }}
                    >
                      Natural-Disaster.io
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.map(({ aspect, llm, us }, i) => (
                    <tr
                      key={aspect}
                      style={{
                        borderBottom: i < comparison.length - 1 ? "1px solid var(--border-c)" : "none",
                        backgroundColor: i % 2 === 0 ? "var(--bg-secondary)" : "var(--bg-primary)",
                      }}
                    >
                      <td
                        className="py-3.5 pr-8 text-[0.625rem] font-mono uppercase tracking-wider"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {aspect}
                      </td>
                      <td
                        className="py-3.5 pr-8 text-xs leading-relaxed"
                        style={{
                          color: "var(--text-muted)",
                          fontFamily: "Georgia, 'Times New Roman', serif",
                        }}
                      >
                        {llm}
                      </td>
                      <td
                        className="py-3.5 text-xs leading-relaxed font-medium"
                        style={{
                          color: "var(--text-secondary)",
                          fontFamily: "Georgia, 'Times New Roman', serif",
                        }}
                      >
                        {us}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* CTA */}
          <div
            className="border p-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6"
            style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
          >
            <div>
              <p
                className="text-[0.5625rem] font-mono uppercase tracking-[0.22em] mb-2"
                style={{ color: "var(--text-muted)" }}
              >
                Ready to see it in action?
              </p>
              <p
                className="text-sm leading-relaxed max-w-md"
                style={{
                  color: "var(--text-secondary)",
                  fontFamily: "Georgia, 'Times New Roman', serif",
                }}
              >
                Ask about any disaster, in any language. The intelligence agent will retrieve live
                data, synthesise it, and plot it on the map — in seconds.
              </p>
            </div>
            <Link
              href="/dashboard"
              className="flex-shrink-0 px-7 py-3 text-[0.6875rem] font-mono font-bold uppercase tracking-widest transition-opacity hover:opacity-85"
              style={{ backgroundColor: "var(--accent)", color: "var(--bg-primary)" }}
            >
              Launch the Agent →
            </Link>
          </div>

        </div>
      </main>

      <Footer />
    </div>
  );
}
