import { ArticleSummary } from "@/lib/api";

export function getDisplayTitle(article: ArticleSummary): string {
  return article.title_en ?? article.title;
}

export function hasTranslation(article: ArticleSummary): boolean {
  return article.title_en != null && article.title_en !== article.title;
}
