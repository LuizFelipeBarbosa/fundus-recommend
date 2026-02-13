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
    <div className="mt-8 rounded-xl border border-rule/80 bg-panel/35 p-3 sm:p-4">
      <div className="flex items-center justify-between">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="rounded-md border border-rule px-3 py-1.5 font-sans text-[10px] font-semibold uppercase tracking-[0.18em] text-ink transition-colors hover:border-accent/70 hover:text-accent disabled:cursor-not-allowed disabled:border-rule/40 disabled:text-rule-dark"
        >
          &larr; Previous
        </button>

        <span className="font-sans text-[10px] uppercase tracking-[0.2em] text-ink-muted">
          Page {page} of {totalPages}
        </span>

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="rounded-md border border-rule px-3 py-1.5 font-sans text-[10px] font-semibold uppercase tracking-[0.18em] text-ink transition-colors hover:border-accent/70 hover:text-accent disabled:cursor-not-allowed disabled:border-rule/40 disabled:text-rule-dark"
        >
          Next &rarr;
        </button>
      </div>
    </div>
  );
}
