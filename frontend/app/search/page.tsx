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
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Semantic Search</h1>

      <div className="mb-8 flex justify-center">
        <SearchBar initialQuery={q} />
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && searched && (
        <>
          <p className="mb-4 text-sm text-gray-500">
            {results.length} result{results.length !== 1 ? "s" : ""} for &quot;{q}&quot;
          </p>
          <ArticleGrid articles={results.map((r) => r.article)} scores={scores} />
        </>
      )}

      {!loading && !error && !searched && (
        <p className="py-12 text-center text-gray-500">
          Enter a query to search articles using semantic similarity.
        </p>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
