"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getStories, StoryListResponse } from "@/lib/api";
import StoryCard from "@/components/StoryCard";
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
    <div className="pt-5 sm:pt-7">
      {/* Section header */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-4xl font-semibold leading-none text-ink sm:text-5xl">
            Today&apos;s Edition
          </h2>
          <p className="mt-1 font-sans text-[11px] uppercase tracking-[0.24em] text-ink-muted">
            {data ? `${data.total} stories in the edition` : "Loading..."}
            {lastUpdated && (
              <span className="ml-3 normal-case tracking-normal text-ink-muted/70">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {publishers.length > 0 && (
            <div className="relative">
              <label className="absolute -top-4 left-0 font-sans text-[9px] font-bold uppercase tracking-[0.2em] text-ink-muted/85">
                Source
              </label>
              <select
                value={publisher}
                onChange={handleFilterChange(setPublisher)}
                className="surface-soft appearance-none rounded-md px-2.5 py-1.5 pr-7 font-sans text-[11px] uppercase tracking-[0.14em] text-ink focus:border-accent focus:outline-none"
              >
                <option value="">All Sources</option>
                {publishers.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-ink-muted">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M2 4l3 3 3-3" /></svg>
              </span>
            </div>
          )}
          {languages.length > 0 && (
            <div className="relative">
              <label className="absolute -top-4 left-0 font-sans text-[9px] font-bold uppercase tracking-[0.2em] text-ink-muted/85">
                Language
              </label>
              <select
                value={language}
                onChange={handleFilterChange(setLanguage)}
                className="surface-soft appearance-none rounded-md px-2.5 py-1.5 pr-7 font-sans text-[11px] uppercase tracking-[0.14em] text-ink focus:border-accent focus:outline-none"
              >
                <option value="">All</option>
                {languages.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-ink-muted">
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

      <div className="rule-thick mb-5" />

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
          {data.items.length === 0 ? (
            <div className="surface rounded-xl p-10 text-center">
              <p className="font-display text-2xl text-ink-muted">No stories in this slice.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {data.items[0] && <StoryCard story={data.items[0]} variant="hero" index={0} />}

              {data.items.slice(1, 4).length > 0 && (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {data.items.slice(1, 4).map((story, idx) => (
                    <StoryCard key={story.story_id} story={story} variant="tile" index={idx + 1} />
                  ))}
                </div>
              )}

              {data.items.slice(4).length > 0 && (
                <div className="rounded-xl border border-rule/80 bg-panel/35 p-2.5 sm:p-3">
                  <div className="mb-2.5 flex items-center gap-2">
                    <span className="compact-label">More Coverage</span>
                    <div className="rule flex-1" />
                  </div>
                  <div className="grid grid-cols-1 gap-2.5 lg:grid-cols-2">
                    {data.items.slice(4).map((story, idx) => (
                      <StoryCard key={story.story_id} story={story} variant="row" index={idx + 4} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
