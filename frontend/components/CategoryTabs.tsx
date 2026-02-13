"use client";

const CATEGORIES = [
  { value: "", label: "All" },
  { value: "US", label: "US" },
  { value: "Global", label: "Global" },
  { value: "Business", label: "Business" },
  { value: "Technology", label: "Technology" },
  { value: "Arts", label: "Arts" },
  { value: "Sports", label: "Sports" },
  { value: "Entertainment", label: "Entertainment" },
  { value: "General", label: "General" },
];

interface CategoryTabsProps {
  selected: string;
  onChange: (category: string) => void;
}

export default function CategoryTabs({ selected, onChange }: CategoryTabsProps) {
  return (
    <div className="mb-1 flex items-center gap-1 overflow-x-auto rounded-lg border border-rule/85 bg-panel/25 p-1">
      {CATEGORIES.map((cat) => {
        const isActive = selected === cat.value;
        return (
          <button
            key={cat.value}
            onClick={() => onChange(cat.value)}
            className={`relative shrink-0 rounded-md px-3 py-1.5 font-sans text-[10px] font-semibold uppercase tracking-[0.17em] transition-all ${
              isActive
                ? "bg-accent/15 text-accent"
                : "text-ink-muted hover:bg-panel-soft/50 hover:text-ink"
            }`}
          >
            {cat.label}
            {isActive && (
              <span className="absolute bottom-0 left-2 right-2 h-[2px] bg-accent/80 animate-rule-draw origin-left" />
            )}
          </button>
        );
      })}
    </div>
  );
}
