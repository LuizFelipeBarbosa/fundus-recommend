"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { getArticles, ArticleListResponse } from "@/lib/api";
import ArticleGrid from "@/components/ArticleGrid";
import Pagination from "@/components/Pagination";

export default function HomePage() {
  const [data, setData] = useState<ArticleListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [publisher, setPublisher] = useState("");
  const [language, setLanguage] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [publishers, setPublishers] = useState<string[]>([]);
  const [languages, setLanguages] = useState<string[]>([]);
  const filtersPopulated = useRef(false);

  const pageSize = 20;

  const fetchArticles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getArticles({
        page,
        page_size: pageSize,
        publisher: publisher || undefined,
        language: language || undefined,
      });
      setData(result);

      if (!filtersPopulated.current && result.items.length > 0) {
        const allPublishers = Array.from(new Set(result.items.map((a) => a.publisher))).sort();
        const allLanguages = Array.from(new Set(result.items.map((a) => a.language).filter(Boolean))) as string[];
        setPublishers(allPublishers);
        setLanguages(allLanguages.sort());
        filtersPopulated.current = true;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch articles");
    } finally {
      setLoading(false);
    }
  }, [page, publisher, language]);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  function handleFilterChange(setter: (v: string) => void) {
    return (e: React.ChangeEvent<HTMLSelectElement>) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Latest Articles</h1>
        <div className="flex gap-3">
          {publishers.length > 0 && (
            <select
              value={publisher}
              onChange={handleFilterChange(setPublisher)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none"
            >
              <option value="">All Publishers</option>
              {publishers.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          )}
          {languages.length > 0 && (
            <select
              value={language}
              onChange={handleFilterChange(setLanguage)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none"
            >
              <option value="">All Languages</option>
              {languages.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          )}
        </div>
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

      {!loading && !error && data && (
        <>
          <ArticleGrid articles={data.items} />
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
