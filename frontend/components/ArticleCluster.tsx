"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArticleSummary } from "@/lib/api";
import { getDisplayTitle } from "@/lib/article-utils";

const SIMILAR_WEBSITES_LIMIT = 5;

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function Placeholder({ publisher }: { publisher: string }) {
  const initial = publisher.charAt(0).toUpperCase();
  return (
    <div className="flex h-full w-full items-center justify-center bg-warm">
      <span className="font-display text-4xl font-bold italic text-rule-dark/60">
        {initial}
      </span>
    </div>
  );
}

/** Pick the best "main" article: prefer one with a cover image, then earliest by id. */
function pickMain(articles: ArticleSummary[]): {
  main: ArticleSummary;
  others: ArticleSummary[];
} {
  const withImage = articles.filter((a) => a.cover_image_url);
  const main = withImage.length > 0 ? withImage[0] : articles[0];
  const others = articles.filter((a) => a.id !== main.id);
  return { main, others };
}

function CompactEntry({ article }: { article: ArticleSummary }) {
  return (
    <Link href={`/articles/${article.id}`} className="group block">
      <article className="py-3">
        <div className="mb-1 flex items-center gap-2">
          <span className="font-sans text-[10px] font-bold uppercase tracking-[0.15em] text-accent">
            {article.publisher}
          </span>
          {article.publishing_date && (
            <>
              <span className="text-[10px] text-rule-dark">/</span>
              <span className="font-sans text-[10px] tracking-wider text-ink-muted">
                {formatDate(article.publishing_date)}
              </span>
            </>
          )}
        </div>
        <h4 className="font-display text-[15px] font-bold leading-snug text-ink transition-colors group-hover:text-accent line-clamp-1">
          {getDisplayTitle(article)}
        </h4>
        {article.authors.length > 0 && (
          <p className="mt-0.5 font-sans text-[11px] italic text-ink-muted">
            {article.authors.join(", ")}
          </p>
        )}
      </article>
    </Link>
  );
}

export default function ArticleCluster({
  articles,
}: {
  articles: ArticleSummary[];
}) {
  const { main, others } = pickMain(articles);
  const [showAll, setShowAll] = useState(false);
  
  const hasMore = others.length > SIMILAR_WEBSITES_LIMIT;
  const displayedOthers = showAll ? others : others.slice(0, SIMILAR_WEBSITES_LIMIT);
  const hiddenCount = others.length - SIMILAR_WEBSITES_LIMIT;

  return (
    <div className="opacity-0 animate-fade-in">
      {/* Sources badge */}
      <div className="mb-3 flex items-center gap-2">
        <span className="font-sans text-[11px] font-bold uppercase tracking-[0.15em] text-accent">
          {articles.length} Sources
        </span>
        <div className="h-px flex-1 bg-rule" />
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:gap-0">
        {/* Left column: main article with image */}
        <div className="lg:w-[42%] lg:pr-6">
          <Link href={`/articles/${main.id}`} className="group block">
            <article>
              <div className="relative aspect-[16/10] overflow-hidden bg-warm">
                {main.cover_image_url ? (
                  <Image
                    src={main.cover_image_url}
                    alt={getDisplayTitle(main)}
                    fill
                    unoptimized
                    className="object-cover transition-transform duration-700 group-hover:scale-[1.03]"
                  />
                ) : (
                  <Placeholder publisher={main.publisher} />
                )}
              </div>
              <div className="pt-3">
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="font-sans text-[10px] font-bold uppercase tracking-[0.15em] text-accent">
                    {main.publisher}
                  </span>
                  {main.publishing_date && (
                    <>
                      <span className="text-[10px] text-rule-dark">/</span>
                      <span className="font-sans text-[10px] tracking-wider text-ink-muted">
                        {formatDate(main.publishing_date)}
                      </span>
                    </>
                  )}
                </div>
                <h3 className="mb-1.5 font-display text-lg font-bold leading-snug text-ink transition-colors group-hover:text-accent">
                  {getDisplayTitle(main)}
                </h3>
                {main.authors.length > 0 && (
                  <p className="font-sans text-xs italic text-ink-muted">
                    By {main.authors.join(", ")}
                  </p>
                )}
              </div>
            </article>
          </Link>
        </div>

        {/* Vertical rule (desktop) */}
        <div className="hidden lg:block lg:w-px lg:self-stretch lg:bg-rule" />

        {/* Right column: compact stacked entries */}
        <div className="lg:flex-1 lg:pl-6">
          {displayedOthers.map((article, i) => (
            <div key={article.id}>
              {i > 0 && <div className="h-px bg-rule" />}
              <CompactEntry article={article} />
            </div>
          ))}
          
          {/* Read more button */}
          {hasMore && (
            <div className="mt-4 border-t border-rule pt-4">
              <button
                onClick={() => setShowAll((v) => !v)}
                className="group flex items-center gap-2 font-sans text-[11px] font-bold uppercase tracking-[0.15em] text-accent transition-colors hover:text-accent/70"
              >
                <span>{showAll ? "Show less" : `Read more (${hiddenCount} more)`}</span>
                <svg
                  className={`h-3 w-3 transition-transform ${showAll ? "rotate-180" : ""}`}
                  viewBox="0 0 10 10"
                  fill="currentColor"
                >
                  <path d="M2 4l3 3 3-3" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
