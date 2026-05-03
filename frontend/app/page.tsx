import Link from "next/link";
import {
  Activity,
  Cpu,
  Globe,
  ShieldAlert,
  Map as MapIcon,
  Database,
  Signal,
  ExternalLink,
} from "lucide-react";
import BackendWarm from "@/components/BackendWarm";
import Footer from "@/components/Footer";

const modules = [
  {
    n: "01",
    Icon: MapIcon,
    title: "Real-Time Tracking",
    desc: "Live geographic visualization of earthquakes, floods, and wildfires across the globe as they happen.",
  },
  {
    n: "02",
    Icon: Cpu,
    title: "AI Summaries",
    desc: "Automated analytical synthesis of complex disaster data into easily digestible executive briefings.",
  },
  {
    n: "03",
    Icon: Activity,
    title: "Narrative Context",
    desc: "Rich humanitarian insights fused with raw event metrics to understand the true impact on populations.",
  },
  {
    n: "04",
    Icon: Globe,
    title: "Geospatial Monitoring",
    desc: "Continuous polling of geospatial coordinates and magnitude telemetry from authoritative scientific arrays.",
  },
  {
    n: "05",
    Icon: Database,
    title: "Trusted Data Fusion",
    desc: "Interlocking data streams from the UN, NASA, and USGS structurally validated and deduplicated.",
  },
  {
    n: "06",
    Icon: ShieldAlert,
    title: "Crisis Signal Detection",
    desc: "Early warning analytics detecting anomalous geographic activity patterns before widespread reporting.",
  },
];

const partners = [
  {
    name: "GDACS",
    full: "Global Disaster Alert & Coordination System",
    href: "https://www.gdacs.org",
  },
  {
    name: "USGS",
    full: "U.S. Geological Survey",
    href: "https://www.usgs.gov",
  },
  {
    name: "ReliefWeb",
    full: "Humanitarian information service",
    href: "https://reliefweb.int",
  },
  {
    name: "NASA FIRMS",
    full: "Fire Information for Resource Management System",
    href: "https://firms.modaps.eosdis.nasa.gov",
  },
];

export default function LandingPage() {
  return (
    <div
      className="flex flex-col min-h-screen overflow-x-hidden"
      style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}
    >
      {/* Warms HuggingFace Space as soon as anyone hits the landing page */}
      <BackendWarm />

      {/* ═══════════════════════════════════════════════════════
          §1  HERO
      ═══════════════════════════════════════════════════════ */}
      <section className="max-w-[1400px] mx-auto w-full px-6 pt-20 pb-24 lg:pt-28 lg:pb-32">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-14 xl:gap-20 items-center">

          {/* Left: editorial copy */}
          <div className="lg:col-span-5 flex flex-col">

            {/* Live badge */}
            <div
              className="mb-10 self-start inline-flex items-center gap-3 px-3.5 py-1.5 border text-[0.625rem] font-mono uppercase tracking-[0.22em]"
              style={{
                borderColor: "var(--border-c)",
                color: "var(--accent)",
                backgroundColor: "color-mix(in srgb, var(--accent) 7%, transparent)",
              }}
            >
              <span className="relative flex h-1.5 w-1.5 flex-shrink-0">
                <span
                  className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                  style={{ backgroundColor: "var(--accent)" }}
                />
                <span
                  className="relative inline-flex rounded-full h-1.5 w-1.5"
                  style={{ backgroundColor: "var(--accent)" }}
                />
              </span>
              Live System Active
            </div>

            {/* Headline */}
            <h1
              className="text-5xl lg:text-6xl xl:text-[4.25rem] font-bold tracking-tight leading-[1.04] mb-7"
              style={{ color: "var(--text-primary)" }}
            >
              Global Crisis<br />
              Intelligence,<br />
              <span style={{ color: "var(--accent)" }}>Reimagined.</span>
            </h1>

            {/* Body */}
            <p
              className="text-base lg:text-[1.0625rem] leading-relaxed mb-10 max-w-md"
              style={{
                color: "var(--text-secondary)",
                fontFamily: "Georgia, 'Times New Roman', serif",
              }}
            >
              Real-time humanitarian signals, fused with AI narrative context.
              Built for a volatile world.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row gap-3 mb-14">
              <Link
                href="/dashboard"
                className="btn-accent-glow px-8 py-3.5 text-[0.6875rem] font-mono font-bold uppercase tracking-widest text-center"
                style={{ backgroundColor: "var(--accent)", color: "var(--bg-primary)" }}
              >
                Launch Dashboard
              </Link>
              <Link
                href="#architecture"
                className="px-8 py-3.5 text-[0.6875rem] font-mono uppercase tracking-widest text-center border transition-opacity hover:opacity-70"
                style={{ borderColor: "var(--border-c)", color: "var(--text-secondary)" }}
              >
                Explore Intelligence
              </Link>
            </div>

            {/* Trust chips */}
            <div className="flex flex-wrap gap-2">
              {["GDACS", "USGS", "NASA FIRMS", "ReliefWeb"].map((s) => (
                <span
                  key={s}
                  className="px-2.5 py-1 text-[0.5625rem] font-mono uppercase tracking-[0.16em] border"
                  style={{ borderColor: "var(--border-c)", color: "var(--text-muted)" }}
                >
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* Right: terminal mockup */}
          <div className="lg:col-span-7">
            <div
              className="w-full overflow-hidden border"
              style={{
                backgroundColor: "var(--bg-secondary)",
                borderColor: "var(--border-c)",
                boxShadow: "0 32px 64px -16px rgba(0,0,0,0.55), 0 0 0 1px var(--border-c)",
              }}
            >
              {/* Window chrome */}
              <div
                className="h-10 flex items-center px-4 gap-3 border-b flex-shrink-0"
                style={{ backgroundColor: "var(--bg-elevated)", borderColor: "var(--border-c)" }}
              >
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--border-c)" }} />
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--border-c)" }} />
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--accent)" }} />
                </div>
                <div
                  className="ml-auto flex items-center gap-2 text-[0.5625rem] font-mono uppercase tracking-[0.22em]"
                  style={{ color: "var(--text-muted)" }}
                >
                  <Activity className="w-3 h-3" style={{ color: "var(--accent)" }} />
                  Intelligence Terminal — v2.4.1
                </div>
              </div>

              {/* Content panes */}
              <div className="flex" style={{ height: "300px" }}>

                {/* Map pane */}
                <div
                  className="flex-1 relative overflow-hidden border-r"
                  style={{ backgroundColor: "var(--bg-primary)", borderColor: "var(--border-c)" }}
                >
                  {/* Grid overlay */}
                  <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                      backgroundImage: `linear-gradient(var(--border-c) 1px, transparent 1px), linear-gradient(90deg, var(--border-c) 1px, transparent 1px)`,
                      backgroundSize: "16% 16%",
                      opacity: 0.28,
                    }}
                  />

                  <span
                    className="absolute top-3 left-3 text-[0.5625rem] font-mono uppercase tracking-[0.18em] pointer-events-none"
                    style={{ color: "var(--text-muted)" }}
                  >
                    Live Geo-Feed
                  </span>

                  {/* Event markers */}
                  <div className="absolute pointer-events-none" style={{ top: "40%", left: "44%" }}>
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-50" style={{ backgroundColor: "#dc2626" }} />
                      <span className="relative inline-flex rounded-full h-3 w-3" style={{ backgroundColor: "#dc2626" }} />
                    </span>
                  </div>
                  <div className="absolute pointer-events-none" style={{ top: "59%", left: "70%" }}>
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: "var(--accent)" }} />
                  </div>
                  <div className="absolute pointer-events-none" style={{ top: "68%", left: "25%" }}>
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-50" style={{ backgroundColor: "#2563eb" }} />
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5" style={{ backgroundColor: "#2563eb" }} />
                    </span>
                  </div>
                  <div className="absolute pointer-events-none" style={{ top: "27%", left: "62%" }}>
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "#ea580c" }} />
                  </div>
                  <div className="absolute pointer-events-none" style={{ top: "50%", left: "14%" }}>
                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "var(--teal)" }} />
                  </div>

                  <span
                    className="absolute bottom-3 left-3 text-[0.5625rem] font-mono pointer-events-none"
                    style={{ color: "var(--text-muted)" }}
                  >
                    47.2°N 8.5°E — Active Scan
                  </span>
                </div>

                {/* Signal stream pane */}
                <div
                  className="w-48 flex-shrink-0 flex flex-col p-3 gap-2 overflow-hidden"
                  style={{ backgroundColor: "var(--bg-secondary)" }}
                >
                  <div
                    className="flex items-center gap-2 pb-2 border-b flex-shrink-0"
                    style={{ borderColor: "var(--border-c)" }}
                  >
                    <Signal className="w-3 h-3 flex-shrink-0" style={{ color: "#22c55e" }} />
                    <span
                      className="text-[0.5625rem] font-mono uppercase tracking-widest truncate"
                      style={{ color: "var(--text-muted)" }}
                    >
                      Incoming Stream
                    </span>
                  </div>

                  {[
                    { id: "EQ-2026-05", label: "Earthquake",  detail: "M6.4 · 10km depth", color: "#dc2626", opacity: 1 },
                    { id: "FL-2026-05", label: "Flood Alert",  detail: "High impact est.",  color: "#2563eb", opacity: 0.65 },
                    { id: "WF-2026-05", label: "Wildfire",     detail: "Thermal anomaly",   color: "#ea580c", opacity: 0.4 },
                  ].map((ev) => (
                    <div
                      key={ev.id}
                      className="p-2 border text-[0.625rem] font-mono flex-shrink-0"
                      style={{
                        borderColor: "var(--border-c)",
                        backgroundColor: "var(--bg-surface)",
                        opacity: ev.opacity,
                      }}
                    >
                      <div className="font-bold mb-0.5" style={{ color: ev.color }}>{ev.id}</div>
                      <div style={{ color: "var(--text-secondary)" }}>{ev.label}</div>
                      <div style={{ color: "var(--text-muted)" }}>{ev.detail}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Status bar */}
              <div
                className="h-8 border-t flex items-center px-4 gap-5 flex-shrink-0 overflow-x-hidden"
                style={{ backgroundColor: "var(--bg-elevated)", borderColor: "var(--border-c)" }}
              >
                {[
                  { label: "EQ",     value: "12", color: "#dc2626" },
                  { label: "Floods", value: "8",  color: "#2563eb" },
                  { label: "Fires",  value: "27", color: "#ea580c" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex items-center gap-1.5 flex-shrink-0">
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                    <span
                      className="text-[0.5625rem] font-mono uppercase tracking-widest whitespace-nowrap"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {label}{" "}
                      <span style={{ color: "var(--text-secondary)" }}>{value}</span>
                    </span>
                  </div>
                ))}
                <div className="ml-auto flex-shrink-0">
                  <span
                    className="text-[0.5625rem] font-mono uppercase tracking-widest"
                    style={{ color: "var(--teal)" }}
                  >
                    ● Stream Live
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════
          §2  INTELLIGENCE MODULES
      ═══════════════════════════════════════════════════════ */}
      <section
        id="architecture"
        className="w-full border-t"
        style={{ borderColor: "var(--border-c)" }}
      >
        {/* Section header */}
        <div
          className="max-w-[1400px] mx-auto px-6 py-12 border-b flex items-end justify-between"
          style={{ borderColor: "var(--border-c)" }}
        >
          <div>
            <p
              className="text-[0.5625rem] font-mono uppercase tracking-[0.28em] mb-2"
              style={{ color: "var(--text-muted)" }}
            >
              System Capabilities
            </p>
            <h2 className="text-2xl font-bold tracking-tight">Intelligence Modules</h2>
          </div>
          <span
            className="hidden md:block text-[0.5625rem] font-mono uppercase tracking-widest"
            style={{ color: "var(--text-muted)" }}
          >
            6 Core Systems
          </span>
        </div>

        {/* Module grid */}
        <div
          className="max-w-[1400px] mx-auto border-b"
          style={{ borderColor: "var(--border-c)" }}
        >
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
            style={{ borderLeft: "1px solid var(--border-c)" }}
          >
            {modules.map(({ n, Icon, title, desc }) => (
              <div key={n} className="module-card p-10 flex flex-col relative">
                <span
                  className="absolute top-7 right-7 text-[0.5625rem] font-mono"
                  style={{ color: "var(--text-muted)" }}
                >
                  {n}
                </span>
                <Icon
                  className="module-icon w-5 h-5 mb-7 flex-shrink-0"
                  style={{ color: "var(--accent)" }}
                />
                <h3 className="text-[0.8125rem] font-bold tracking-tight mb-3">{title}</h3>
                <p
                  className="text-sm leading-relaxed"
                  style={{
                    color: "var(--text-secondary)",
                    fontFamily: "Georgia, 'Times New Roman', serif",
                  }}
                >
                  {desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════
          §3  TRUSTED DATA PARTNERS
      ═══════════════════════════════════════════════════════ */}
      <section
        className="w-full border-b py-24"
        style={{ borderColor: "var(--border-c)" }}
      >
        <div className="max-w-[1400px] mx-auto px-6">
          <div className="text-center mb-16">
            <p
              className="text-[0.5625rem] font-mono uppercase tracking-[0.28em] mb-3"
              style={{ color: "var(--text-muted)" }}
            >
              Institutional Sourcing
            </p>
            <h2 className="text-2xl font-bold tracking-tight mb-3">Trusted Data Partners</h2>
            <p
              className="text-sm max-w-sm mx-auto"
              style={{
                color: "var(--text-secondary)",
                fontFamily: "Georgia, 'Times New Roman', serif",
              }}
            >
              Authoritative data streams from globally recognised monitoring institutions.
            </p>
          </div>

          <div
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px"
            style={{ backgroundColor: "var(--border-c)" }}
          >
            {partners.map(({ name, full, href }) => (
              <Link
                key={name}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="partner-card group flex flex-col justify-between p-6 sm:p-7 min-h-[140px] sm:min-h-[160px]"
              >
                <div className="partner-name text-xl font-bold mb-3 leading-none">{name}</div>
                <p
                  className="text-[0.5625rem] font-mono uppercase tracking-wider leading-relaxed mb-5"
                  style={{ color: "var(--text-muted)" }}
                >
                  {full}
                </p>
                <ExternalLink className="partner-icon w-3.5 h-3.5" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
