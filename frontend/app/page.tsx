"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { getStories, StoryListResponse } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import ArticleCluster from "@/components/ArticleCluster";
import CategoryTabs from "@/components/CategoryTabs";
import Pagination from "@/components/Pagination";

export default function HomePage() {
  const [data, setData] = useState<StoryListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [publisher, setPublisher] = useState("");
  const [language, setLanguage] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [publishers, setPublishers] = useState<string[]>([]);
  const [languages, setLanguages] = useState<string[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const filtersPopulated = useRef(false);

  const pageSize = 15;

  const fetchArticles = useCallback(async (isPolling = false) => {
    if (!isPolling) {
      setLoading(true);
    }
    setError(null);
    try {
      const result = await getStories({
        page,
        page_size: pageSize,
        publisher: publisher || undefined,
        language: language || undefined,
        category: category || undefined,
      });
      setData(result);
      setLastUpdated(new Date());

      if (!filtersPopulated.current && result.items.length > 0) {
        const allPublishers = Array.from(new Set(result.items.map((story) => story.lead_article.publisher))).sort();
        const allLanguages = Array.from(
          new Set(result.items.map((story) => story.lead_article.language).filter(Boolean))
        ) as string[];
        setPublishers(allPublishers);
        setLanguages(allLanguages.sort());
        filtersPopulated.current = true;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch articles");
    } finally {
      if (!isPolling) {
        setLoading(false);
      }
    }
  }, [page, publisher, language, category]);

  useEffect(() => {
    fetchArticles();

    const interval = setInterval(() => {
      fetchArticles(true);
    }, 60_000);

    return () => clearInterval(interval);
  }, [fetchArticles]);

  function handleFilterChange(setter: (v: string) => void) {
    return (e: React.ChangeEvent<HTMLSelectElement>) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="pt-8">
      {/* Section header */}
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-3xl font-bold italic text-ink">Today&apos;s Edition</h2>
          <p className="mt-1 font-sans text-xs uppercase tracking-[0.2em] text-ink-muted">
            {data ? `${data.total} stories in the edition` : "Loading..."}
            {lastUpdated && (
              <span className="ml-3 normal-case tracking-normal text-ink-muted/60">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-4">
          {publishers.length > 0 && (
            <div className="relative">
              <label className="absolute -top-4 left-0 font-sans text-[9px] font-bold uppercase tracking-[0.2em] text-ink-muted">
                Source
              </label>
              <select
                value={publisher}
                onChange={handleFilterChange(setPublisher)}
                className="appearance-none border-b-2 border-rule bg-transparent py-1.5 pr-6 font-sans text-xs text-ink focus:border-accent focus:outline-none"
              >
                <option value="">All Sources</option>
                {publishers.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 text-ink-muted">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M2 4l3 3 3-3" /></svg>
              </span>
            </div>
          )}
          {languages.length > 0 && (
            <div className="relative">
              <label className="absolute -top-4 left-0 font-sans text-[9px] font-bold uppercase tracking-[0.2em] text-ink-muted">
                Language
              </label>
              <select
                value={language}
                onChange={handleFilterChange(setLanguage)}
                className="appearance-none border-b-2 border-rule bg-transparent py-1.5 pr-6 font-sans text-xs text-ink focus:border-accent focus:outline-none"
              >
                <option value="">All</option>
                {languages.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 text-ink-muted">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M2 4l3 3 3-3" /></svg>
              </span>
            </div>
          )}
        </div>
      </div>

      <CategoryTabs
        selected={category}
        onChange={(c) => {
          setCategory(c);
          setPage(1);
        }}
      />

      <div className="rule-thick mb-8" />

      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-24">
          <div className="mb-4 font-display text-lg italic text-ink-muted">
            Composing the edition...
          </div>
          <div className="h-px w-32 origin-left animate-rule-draw bg-accent" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="border-l-[3px] border-accent bg-accent-light px-6 py-4">
          <p className="font-sans text-xs font-bold uppercase tracking-[0.15em] text-accent">Error</p>
          <p className="mt-1 font-body text-sm text-ink-light">{error}</p>
        </div>
      )}

      {/* Content */}
      {!loading && !error && data && (
        <>
          <div className="space-y-10">
            {data.items.map((story, idx) => (
              <div key={story.story_id}>
                {story.articles.length > 1 ? (
                  <ArticleCluster articles={story.articles} />
                ) : (
                  <ArticleCard
                    article={story.lead_article}
                    featured={idx === 0}
                  />
                )}
                {idx < data.items.length - 1 && (
                  <div className="rule-thick mt-10" />
                )}
              </div>
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
