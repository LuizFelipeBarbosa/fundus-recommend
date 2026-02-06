const API_BASE = "http://localhost:8000";

export interface ArticleSummary {
  id: number;
  url: string;
  title: string;
  title_en: string | null;
  authors: string[];
  topics: string[];
  publisher: string;
  language: string | null;
  publishing_date: string | null;
  cover_image_url: string | null;
  dedup_cluster_id: number | null;
  category: string | null;
}

export interface ArticleDetail extends ArticleSummary {
  body: string;
}

export interface ArticleListResponse {
  items: ArticleSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface SearchResult {
  article: ArticleSummary;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

export interface RecommendationResponse {
  strategy: string;
  results: SearchResult[];
}

async function fetchApi<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getArticles(params?: {
  page?: number;
  page_size?: number;
  publisher?: string;
  language?: string;
  category?: string;
}): Promise<ArticleListResponse> {
  const query: Record<string, string> = {};
  if (params?.page) query.page = String(params.page);
  if (params?.page_size) query.page_size = String(params.page_size);
  if (params?.publisher) query.publisher = params.publisher;
  if (params?.language) query.language = params.language;
  if (params?.category) query.category = params.category;
  return fetchApi<ArticleListResponse>("/articles", query);
}

export async function getArticle(id: number): Promise<ArticleDetail> {
  return fetchApi<ArticleDetail>(`/articles/${id}`);
}

export async function search(q: string, limit?: number): Promise<SearchResponse> {
  const query: Record<string, string> = { q };
  if (limit) query.limit = String(limit);
  return fetchApi<SearchResponse>("/search", query);
}

export async function getRecommendations(params?: {
  topic?: string;
  similar_to?: number;
  limit?: number;
}): Promise<RecommendationResponse> {
  const query: Record<string, string> = {};
  if (params?.topic) query.topic = params.topic;
  if (params?.similar_to) query.similar_to = String(params.similar_to);
  if (params?.limit) query.limit = String(params.limit);
  return fetchApi<RecommendationResponse>("/recommendations", query);
}

export async function getFeed(userId: string, limit?: number): Promise<RecommendationResponse> {
  const query: Record<string, string> = {};
  if (limit) query.limit = String(limit);
  return fetchApi<RecommendationResponse>(`/feed/${userId}`, query);
}
