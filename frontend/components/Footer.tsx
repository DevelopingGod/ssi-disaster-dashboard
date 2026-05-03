import Link from "next/link";
import { ExternalLink } from "lucide-react";

const SOCIAL_LINKS = [
  { label: "LinkedIn", href: "https://www.linkedin.com/in/sankalp-indish/" },
  { label: "GitHub",   href: "https://github.com/DevelopingGod" },
];

export default function Footer() {
  return (
    <footer
      className="border-t w-full"
      style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
    >
      <div className="max-w-[1400px] mx-auto px-6 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">

          {/* Copyright */}
          <span
            className="text-[0.5625rem] font-mono uppercase tracking-widest"
            style={{ color: "var(--text-muted)" }}
          >
            © 2026 Sankalp Indish. All rights reserved.
          </span>

          {/* Made with passion */}
          <span
            className="text-[0.5625rem] font-mono tracking-wide"
            style={{ color: "var(--text-muted)" }}
          >
            🌍 Made with passion for the society
          </span>

          {/* Social links */}
          <div className="flex items-center gap-5">
            {SOCIAL_LINKS.map(({ label, href }) => (
              <Link
                key={label}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-[0.5625rem] font-mono uppercase tracking-widest transition-opacity hover:opacity-100"
                style={{ color: "var(--text-muted)" }}
              >
                <ExternalLink className="w-3 h-3" />
                {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
