"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export default function SearchBar({ compact = false, initialQuery = "" }: { compact?: boolean; initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const router = useRouter();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className={compact ? "max-w-md" : "w-full max-w-2xl"}>
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search articles..."
          className={`w-full rounded-lg border border-gray-300 bg-white pl-4 pr-10 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 ${
            compact ? "py-2 text-sm" : "py-3 text-base"
          }`}
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-gray-400 hover:text-blue-600"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
      </div>
    </form>
  );
}
