"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArticleSummary } from "@/lib/api";
import { getDisplayTitle } from "@/lib/article-utils";

const SIMILAR_WEBSITES_LIMIT = 5;

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function Placeholder({ publisher }: { publisher: string }) {
  const initial = publisher.charAt(0).toUpperCase();
  return (
    <div className="flex h-full w-full items-center justify-center bg-panel-soft">
      <span className="font-display text-3xl font-semibold text-ink-muted/70">{initial}</span>
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
      <article className="rounded-md border border-transparent px-2 py-2 transition-colors hover:border-rule hover:bg-panel/35">
        <div className="mb-1 flex items-center gap-1.5">
          <span className="font-sans text-[9px] font-semibold uppercase tracking-[0.18em] text-accent">
            {article.publisher}
          </span>
          {article.publishing_date && (
            <>
              <span className="text-[9px] text-rule-dark">&middot;</span>
              <span className="font-sans text-[9px] uppercase tracking-[0.14em] text-ink-muted">
                {formatDate(article.publishing_date)}
              </span>
            </>
          )}
        </div>
        <h4 className="font-display text-[22px] font-medium leading-[1.05] text-ink transition-colors group-hover:text-accent line-clamp-1">
          {getDisplayTitle(article)}
        </h4>
        {article.authors.length > 0 && (
          <p className="mt-0.5 font-sans text-[10px] uppercase tracking-[0.14em] text-ink-muted">
            {article.authors.slice(0, 2).join(", ")}
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
    <div className="surface rounded-xl p-2.5 opacity-0 animate-fade-in sm:p-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="data-chip">{articles.length} sources</span>
        <div className="h-px flex-1 bg-rule" />
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <div className="rounded-lg border border-rule/85 bg-panel/35 p-2.5">
          <Link href={`/articles/${main.id}`} className="group block">
            <article>
              <div className="relative aspect-[16/10] overflow-hidden rounded-md bg-panel-soft">
                {main.cover_image_url ? (
                  <Image
                    src={main.cover_image_url}
                    alt={getDisplayTitle(main)}
                    fill
                    unoptimized
                    className="object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                  />
                ) : (
                  <Placeholder publisher={main.publisher} />
                )}
              </div>
              <div className="pt-2.5">
                <div className="mb-1 flex items-center gap-1.5">
                  <span className="font-sans text-[9px] font-semibold uppercase tracking-[0.18em] text-accent">
                    {main.publisher}
                  </span>
                  {main.publishing_date && (
                    <>
                      <span className="text-[9px] text-rule-dark">&middot;</span>
                      <span className="font-sans text-[9px] uppercase tracking-[0.14em] text-ink-muted">
                        {formatDate(main.publishing_date)}
                      </span>
                    </>
                  )}
                </div>
                <h3 className="font-display text-[26px] font-medium leading-[1.04] text-ink transition-colors group-hover:text-accent line-clamp-2">
                  {getDisplayTitle(main)}
                </h3>
                {main.authors.length > 0 && (
                  <p className="mt-1 font-sans text-[10px] uppercase tracking-[0.14em] text-ink-muted">
                    {main.authors.slice(0, 2).join(", ")}
                  </p>
                )}
              </div>
            </article>
          </Link>
        </div>

        <div className="space-y-1 rounded-lg border border-rule/85 bg-panel/30 p-1.5">
          {displayedOthers.map((article) => (
            <CompactEntry key={article.id} article={article} />
          ))}

          {hasMore && (
            <div className="pt-1 text-right">
              <button
                onClick={() => setShowAll((v) => !v)}
                className="font-sans text-[10px] font-semibold uppercase tracking-[0.18em] text-accent transition-colors hover:text-accent/70"
              >
                {showAll ? "Show Less" : `Read More (${hiddenCount})`}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
