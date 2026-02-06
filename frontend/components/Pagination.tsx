"use client";

export default function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  return (
    <div className="mt-12 border-t-2 border-ink pt-6">
      <div className="flex items-center justify-between">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="font-sans text-[11px] font-semibold uppercase tracking-[0.2em] text-ink transition-colors hover:text-accent disabled:cursor-not-allowed disabled:text-rule-dark"
        >
          &larr; Previous
        </button>

        <span className="font-sans text-[11px] uppercase tracking-[0.2em] text-ink-muted">
          Page {page} of {totalPages}
        </span>

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="font-sans text-[11px] font-semibold uppercase tracking-[0.2em] text-ink transition-colors hover:text-accent disabled:cursor-not-allowed disabled:text-rule-dark"
        >
          Next &rarr;
        </button>
      </div>
    </div>
  );
}
