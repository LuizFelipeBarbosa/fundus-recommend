"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import { getArticle, getRecommendations, ArticleDetail, SearchResult } from "@/lib/api";
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
  const [similar, setSimilar] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [articleData, recsData] = await Promise.all([
          getArticle(id),
          getRecommendations({ similar_to: id, limit: 6 }),
        ]);
        setArticle(articleData);
        setSimilar(recsData.results);
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
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        {error || "Article not found"}
      </div>
    );
  }

  const scores = new Map(similar.map((r) => [r.article.id, r.score]));

  return (
    <article className="mx-auto max-w-4xl">
      {/* Hero image */}
      {article.cover_image_url && (
        <div className="relative mb-6 aspect-video overflow-hidden rounded-xl bg-gray-100">
          <Image
            src={article.cover_image_url}
            alt={article.title}
            fill
            unoptimized
            className="object-cover"
          />
        </div>
      )}

      {/* Metadata */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <span className="rounded-md bg-blue-100 px-2.5 py-1 text-sm font-medium text-blue-800">
          {article.publisher}
        </span>
        {article.publishing_date && (
          <span className="text-sm text-gray-500">{formatDate(article.publishing_date)}</span>
        )}
        {article.language && (
          <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600 uppercase">
            {article.language}
          </span>
        )}
      </div>

      {/* Title */}
      <h1 className="mb-4 text-3xl font-bold leading-tight text-gray-900">{article.title}</h1>

      {/* Authors */}
      {article.authors.length > 0 && (
        <p className="mb-4 text-gray-600">By {article.authors.join(", ")}</p>
      )}

      {/* Topics */}
      {article.topics.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          {article.topics.map((topic) => (
            <span key={topic} className="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700">
              {topic}
            </span>
          ))}
        </div>
      )}

      {/* Body */}
      <div className="prose prose-gray max-w-none mb-12">
        {article.body.split("\n").map((paragraph, i) => (
          paragraph.trim() ? <p key={i}>{paragraph}</p> : null
        ))}
      </div>

      {/* Source link */}
      <div className="mb-12 border-t border-gray-200 pt-4">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:underline"
        >
          Read original article
        </a>
      </div>

      {/* Similar articles */}
      {similar.length > 0 && (
        <section>
          <h2 className="mb-6 text-xl font-bold text-gray-900">Similar Articles</h2>
          <ArticleGrid articles={similar.map((r) => r.article)} scores={scores} />
        </section>
      )}
    </article>
  );
}
