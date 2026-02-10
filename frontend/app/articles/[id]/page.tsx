"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import {
  getArticle,
  getSessionId,
  getStoryRecommendations,
  trackView,
  ArticleDetail,
  StoryRecommendationResult,
} from "@/lib/api";
import { getDisplayTitle, hasTranslation } from "@/lib/article-utils";
import ArticleGrid from "@/components/ArticleGrid";

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function ArticleDetailPage() {
  const params = useParams();
  const id = Number(params.id);

  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [similar, setSimilar] = useState<StoryRecommendationResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);

  useEffect(() => {
    if (!id) return;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [articleData, recsData] = await Promise.all([
          getArticle(id),
          getStoryRecommendations({ similar_to: id, limit: 6 }),
        ]);
        setArticle(articleData);
        setSimilar(recsData.results);
        trackView(id, getSessionId());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load article");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="mb-4 font-display text-lg italic text-ink-muted">
          Retrieving article...
        </div>
        <div className="h-px w-32 origin-left animate-rule-draw bg-accent" />
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="border-l-[3px] border-accent bg-accent-light px-6 py-4 mt-8">
        <p className="font-sans text-xs font-bold uppercase tracking-[0.15em] text-accent">Error</p>
        <p className="mt-1 font-body text-sm text-ink-light">{error || "Article not found"}</p>
      </div>
    );
  }

  const scores = new Map<number, number>();
  for (const result of similar) {
    for (const similarArticle of result.story.articles) {
      scores.set(similarArticle.id, result.score);
    }
  }

  return (
    <div className="pt-8 opacity-0 animate-fade-in">
      <article className="mx-auto max-w-3xl">
        {/* Publisher & date */}
        <div className="mb-4 flex items-center gap-3">
          <span className="font-sans text-[11px] font-bold uppercase tracking-[0.2em] text-accent">
            {article.publisher}
          </span>
          {article.publishing_date && (
            <>
              <span className="text-rule-dark">&middot;</span>
              <span className="font-sans text-[11px] uppercase tracking-wider text-ink-muted">
                {formatDate(article.publishing_date)}
              </span>
            </>
          )}
          {article.language && (
            <>
              <span className="text-rule-dark">&middot;</span>
              <span className="font-sans text-[11px] uppercase tracking-wider text-ink-muted">
                {article.language}
              </span>
            </>
          )}
        </div>

        {/* Title */}
        <div className="mb-6 flex items-start gap-2">
          {hasTranslation(article) && (
            <button
              onClick={() => setShowOriginal((v) => !v)}
              className="mt-1.5 shrink-0 text-accent transition-colors hover:text-accent/70"
              title={showOriginal ? "Show English translation" : "Show original title"}
              aria-label={showOriginal ? "Show English translation" : "Show original title"}
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
                <circle cx="12" cy="12" r="10" />
                <path d="M2 12h20" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
            </button>
          )}
          <h1 className="font-display text-4xl font-bold leading-[1.15] tracking-tight text-ink text-balance lg:text-5xl">
            {showOriginal ? article.title : getDisplayTitle(article)}
          </h1>
        </div>

        {/* Authors */}
        {article.authors.length > 0 && (
          <p className="mb-6 font-sans text-sm italic text-ink-light">
            By {article.authors.join(", ")}
          </p>
        )}

        <div className="rule-double mb-8" />

        {/* Hero image */}
        {article.cover_image_url && (
          <div className="relative mb-8 aspect-[16/10] overflow-hidden bg-warm">
            <Image
              src={article.cover_image_url}
              alt={getDisplayTitle(article)}
              fill
              unoptimized
              className="object-cover"
            />
          </div>
        )}

        {/* Topics */}
        {article.topics.length > 0 && (
          <div className="mb-8 flex flex-wrap gap-2">
            {article.topics.map((topic) => (
              <span
                key={topic}
                className="border border-rule px-3 py-1 font-sans text-[10px] uppercase tracking-[0.15em] text-ink-muted transition-colors hover:border-accent hover:text-accent"
              >
                {topic}
              </span>
            ))}
          </div>
        )}

        {/* Body */}
        <div className="mb-12 space-y-5">
          {article.body.split("\n").map((paragraph, i) =>
            paragraph.trim() ? (
              <p key={i} className={`font-body text-[17px] leading-[1.8] text-ink-light ${i === 0 ? "first-letter:float-left first-letter:mr-2 first-letter:font-display first-letter:text-5xl first-letter:font-bold first-letter:leading-[0.85] first-letter:text-ink" : ""}`}>
                {paragraph}
              </p>
            ) : null
          )}
        </div>

        {/* Source link */}
        <div className="mb-16 border-t-2 border-ink pt-4 flex items-center justify-between">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-sans text-[11px] font-semibold uppercase tracking-[0.2em] text-accent transition-opacity hover:opacity-70"
          >
            Read Original &rarr;
          </a>
          <span className="font-sans text-[10px] uppercase tracking-wider text-ink-muted">
            Source: {article.publisher}
          </span>
        </div>
      </article>

      {/* Similar articles */}
      {similar.length > 0 && (
        <section className="border-t-2 border-ink pt-8">
          <h2 className="mb-2 font-display text-2xl font-bold italic text-ink">Related Coverage</h2>
          <p className="mb-6 font-sans text-[11px] uppercase tracking-[0.2em] text-ink-muted">
            Popular related stories
          </p>
          <div className="rule mb-8" />
          <ArticleGrid articles={similar.flatMap((result) => result.story.articles)} scores={scores} />
        </section>
      )}
    </div>
  );
}
