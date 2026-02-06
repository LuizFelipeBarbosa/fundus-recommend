"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { search, SearchResult } from "@/lib/api";
import SearchBar from "@/components/SearchBar";
import ArticleGrid from "@/components/ArticleGrid";

function SearchContent() {
  const searchParams = useSearchParams();
  const q = searchParams.get("q") || "";

  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    if (!q) {
      setResults([]);
      setSearched(false);
      return;
    }

    async function doSearch() {
      setLoading(true);
      setError(null);
      try {
        const data = await search(q, 20);
        setResults(data.results);
        setSearched(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed");
      } finally {
        setLoading(false);
      }
    }

    doSearch();
  }, [q]);

  const scores = new Map(results.map((r) => [r.article.id, r.score]));

  return (
    <div className="pt-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <h2 className="font-display text-3xl font-bold italic text-ink">Search the Archive</h2>
        <p className="mt-1 font-sans text-[11px] uppercase tracking-[0.3em] text-ink-muted">
          Semantic similarity &middot; AI-powered discovery
        </p>
      </div>

      <div className="rule mb-8" />

      <div className="mb-10 flex justify-center">
        <SearchBar initialQuery={q} />
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-24">
          <div className="mb-4 font-display text-lg italic text-ink-muted">
            Searching the archive...
          </div>
          <div className="h-px w-32 origin-left animate-rule-draw bg-accent" />
        </div>
      )}

      {error && (
        <div className="border-l-[3px] border-accent bg-accent-light px-6 py-4">
          <p className="font-sans text-xs font-bold uppercase tracking-[0.15em] text-accent">Error</p>
          <p className="mt-1 font-body text-sm text-ink-light">{error}</p>
        </div>
      )}

      {!loading && !error && searched && (
        <>
          <div className="mb-6 flex items-center gap-3">
            <div className="rule-accent w-8" />
            <p className="font-sans text-[11px] uppercase tracking-[0.2em] text-ink-muted">
              {results.length} result{results.length !== 1 ? "s" : ""} for &ldquo;{q}&rdquo;
            </p>
          </div>
          <ArticleGrid articles={results.map((r) => r.article)} scores={scores} />
        </>
      )}

      {!loading && !error && !searched && (
        <div className="py-16 text-center">
          <p className="font-display text-xl italic text-ink-muted">
            Enter a query to discover articles through meaning, not just keywords.
          </p>
          <div className="mx-auto mt-6 h-px w-24 bg-rule" />
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center py-24">
          <div className="h-px w-32 origin-left animate-rule-draw bg-accent" />
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
