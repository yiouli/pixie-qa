/** Tab bar component */

interface Tab {
  id: string;
  label: string;
}

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onSelect: (id: string) => void;
}

export function TabBar({ tabs, activeTab, onSelect }: TabBarProps) {
  return (
    <nav className="sticky top-12.25 z-15 flex gap-0 border-b-2 border-border bg-surface px-10">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`-mb-0.5 whitespace-nowrap border-b-2 bg-transparent px-5 py-2.5 font-mono text-base font-bold transition-colors ${
            activeTab === tab.id
              ? "border-accent text-accent"
              : "border-transparent text-ink hover:text-accent"
          }`}
          onClick={() => onSelect(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
