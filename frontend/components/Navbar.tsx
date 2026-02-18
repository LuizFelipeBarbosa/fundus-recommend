"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

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

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      {open ? (
        <>
          <path d="M6 6l12 12" />
          <path d="M18 6L6 18" />
        </>
      ) : (
        <>
          <path d="M4 7h16" />
          <path d="M4 12h16" />
          <path d="M4 17h16" />
        </>
      )}
    </svg>
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    };

    const mediaQuery = window.matchMedia("(min-width: 640px)");
    const handleMediaChange = (event: MediaQueryListEvent) => {
      if (event.matches) {
        setMenuOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handleMediaChange);
    } else {
      mediaQuery.addListener(handleMediaChange);
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      if (typeof mediaQuery.removeEventListener === "function") {
        mediaQuery.removeEventListener("change", handleMediaChange);
      } else {
        mediaQuery.removeListener(handleMediaChange);
      }
    };
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-rule/90 bg-cream/90 backdrop-blur">
      <div className="rule-accent mx-auto max-w-[1320px]" />

      <div className="mx-auto max-w-[1320px] px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-[40px_1fr_40px] items-center py-2 sm:hidden">
          <button
            type="button"
            aria-expanded={menuOpen}
            aria-controls="mobile-primary-nav"
            aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
            onClick={() => setMenuOpen((v) => !v)}
            className="flex h-10 w-10 items-center justify-center rounded-md border border-rule/90 text-ink transition-colors hover:border-accent/70 hover:text-accent"
          >
            <MenuIcon open={menuOpen} />
          </button>

          <Link href="/" className="group justify-self-center">
            <h1 className="font-display text-[30px] font-semibold tracking-[0.01em] text-ink transition-colors group-hover:text-accent">
              Nexus
            </h1>
          </Link>

          <span className="h-10 w-10" aria-hidden="true" />
        </div>

        <div className="hidden grid-cols-[1fr_auto_1fr] items-center py-2.5 sm:grid">
          <p className="justify-self-start font-sans text-[10px] uppercase tracking-[0.2em] text-ink-muted/85">
            <TodayDate />
          </p>

          <Link href="/" className="group justify-self-center">
            <h1 className="font-display text-[30px] font-semibold tracking-[0.01em] text-ink transition-colors group-hover:text-accent">
              Nexus
            </h1>
          </Link>

          <nav className="justify-self-end flex items-center gap-6">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`relative py-1 font-sans text-[11px] font-semibold uppercase tracking-[0.2em] transition-colors ${
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
      </div>

      <div className="rule mx-auto max-w-[1320px]" />

      {menuOpen && (
        <button
          type="button"
          aria-label="Close mobile navigation backdrop"
          onClick={() => setMenuOpen(false)}
          className="fixed inset-0 z-40 bg-black/30 sm:hidden"
        />
      )}

      <div
        id="mobile-primary-nav"
        className={`absolute left-0 right-0 top-full z-50 overflow-hidden border-b border-rule/90 bg-cream/95 transition-all duration-300 sm:hidden ${
          menuOpen
            ? "max-h-72 translate-y-0 opacity-100"
            : "pointer-events-none max-h-0 -translate-y-2 opacity-0"
        }`}
      >
        <nav className="mx-auto max-w-[1320px] px-4 py-3">
          <div className="space-y-1 rounded-lg border border-rule/85 bg-panel/25 p-2">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className={`block rounded-md px-3 py-2.5 font-sans text-[11px] font-semibold uppercase tracking-[0.18em] transition-colors ${
                    isActive
                      ? "bg-accent/15 text-accent"
                      : "text-ink-muted hover:bg-panel-soft/50 hover:text-ink"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </header>
  );
}
