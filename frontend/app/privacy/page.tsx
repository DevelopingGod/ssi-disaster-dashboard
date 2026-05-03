import Footer from "@/components/Footer";

type Section = { heading: string; body: string | string[] };

const sections: Section[] = [
  {
    heading: "Introduction",
    body: "This Privacy Policy explains how Natural-Disaster.io (“we”, “our”, or “the platform”) handles information when you use this service. Natural-Disaster.io is a demonstration platform for AI-powered humanitarian intelligence. We are committed to minimising data collection and being transparent about how any information is used.",
  },
  {
    heading: "Information We Collect",
    body: [
      "Query text you submit to the AI agent — used transiently to generate a response, then discarded. We do not store query history in any database.",
      "Theme preference (dark / light) — stored only in your browser's localStorage. It never leaves your device.",
      "No account, email, name, IP address, or personally-identifiable information is collected or retained.",
    ],
  },
  {
    heading: "How We Use Your Information",
    body: [
      "Your query is forwarded to the Groq API (a third-party LLM provider) to generate a natural-language response. Groq's own privacy policy governs their handling of this data.",
      "Your query may also trigger requests to GDACS and ReliefWeb APIs to retrieve live disaster event data. These requests contain only a search term — no user identity.",
      "We do not use your information for advertising, profiling, or any secondary purpose.",
    ],
  },
  {
    heading: "Third-Party Services",
    body: [
      "Groq API (LLM inference) — groq.com",
      "GDACS RSS Feed — gdacs.org",
      "ReliefWeb v2 API — reliefweb.int",
      "HuggingFace Spaces (backend hosting) — huggingface.co",
      "Vercel (frontend hosting) — vercel.com",
      "Each third-party service operates under its own privacy policy. We recommend reviewing them if you have concerns about downstream data handling.",
    ],
  },
  {
    heading: "Cookies & Local Storage",
    body: "We do not use tracking cookies or analytics cookies. The only browser storage we write to is localStorage for your theme preference (key: disaster-theme). This value is never transmitted to any server.",
  },
  {
    heading: "Data Retention",
    body: "We retain no user data. Queries are processed in memory and discarded upon response delivery. There is no user database, no logs tied to individuals, and no analytics pipeline.",
  },
  {
    heading: "Children's Privacy",
    body: "This service is not directed at children under 13 years of age. We do not knowingly collect information from children.",
  },
  {
    heading: "Changes to This Policy",
    body: "We may update this Privacy Policy from time to time. The date at the top of this page reflects the most recent revision. Continued use of the platform after changes constitutes acceptance of the updated policy.",
  },
  {
    heading: "Contact",
    body: "For privacy-related questions, contact the developer via LinkedIn at linkedin.com/in/sankalp-indish or via GitHub at github.com/SankalpIndish.",
  },
];

export default function PrivacyPolicy() {
  return (
    <div
      className="flex flex-col min-h-[calc(100vh-56px)]"
      style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}
    >
      <main className="flex-1">
        {/* Header */}
        <div
          className="w-full border-b"
          style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
        >
          <div className="max-w-[1400px] mx-auto px-6 py-12">
            <p
              className="text-[0.5625rem] font-mono uppercase tracking-[0.28em] mb-2"
              style={{ color: "var(--text-muted)" }}
            >
              Legal
            </p>
            <h1 className="text-3xl font-bold tracking-tight mb-1">Privacy Policy</h1>
            <p
              className="text-[0.625rem] font-mono uppercase tracking-widest"
              style={{ color: "var(--text-muted)" }}
            >
              Last updated: May 2026
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="max-w-[1400px] mx-auto px-6 py-16 w-full">
          <div className="max-w-3xl">
            <div className="space-y-10">
              {sections.map(({ heading, body }, i) => (
                <div key={heading}>
                  <div className="flex items-start gap-5 mb-4">
                    <span
                      className="text-[0.5625rem] font-mono w-6 flex-shrink-0 mt-1"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <h2
                      className="text-base font-bold tracking-tight"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {heading}
                    </h2>
                  </div>

                  <div className="pl-11">
                    {Array.isArray(body) ? (
                      <ul className="space-y-2">
                        {body.map((item, j) => (
                          <li key={j} className="flex gap-3 text-sm leading-relaxed">
                            <span
                              className="flex-shrink-0 mt-1.5 w-1 h-1 rounded-full"
                              style={{ backgroundColor: "var(--accent)" }}
                            />
                            <span style={{
                              color: "var(--text-secondary)",
                              fontFamily: "Georgia, 'Times New Roman', serif",
                            }}>
                              {item}
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p
                        className="text-sm leading-relaxed"
                        style={{
                          color: "var(--text-secondary)",
                          fontFamily: "Georgia, 'Times New Roman', serif",
                        }}
                      >
                        {body}
                      </p>
                    )}
                  </div>

                  {i < sections.length - 1 && (
                    <div
                      className="mt-10 border-b"
                      style={{ borderColor: "var(--border-c)" }}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
