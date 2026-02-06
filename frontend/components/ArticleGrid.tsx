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
      <div className="py-12 text-center text-gray-500">
        No articles found.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {articles.map((article) => (
        <ArticleCard
          key={article.id}
          article={article}
          score={scores?.get(article.id)}
        />
      ))}
    </div>
  );
}
