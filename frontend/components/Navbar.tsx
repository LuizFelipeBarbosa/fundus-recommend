"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navLinks = [
  { href: "/", label: "Front Page" },
  { href: "/search", label: "Search" },
  { href: "/recommendations", label: "For You" },
];

function TodayDate() {
  const d = new Date();
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="relative z-50 bg-cream">
      {/* Top rule */}
      <div className="rule-accent mx-auto max-w-[1200px]" />

      {/* Dateline */}
      <div className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-2">
        <p className="font-sans text-[10px] uppercase tracking-[0.25em] text-ink-muted">
          <TodayDate />
        </p>
        <p className="font-sans text-[10px] uppercase tracking-[0.25em] text-accent">
          AI-Curated Edition
        </p>
      </div>

      <div className="rule mx-auto max-w-[1200px]" />

      {/* Masthead */}
      <div className="mx-auto max-w-[1200px] px-6 py-5 text-center">
        <Link href="/" className="group inline-block">
          <h1 className="font-display text-5xl font-black tracking-tight text-ink transition-colors group-hover:text-accent">
            The Fundus Record
          </h1>
        </Link>
        <p className="mt-1 font-sans text-[11px] uppercase tracking-[0.3em] text-ink-muted">
          News Intelligence &middot; Semantic Discovery &middot; AI Recommendations
        </p>
      </div>

      {/* Double rule */}
      <div className="mx-auto max-w-[1200px]">
        <div className="rule-thick" />
        <div className="mt-[3px] rule-thick" />
      </div>

      {/* Navigation */}
      <nav className="mx-auto max-w-[1200px] px-6">
        <div className="flex items-center justify-center gap-0">
          {navLinks.map((link, i) => (
            <div key={link.href} className="flex items-center">
              {i > 0 && (
                <span className="mx-5 text-rule-dark select-none">&bull;</span>
              )}
              <Link
                href={link.href}
                className={`relative py-3 font-sans text-xs font-semibold uppercase tracking-[0.2em] transition-colors ${
                  pathname === link.href
                    ? "text-accent"
                    : "text-ink-light hover:text-accent"
                }`}
              >
                {link.label}
                {pathname === link.href && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-accent animate-rule-draw origin-left" />
                )}
              </Link>
            </div>
          ))}
        </div>
      </nav>

      <div className="rule mx-auto max-w-[1200px]" />
    </header>
  );
}
