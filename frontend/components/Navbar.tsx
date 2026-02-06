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

      {/* Masthead with integrated nav */}
      <div className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-3">
        {/* Left: Date */}
        <p className="hidden font-sans text-[10px] uppercase tracking-[0.2em] text-ink-muted sm:block">
          <TodayDate />
        </p>

        {/* Center: Logo */}
        <Link href="/" className="group absolute left-1/2 -translate-x-1/2">
          <h1 className="font-display text-2xl font-bold tracking-tight text-ink transition-colors group-hover:text-accent">
            Nexus
          </h1>
        </Link>

        {/* Right: Nav */}
        <nav className="flex items-center gap-6">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`relative py-1 font-sans text-[11px] font-medium uppercase tracking-[0.15em] transition-colors ${
                pathname === link.href
                  ? "text-accent"
                  : "text-ink-light hover:text-accent"
              }`}
            >
              {link.label}
              {pathname === link.href && (
                <span className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent" />
              )}
            </Link>
          ))}
        </nav>
      </div>

      <div className="rule mx-auto max-w-[1200px]" />
    </header>
  );
}
