"use client";

import { FormEvent, useState } from "react";
import { getRecommendations, SearchResult } from "@/lib/api";
import ArticleGrid from "@/components/ArticleGrid";

export default function RecommendationsPage() {
  const [topic, setTopic] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
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
      const data = await getRecommendations({ topic: topic.trim(), limit: 20 });
      setResults(data.results);
      setCurrentTopic(topic.trim());
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get recommendations");
    } finally {
      setLoading(false);
    }
  }

  const scores = new Map(results.map((r) => [r.article.id, r.score]));

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Topic Recommendations</h1>

      <div className="mb-8 flex justify-center">
        <form onSubmit={handleSubmit} className="w-full max-w-2xl">
          <div className="relative">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter a topic (e.g., climate change, technology, sports)"
              className="w-full rounded-lg border border-gray-300 bg-white py-3 pl-4 pr-28 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Loading..." : "Get Recs"}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && searched && (
        <>
          <p className="mb-4 text-sm text-gray-500">
            {results.length} recommendation{results.length !== 1 ? "s" : ""} for &quot;{currentTopic}&quot;
          </p>
          <ArticleGrid articles={results.map((r) => r.article)} scores={scores} />
        </>
      )}

      {!loading && !error && !searched && (
        <p className="py-12 text-center text-gray-500">
          Enter a topic to get AI-powered article recommendations.
        </p>
      )}
    </div>
  );
}
