import Link from "next/link";
import { ExternalLink } from "lucide-react";
import Footer from "@/components/Footer";

export default function AboutPage() {
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
            <h1 className="text-3xl font-bold tracking-tight">About</h1>
          </div>
        </div>

        <div className="max-w-[1400px] mx-auto px-6 py-16 w-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-14">

            {/* Left: developer profile */}
            <div className="lg:col-span-4 flex flex-col gap-6">

              {/* Identity card */}
              <div
                className="border p-8"
                style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
              >
                <p
                  className="text-[0.5625rem] font-mono uppercase tracking-[0.22em] mb-5"
                  style={{ color: "var(--text-muted)" }}
                >
                  Developer
                </p>

                <h2
                  className="text-2xl font-bold tracking-tight mb-1"
                  style={{ color: "var(--text-primary)" }}
                >
                  Sankalp Sandeep Indish
                </h2>
                <p
                  className="text-[0.6875rem] font-mono uppercase tracking-wider mb-7"
                  style={{ color: "var(--accent)" }}
                >
                  AI Engineer
                </p>

                <div className="space-y-3">
                  {[
                    ["Specialisation", "Agentic Workflows & LLM Systems"],
                    ["Stack",          "React · FastAPI · LangGraph"],
                    ["Focus",          "RAG · Tool Calling · Autonomous Agents"],
                    ["IEEE ID",        "100397836"],
                    ["Languages",      "English, German, Chinese, Marathi, Hindi"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex gap-4 text-sm">
                      <span
                        className="w-28 flex-shrink-0 font-mono text-[0.625rem] uppercase tracking-wider"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {label}
                      </span>
                      <span style={{ color: "var(--text-secondary)" }}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Social links */}
              <div className="flex flex-col gap-2">
                {[
                  {
                    label: "LinkedIn — Sankalp Indish",
                    href: "https://www.linkedin.com/in/sankalp-indish/",
                  },
                  {
                    label: "GitHub — DevelopingGod",
                    href: "https://github.com/DevelopingGod",
                  },
                ].map(({ label, href }) => (
                  <Link
                    key={label}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="border flex items-center justify-between p-4 transition-opacity hover:opacity-80"
                    style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
                  >
                    <span
                      className="text-[0.625rem] font-mono uppercase tracking-widest"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {label}
                    </span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0" style={{ color: "var(--accent)" }} />
                  </Link>
                ))}
              </div>
            </div>

            {/* Right: project details */}
            <div className="lg:col-span-8 space-y-12">

              {/* What is it */}
              <div>
                <p
                  className="text-[0.5625rem] font-mono uppercase tracking-[0.22em] mb-4"
                  style={{ color: "var(--text-muted)" }}
                >
                  The Project
                </p>
                <h3 className="text-xl font-bold tracking-tight mb-4">What is Natural-Disaster.io?</h3>
                <p
                  className="text-sm leading-relaxed"
                  style={{
                    color: "var(--text-secondary)",
                    fontFamily: "Georgia, 'Times New Roman', serif",
                  }}
                >
                  Natural-Disaster.io is an AI-powered crisis intelligence platform that merges live
                  humanitarian data with large-language-model interpretation. Users pose natural-language
                  queries — &quot;What earthquakes happened in Southeast Asia this week?&quot; — and receive
                  AI-synthesized briefings grounded in real GDACS alerts and ReliefWeb humanitarian reports,
                  rendered on a live geospatial map.
                </p>
              </div>

              {/* Data sources */}
              <div>
                <p
                  className="text-[0.5625rem] font-mono uppercase tracking-[0.22em] mb-6"
                  style={{ color: "var(--text-muted)" }}
                >
                  Authoritative Data Sources
                </p>
                <div className="space-y-2">
                  {[
                    { name: "GDACS",      role: "Global real-time disaster alerts",        href: "https://www.gdacs.org",                   status: "live" },
                    { name: "USGS",       role: "Seismic & geophysical telemetry",         href: "https://www.usgs.gov",                    status: "live" },
                    { name: "NASA FIRMS", role: "Active fire detection via satellite",     href: "https://firms.modaps.eosdis.nasa.gov",    status: "live" },
                    { name: "ReliefWeb",  role: "Humanitarian narrative reports",          href: "https://reliefweb.int",                   status: "live" },
                  ].map(({ name, role, href, status }) => (
                    <Link
                      key={name}
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between border px-5 py-3.5 transition-opacity hover:opacity-80"
                      style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
                    >
                      <div className="flex items-center gap-5">
                        <span
                          className="w-24 text-[0.6875rem] font-mono font-bold uppercase tracking-wider flex-shrink-0"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {name}
                        </span>
                        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                          {role}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <span
                          className="text-[0.5rem] font-mono uppercase tracking-widest"
                          style={{ color: status === "live" ? "var(--teal)" : "var(--text-muted)" }}
                        >
                          {status}
                        </span>
                        <ExternalLink className="w-3 h-3" style={{ color: "var(--border-c)" }} />
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
