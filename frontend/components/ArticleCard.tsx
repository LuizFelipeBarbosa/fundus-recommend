import Image from "next/image";
import Link from "next/link";
import { ArticleSummary } from "@/lib/api";
import { getDisplayTitle } from "@/lib/article-utils";

function Placeholder({ publisher }: { publisher: string }) {
  const initial = publisher.charAt(0).toUpperCase();
  return (
    <div className="flex h-full w-full items-center justify-center bg-warm">
      <span className="font-display text-5xl font-bold italic text-rule-dark/60">{initial}</span>
    </div>
  );
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ArticleCard({
  article,
  score,
  featured = false,
}: {
  article: ArticleSummary;
  score?: number;
  featured?: boolean;
}) {
  if (featured) {
    return (
      <Link href={`/articles/${article.id}`} className="group block">
        <article className="relative">
          <div className="relative aspect-[21/9] overflow-hidden bg-warm">
            {article.cover_image_url ? (
              <Image
                src={article.cover_image_url}
                alt={getDisplayTitle(article)}
                fill
                unoptimized
                className="object-cover transition-transform duration-700 group-hover:scale-[1.03]"
              />
            ) : (
              <Placeholder publisher={article.publisher} />
            )}
            {/* Gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-ink/70 via-ink/20 to-transparent" />

            {/* Content overlay */}
            <div className="absolute bottom-0 left-0 right-0 p-6">
              {score !== undefined && (
                <span className="mb-3 inline-block bg-accent px-2 py-0.5 font-sans text-[10px] font-bold uppercase tracking-widest text-white">
                  {(score * 100).toFixed(0)}% Match
                </span>
              )}
              <div className="mb-2 flex items-center gap-3">
                <span className="font-sans text-[10px] font-bold uppercase tracking-[0.2em] text-white/80">
                  {article.publisher}
                </span>
                {article.publishing_date && (
                  <>
                    <span className="text-white/40">&middot;</span>
                    <span className="font-sans text-[10px] tracking-wider text-white/60">
                      {formatDate(article.publishing_date)}
                    </span>
                  </>
                )}
              </div>
              <h2 className="font-display text-2xl font-bold leading-tight text-white text-balance">
                {getDisplayTitle(article)}
              </h2>
              {article.authors.length > 0 && (
                <p className="mt-2 font-sans text-xs italic text-white/70">
                  By {article.authors.join(", ")}
                </p>
              )}
            </div>
          </div>
        </article>
      </Link>
    );
  }

  return (
    <Link href={`/articles/${article.id}`} className="group block">
      <article className="h-full">
        {/* Image */}
        <div className="relative aspect-[16/10] overflow-hidden bg-warm">
          {article.cover_image_url ? (
            <Image
              src={article.cover_image_url}
              alt={getDisplayTitle(article)}
              fill
              unoptimized
              className="object-cover transition-transform duration-700 group-hover:scale-[1.03]"
            />
          ) : (
            <Placeholder publisher={article.publisher} />
          )}
          {score !== undefined && (
            <span className="absolute right-3 top-3 bg-accent px-2 py-0.5 font-sans text-[10px] font-bold uppercase tracking-wider text-white">
              {(score * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {/* Content */}
        <div className="pt-3">
          <div className="mb-1.5 flex items-center gap-2">
            <span className="font-sans text-[10px] font-bold uppercase tracking-[0.15em] text-accent">
              {article.publisher}
            </span>
            {article.publishing_date && (
              <>
                <span className="text-rule-dark text-[10px]">/</span>
                <span className="font-sans text-[10px] tracking-wider text-ink-muted">
                  {formatDate(article.publishing_date)}
                </span>
              </>
            )}
          </div>

          <h3 className="mb-1.5 font-display text-lg font-bold leading-snug text-ink transition-colors group-hover:text-accent line-clamp-3">
            {getDisplayTitle(article)}
          </h3>

          {article.authors.length > 0 && (
            <p className="mb-2 font-sans text-xs italic text-ink-muted">
              {article.authors.join(", ")}
            </p>
          )}

          {article.topics.length > 0 && (
            <div className="flex flex-wrap gap-x-2 gap-y-1">
              {article.topics.slice(0, 3).map((topic) => (
                <span
                  key={topic}
                  className="font-sans text-[10px] uppercase tracking-wider text-ink-muted"
                >
                  {topic}
                </span>
              ))}
            </div>
          )}
        </div>
      </article>
    </Link>
  );
}
