import Image from "next/image";
import Link from "next/link";
import { NewsStory } from "@/lib/api";
import { getDisplayTitle } from "@/lib/article-utils";

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "Unknown time";
  const date = new Date(dateStr);
  const ts = date.getTime();
  if (Number.isNaN(ts)) return "Unknown time";
  const now = Date.now();
  const diffMs = now - ts;
  if (diffMs < 0) return "Just now";
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diffMs < hour) {
    const mins = Math.max(1, Math.round(diffMs / minute));
    return `${mins} min ago`;
  }
  if (diffMs < day) {
    const hours = Math.round(diffMs / hour);
    return `${hours}h ago`;
  }
  const days = Math.round(diffMs / day);
  return `${days}d ago`;
}

function Placeholder({ publisher }: { publisher: string }) {
  const initials = publisher
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <div className="flex h-full w-full items-center justify-center bg-panel-soft">
      <span className="font-sans text-xl font-bold uppercase tracking-[0.24em] text-ink-muted/80">
        {initials || "NW"}
      </span>
    </div>
  );
}

function MetaLine({ story }: { story: NewsStory }) {
  const lead = story.lead_article;
  return (
    <div className="mb-2 flex flex-wrap items-center gap-2.5">
      <span className="font-sans text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">
        {lead.publisher}
      </span>
      <span className="h-1 w-1 rounded-full bg-rule-dark" />
      <span className="font-sans text-[10px] uppercase tracking-[0.2em] text-ink-muted">
        {formatRelativeTime(lead.publishing_date)}
      </span>
      <span className="data-chip">{story.source_count} sources</span>
    </div>
  );
}

function StoryImage({
  story,
  className,
  priority = false,
}: {
  story: NewsStory;
  className?: string;
  priority?: boolean;
}) {
  const lead = story.lead_article;
  if (lead.cover_image_url) {
    return (
      <Image
        src={lead.cover_image_url}
        alt={getDisplayTitle(lead)}
        fill
        priority={priority}
        unoptimized
        className={`object-cover transition-transform duration-500 group-hover:scale-[1.035] ${className ?? ""}`}
      />
    );
  }

  return <Placeholder publisher={lead.publisher} />;
}

export default function StoryCard({
  story,
  variant,
  index = 0,
}: {
  story: NewsStory;
  variant: "hero" | "tile" | "row";
  index?: number;
}) {
  const lead = story.lead_article;
  const staggerClass = `stagger-${Math.min(index + 1, 8)}`;

  if (variant === "hero") {
    return (
      <Link href={`/articles/${lead.id}`} className={`group block opacity-0 animate-fade-up ${staggerClass}`}>
        <article className="surface overflow-hidden rounded-2xl">
          <div className="grid lg:grid-cols-12">
            <div className="p-5 sm:p-6 lg:col-span-5 lg:p-8">
              <p className="compact-label">Lead Story</p>
              <MetaLine story={story} />
              <h2 className="font-display text-[34px] font-semibold leading-[1.02] text-ink sm:text-[42px]">
                {getDisplayTitle(lead)}
              </h2>
              {lead.topics.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {lead.topics.slice(0, 4).map((topic) => (
                    <span key={topic} className="data-chip">
                      {topic}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="relative min-h-[220px] overflow-hidden lg:col-span-7 lg:min-h-[330px]">
              <StoryImage story={story} priority />
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-l from-transparent via-transparent to-cream/28" />
            </div>
          </div>
        </article>
      </Link>
    );
  }

  if (variant === "tile") {
    return (
      <Link href={`/articles/${lead.id}`} className={`group block opacity-0 animate-fade-up ${staggerClass}`}>
        <article className="surface h-full overflow-hidden rounded-xl transition-colors hover:border-accent/70">
          <div className="relative aspect-[16/10] overflow-hidden">
            <StoryImage story={story} />
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/55 via-transparent to-transparent" />
          </div>
          <div className="p-3.5">
            <MetaLine story={story} />
            <h3 className="font-display text-[27px] font-medium leading-[1.05] text-ink line-clamp-2">
              {getDisplayTitle(lead)}
            </h3>
          </div>
        </article>
      </Link>
    );
  }

  return (
    <Link href={`/articles/${lead.id}`} className={`group block opacity-0 animate-fade-up ${staggerClass}`}>
      <article className="surface flex h-full overflow-hidden rounded-xl transition-colors hover:border-accent/70">
        <div className="relative w-[38%] min-w-[136px] overflow-hidden sm:w-[34%]">
          <StoryImage story={story} />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-black/18" />
        </div>
        <div className="flex flex-1 flex-col justify-center p-3 sm:p-3.5">
          <MetaLine story={story} />
          <h3 className="font-display text-[24px] font-medium leading-[1.07] text-ink line-clamp-2">
            {getDisplayTitle(lead)}
          </h3>
        </div>
      </article>
    </Link>
  );
}
