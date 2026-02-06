import Image from "next/image";
import Link from "next/link";
import { ArticleSummary } from "@/lib/api";

function Placeholder({ publisher }: { publisher: string }) {
  const initial = publisher.charAt(0).toUpperCase();
  return (
    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-blue-500 to-indigo-600">
      <span className="text-4xl font-bold text-white">{initial}</span>
    </div>
  );
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ArticleCard({ article, score }: { article: ArticleSummary; score?: number }) {
  return (
    <Link href={`/articles/${article.id}`} className="group block">
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md">
        <div className="relative aspect-video overflow-hidden bg-gray-100">
          {article.cover_image_url ? (
            <Image
              src={article.cover_image_url}
              alt={article.title}
              fill
              unoptimized
              className="object-cover transition-transform group-hover:scale-105"
            />
          ) : (
            <Placeholder publisher={article.publisher} />
          )}
          {score !== undefined && (
            <span className="absolute right-2 top-2 rounded-full bg-blue-600 px-2.5 py-0.5 text-xs font-semibold text-white">
              {(score * 100).toFixed(0)}%
            </span>
          )}
        </div>

        <div className="p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
              {article.publisher}
            </span>
            {article.publishing_date && (
              <span className="text-xs text-gray-500">{formatDate(article.publishing_date)}</span>
            )}
          </div>

          <h3 className="mb-2 line-clamp-2 text-sm font-semibold text-gray-900 group-hover:text-blue-600">
            {article.title}
          </h3>

          {article.authors.length > 0 && (
            <p className="mb-2 text-xs text-gray-500">{article.authors.join(", ")}</p>
          )}

          {article.topics.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {article.topics.slice(0, 3).map((topic) => (
                <span key={topic} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                  {topic}
                </span>
              ))}
              {article.topics.length > 3 && (
                <span className="text-xs text-gray-400">+{article.topics.length - 3}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
