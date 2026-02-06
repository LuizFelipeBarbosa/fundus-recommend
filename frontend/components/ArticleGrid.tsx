import { ArticleSummary } from "@/lib/api";
import ArticleCard from "./ArticleCard";
import ArticleCluster from "./ArticleCluster";

type Segment =
  | { type: "standalones"; articles: ArticleSummary[] }
  | { type: "cluster"; articles: ArticleSummary[] };

/**
 * Group articles into render segments preserving original order.
 * Consecutive standalone articles become grid sections;
 * clusters (2+ articles sharing a dedup_cluster_id) become full-width blocks.
 */
function buildSegments(articles: ArticleSummary[]): Segment[] {
  // Collect clusters: map cluster_id → articles (in order of appearance)
  const clusterMap = new Map<number, ArticleSummary[]>();
  for (const a of articles) {
    if (a.dedup_cluster_id != null) {
      const list = clusterMap.get(a.dedup_cluster_id);
      if (list) list.push(a);
      else clusterMap.set(a.dedup_cluster_id, [a]);
    }
  }

  // Only treat groups of 2+ as clusters; singletons become standalones
  const realClusters = new Set<number>();
  clusterMap.forEach((list, id) => {
    if (list.length >= 2) realClusters.add(id);
  });

  // Track which cluster IDs we've already emitted
  const emittedClusters = new Set<number>();
  const segments: Segment[] = [];

  let pendingStandalones: ArticleSummary[] = [];

  const flushStandalones = () => {
    if (pendingStandalones.length > 0) {
      segments.push({ type: "standalones", articles: pendingStandalones });
      pendingStandalones = [];
    }
  };

  for (const article of articles) {
    const cid = article.dedup_cluster_id;
    if (cid != null && realClusters.has(cid)) {
      // First time we see this cluster → emit it as a block
      if (!emittedClusters.has(cid)) {
        flushStandalones();
        emittedClusters.add(cid);
        segments.push({ type: "cluster", articles: clusterMap.get(cid)! });
      }
      // Otherwise skip (already emitted with the cluster)
    } else {
      pendingStandalones.push(article);
    }
  }
  flushStandalones();

  return segments;
}

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

  const segments = buildSegments(articles);

  // Pull the first standalone for featured treatment
  let featured: ArticleSummary | null = null;
  if (segments[0]?.type === "standalones" && segments[0].articles.length > 0) {
    featured = segments[0].articles[0];
    segments[0] = {
      type: "standalones",
      articles: segments[0].articles.slice(1),
    };
    // Remove empty segment
    if (segments[0].articles.length === 0) segments.shift();
  }

  let staggerIndex = 0;

  return (
    <div className="opacity-0 animate-fade-in">
      {/* Featured article */}
      {featured && (
        <>
          <div className="mb-8">
            <ArticleCard
              article={featured}
              score={scores?.get(featured.id)}
              featured
            />
          </div>
          <div className="rule-thick mb-6" />
        </>
      )}

      {/* Segments */}
      {segments.map((segment, si) => {
        if (segment.type === "cluster") {
          return (
            <div key={`cluster-${si}`} className="mb-8">
              <ArticleCluster articles={segment.articles} />
              <div className="rule-thick mt-8" />
            </div>
          );
        }

        // Standalones → 3-column grid
        const gridArticles = segment.articles;
        const startStagger = staggerIndex;
        staggerIndex += gridArticles.length;

        return (
          <div
            key={`grid-${si}`}
            className="mb-8 grid grid-cols-1 gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-3"
          >
            {gridArticles.map((article, i) => (
              <div
                key={article.id}
                className={`opacity-0 animate-fade-up stagger-${Math.min(startStagger + i + 1, 8)} ${
                  i < gridArticles.length - 1
                    ? "border-b border-rule pb-8 lg:border-b-0 lg:pb-0"
                    : ""
                }`}
              >
                <ArticleCard article={article} score={scores?.get(article.id)} />
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
