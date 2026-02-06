"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export default function SearchBar({
  compact = false,
  initialQuery = "",
}: {
  compact?: boolean;
  initialQuery?: string;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [focused, setFocused] = useState(false);
  const router = useRouter();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className={compact ? "max-w-sm" : "w-full max-w-2xl"}>
      <div className={`relative transition-all duration-300 ${focused ? "scale-[1.01]" : ""}`}>
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-muted">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Search the archive..."
          className={`w-full border-b-2 border-rule bg-transparent pl-11 pr-4 font-body text-ink placeholder-ink-muted/60 transition-colors focus:border-accent focus:outline-none ${
            compact ? "py-2 text-sm" : "py-3.5 text-base"
          }`}
        />
        {query && (
          <button
            type="submit"
            className="absolute right-0 top-1/2 -translate-y-1/2 font-sans text-[10px] font-bold uppercase tracking-[0.2em] text-accent transition-opacity hover:opacity-70"
          >
            Search
          </button>
        )}
      </div>
    </form>
  );
}
