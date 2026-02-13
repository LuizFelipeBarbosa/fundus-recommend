import Image from "next/image";
import Link from "next/link";
import { ArticleSummary } from "@/lib/api";
import { getDisplayTitle } from "@/lib/article-utils";

type CardVariant = "feature" | "compact" | "row";

function Placeholder({ publisher }: { publisher: string }) {
  const initial = publisher.charAt(0).toUpperCase();
  return (
    <div className="flex h-full w-full items-center justify-center bg-panel-soft">
      <span className="font-display text-4xl font-semibold text-ink-muted/70">{initial}</span>
    </div>
  );
}

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

function Meta({
  article,
  score,
  small = false,
}: {
  article: ArticleSummary;
  score?: number;
  small?: boolean;
}) {
  return (
    <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
      <span className={`font-sans font-semibold uppercase tracking-[0.18em] text-accent ${small ? "text-[9px]" : "text-[10px]"}`}>
        {article.publisher}
      </span>
      {article.publishing_date && (
        <>
          <span className={`text-rule-dark ${small ? "text-[9px]" : "text-[10px]"}`}>&middot;</span>
          <span className={`font-sans uppercase tracking-[0.16em] text-ink-muted ${small ? "text-[9px]" : "text-[10px]"}`}>
            {formatDate(article.publishing_date)}
          </span>
        </>
      )}
      {score !== undefined && <span className="data-chip">{(score * 100).toFixed(0)}% match</span>}
    </div>
  );
}

function renderImage(article: ArticleSummary, title: string, className?: string) {
  if (article.cover_image_url) {
    return (
      <Image
        src={article.cover_image_url}
        alt={title}
        fill
        unoptimized
        className={`object-cover transition-transform duration-500 group-hover:scale-[1.03] ${className ?? ""}`}
      />
    );
  }
  return <Placeholder publisher={article.publisher} />;
}

export default function ArticleCard({
  article,
  score,
  featured = false,
  variant = "compact",
}: {
  article: ArticleSummary;
  score?: number;
  featured?: boolean;
  variant?: CardVariant;
}) {
  const resolvedVariant: CardVariant = featured ? "feature" : variant;
  const title = getDisplayTitle(article);

  if (resolvedVariant === "feature") {
    return (
      <Link href={`/articles/${article.id}`} className="group block">
        <article className="surface overflow-hidden rounded-2xl">
          <div className="grid lg:grid-cols-12">
            <div className="p-5 sm:p-6 lg:col-span-5 lg:p-7">
              <Meta article={article} score={score} />
              <h2 className="font-display text-[34px] font-semibold leading-[1.02] text-ink sm:text-[42px]">
                {title}
              </h2>
              {article.authors.length > 0 && (
                <p className="mt-2 font-sans text-[11px] uppercase tracking-[0.14em] text-ink-muted">
                  {article.authors.slice(0, 2).join(", ")}
                </p>
              )}
            </div>
            <div className="relative min-h-[220px] overflow-hidden lg:col-span-7 lg:min-h-[320px]">
              {renderImage(article, title)}
            </div>
          </div>
        </article>
      </Link>
    );
  }

  if (resolvedVariant === "row") {
    return (
      <Link href={`/articles/${article.id}`} className="group block">
        <article className="surface flex h-full overflow-hidden rounded-lg transition-colors hover:border-accent/70">
          <div className="relative w-[36%] min-w-[120px] overflow-hidden">
            {renderImage(article, title)}
          </div>
          <div className="flex flex-1 flex-col justify-center p-3">
            <Meta article={article} score={score} small />
            <h3 className="font-display text-[23px] font-medium leading-[1.06] text-ink line-clamp-2">
              {title}
            </h3>
            {article.topics.length > 0 && (
              <p className="mt-1 font-sans text-[9px] uppercase tracking-[0.15em] text-ink-muted">
                {article.topics.slice(0, 2).join(" / ")}
              </p>
            )}
          </div>
        </article>
      </Link>
    );
  }

  return (
    <Link href={`/articles/${article.id}`} className="group block h-full">
      <article className="surface flex h-full flex-col overflow-hidden rounded-lg transition-colors hover:border-accent/70">
        <div className="relative aspect-[16/9] overflow-hidden">
          {renderImage(article, title)}
        </div>
        <div className="flex flex-1 flex-col p-3">
          <Meta article={article} score={score} small />
          <h3 className="font-display text-[25px] font-medium leading-[1.06] text-ink line-clamp-2">
            {title}
          </h3>
          {article.authors.length > 0 && (
            <p className="mt-1 font-sans text-[10px] uppercase tracking-[0.14em] text-ink-muted">
              {article.authors[0]}
            </p>
          )}
          {article.topics.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {article.topics.slice(0, 2).map((topic) => (
                <span key={topic} className="data-chip">
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
