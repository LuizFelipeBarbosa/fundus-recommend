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
    <header className="sticky top-0 z-50 border-b border-rule/90 bg-cream/90 backdrop-blur">
      {/* Top rule */}
      <div className="rule-accent mx-auto max-w-[1320px]" />

      {/* Masthead with integrated nav */}
      <div className="mx-auto flex max-w-[1320px] items-center justify-between px-4 py-2.5 sm:px-6 lg:px-8">
        {/* Left: Date */}
        <p className="hidden font-sans text-[10px] uppercase tracking-[0.2em] text-ink-muted/85 sm:block">
          <TodayDate />
        </p>

        {/* Center: Logo */}
        <Link href="/" className="group absolute left-1/2 -translate-x-1/2">
          <h1 className="font-display text-[30px] font-semibold tracking-[0.01em] text-ink transition-colors group-hover:text-accent">
            Nexus
          </h1>
        </Link>

        {/* Right: Nav */}
        <nav className="flex items-center gap-4 sm:gap-6">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`relative py-1 font-sans text-[10px] font-semibold uppercase tracking-[0.2em] transition-colors sm:text-[11px] ${
                pathname === link.href
                  ? "text-accent"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              {link.label}
              {pathname === link.href && (
                <span className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent/90" />
              )}
            </Link>
          ))}
        </nav>
      </div>

      <div className="rule mx-auto max-w-[1320px]" />
    </header>
  );
}
