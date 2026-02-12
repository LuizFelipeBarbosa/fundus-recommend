"use client";

import { FormEvent, useState } from "react";
import { getStoryRecommendations, StoryRecommendationResult } from "@/lib/api";
import ArticleGrid from "@/components/ArticleGrid";

export default function RecommendationsPage() {
  const [topic, setTopic] = useState("");
  const [results, setResults] = useState<StoryRecommendationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [currentTopic, setCurrentTopic] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await getStoryRecommendations({ topic: topic.trim(), limit: 20 });
      setResults(data.results);
      setCurrentTopic(topic.trim());
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get recommendations");
    } finally {
      setLoading(false);
    }
  }

  const scores = new Map<number, number>();
  for (const result of results) {
    for (const article of result.story.articles) {
      scores.set(article.id, result.score);
    }
  }

  return (
    <div className="pt-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <h2 className="font-display text-3xl font-bold italic text-ink">For You</h2>
        <p className="mt-1 font-sans text-[11px] uppercase tracking-[0.3em] text-ink-muted">
          Topic-driven recommendations &middot; Curated by AI
        </p>
      </div>

      <div className="rule mb-8" />

      {/* Topic input */}
      <div className="mb-10 flex justify-center">
        <form onSubmit={handleSubmit} className="w-full max-w-2xl">
          <div className="relative">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter a topic &mdash; e.g., climate policy, AI regulation, space exploration"
              className="w-full border-b-2 border-rule bg-transparent py-3.5 pl-0 pr-24 font-body text-base text-ink placeholder-ink-muted/50 transition-colors focus:border-accent focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="absolute right-0 top-1/2 -translate-y-1/2 font-sans text-[10px] font-bold uppercase tracking-[0.2em] text-accent transition-opacity hover:opacity-70 disabled:opacity-40"
            >
              {loading ? "Loading..." : "Recommend"}
            </button>
          </div>
        </form>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-24">
          <div className="mb-4 font-display text-lg italic text-ink-muted">
            Curating recommendations...
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
              {results.length} story recommendation{results.length !== 1 ? "s" : ""} for &ldquo;{currentTopic}&rdquo;
            </p>
          </div>
          <ArticleGrid articles={results.flatMap((result) => result.story.articles)} scores={scores} />
        </>
      )}

      {!loading && !error && !searched && (
        <div className="py-16 text-center">
          <p className="font-display text-xl italic text-ink-muted">
            Tell us what interests you. We&apos;ll find the stories that matter.
          </p>
          <div className="mx-auto mt-6 h-px w-24 bg-rule" />
        </div>
      )}
    </div>
  );
}
