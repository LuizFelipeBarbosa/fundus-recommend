import { ArticleSummary } from "@/lib/api";
import ArticleCard from "./ArticleCard";

export default function ArticleGrid({
  articles,
  scores,
}: {
  articles: ArticleSummary[];
  scores?: Map<number, number>;
}) {
  if (articles.length === 0) {
    return (
      <div className="py-16 text-center">
        <p className="font-display text-xl italic text-ink-muted">No articles found.</p>
        <div className="mx-auto mt-4 h-px w-24 bg-rule" />
      </div>
    );
  }

  // First article gets featured treatment
  const featured = articles[0];
  const rest = articles.slice(1);

  return (
    <div className="opacity-0 animate-fade-in">
      {/* Featured article */}
      <div className="mb-8">
        <ArticleCard
          article={featured}
          score={scores?.get(featured.id)}
          featured
        />
      </div>

      <div className="rule-thick mb-6" />

      {/* Remaining articles in newspaper columns */}
      <div className="grid grid-cols-1 gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
        {rest.map((article, i) => (
          <div
            key={article.id}
            className={`opacity-0 animate-fade-up stagger-${Math.min(i + 1, 8)} ${
              i < rest.length - 1 ? "border-b border-rule pb-8 lg:border-b-0 lg:pb-0" : ""
            }`}
          >
            <ArticleCard article={article} score={scores?.get(article.id)} />
          </div>
        ))}
      </div>
    </div>
  );
}
