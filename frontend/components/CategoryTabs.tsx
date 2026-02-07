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
    <div className="flex items-center gap-0 overflow-x-auto border-b border-rule">
      {CATEGORIES.map((cat) => {
        const isActive = selected === cat.value;
        return (
          <button
            key={cat.value}
            onClick={() => onChange(cat.value)}
            className={`relative shrink-0 px-4 py-2.5 font-sans text-xs font-bold uppercase tracking-[0.15em] transition-colors ${
              isActive
                ? "text-accent"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            {cat.label}
            {isActive && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-accent animate-rule-draw origin-left" />
            )}
          </button>
        );
      })}
    </div>
  );
}
