"use client";

import Link from "next/link";
import { Sun, Moon, Menu, X, ExternalLink } from "lucide-react";
import { useState, useEffect } from "react";

const NAV_LINKS = [
  { label: "Home",           href: "/" },
  { label: "Dashboard",      href: "/dashboard" },
  { label: "Why Use This?",  href: "/why" },
  { label: "About",          href: "/about" },
  { label: "Privacy Policy", href: "/privacy" },
  { label: "Terms",          href: "/terms" },
];

export default function Navbar() {
  const [theme, setTheme]     = useState<"dark" | "light">("dark");
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("disaster-theme") as "dark" | "light" | null;
    if (saved) {
      setTheme(saved);
      if (saved === "light") document.documentElement.classList.add("light");
    }
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* Close drawer when viewport grows past the mobile breakpoint */
  useEffect(() => {
    const onResize = () => { if (window.innerWidth >= 1024) setMenuOpen(false); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    if (next === "light") {
      document.documentElement.classList.add("light");
    } else {
      document.documentElement.classList.remove("light");
    }
    localStorage.setItem("disaster-theme", next);
  }

  return (
    <nav
      style={{
        backgroundColor: scrolled
          ? "color-mix(in srgb, var(--bg-secondary) 97%, transparent)"
          : "color-mix(in srgb, var(--bg-secondary) 82%, transparent)",
        borderBottomColor: "var(--border-c)",
      }}
      className="sticky top-0 z-[5000] w-full border-b backdrop-blur-md transition-colors duration-300"
    >
      {/* ── Main bar ── */}
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">

        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
          <span className="relative flex h-2 w-2 flex-shrink-0">
            <span
              className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60"
              style={{ backgroundColor: "var(--accent)" }}
            />
            <span
              className="relative inline-flex rounded-full h-2 w-2"
              style={{ backgroundColor: "var(--accent)" }}
            />
          </span>
          <span
            className="font-mono font-bold tracking-[0.18em] text-[0.8125rem] uppercase"
            style={{ color: "var(--text-primary)" }}
          >
            Natural-Disaster.io
          </span>
        </Link>

        {/* Desktop nav links — hidden below lg */}
        <div className="hidden lg:flex items-center gap-6 flex-1 justify-center">
          {NAV_LINKS.map(({ label, href }) => (
            <Link key={label} href={href} className="nav-link whitespace-nowrap">
              {label}
            </Link>
          ))}
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          {/* GitHub — desktop only */}
          <Link
            href="https://github.com/DevelopingGod"
            target="_blank"
            rel="noopener noreferrer"
            className="nav-link hidden lg:flex items-center gap-1.5 whitespace-nowrap"
          >
            GitHub <ExternalLink className="w-2.5 h-2.5" />
          </Link>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="w-8 h-8 flex items-center justify-center border transition-opacity hover:opacity-70"
            style={{ borderColor: "var(--border-c)", color: "var(--text-muted)" }}
            aria-label="Toggle theme"
          >
            {theme === "dark"
              ? <Sun className="w-3.5 h-3.5" />
              : <Moon className="w-3.5 h-3.5" />}
          </button>

          {/* Launch App — desktop */}
          <Link
            href="/dashboard"
            className="btn-accent-glow hidden lg:inline-flex px-5 py-2 text-[0.6875rem] font-mono font-bold uppercase tracking-widest"
            style={{ backgroundColor: "var(--accent)", color: "var(--bg-primary)" }}
          >
            Launch App
          </Link>

          {/* Hamburger — mobile / tablet */}
          <button
            onClick={() => setMenuOpen(o => !o)}
            className="lg:hidden w-8 h-8 flex items-center justify-center border transition-opacity hover:opacity-70"
            style={{ borderColor: "var(--border-c)", color: "var(--text-muted)" }}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
          >
            {menuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* ── Mobile drawer ── */}
      {menuOpen && (
        <div
          className="lg:hidden border-t"
          style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
        >
          <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-3 flex flex-col">
            {NAV_LINKS.map(({ label, href }) => (
              <Link
                key={label}
                href={href}
                onClick={() => setMenuOpen(false)}
                className="text-[0.6875rem] font-mono uppercase tracking-widest py-3.5 border-b transition-opacity hover:opacity-70"
                style={{ borderColor: "var(--border-c)", color: "var(--text-secondary)" }}
              >
                {label}
              </Link>
            ))}

            <Link
              href="https://github.com/DevelopingGod"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-1.5 text-[0.6875rem] font-mono uppercase tracking-widest py-3.5 border-b transition-opacity hover:opacity-70"
              style={{ borderColor: "var(--border-c)", color: "var(--text-secondary)" }}
            >
              GitHub <ExternalLink className="w-2.5 h-2.5" />
            </Link>

            <Link
              href="/dashboard"
              onClick={() => setMenuOpen(false)}
              className="mt-4 mb-1 text-center py-3 text-[0.6875rem] font-mono font-bold uppercase tracking-widest transition-opacity hover:opacity-85"
              style={{ backgroundColor: "var(--accent)", color: "var(--bg-primary)" }}
            >
              Launch App
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
