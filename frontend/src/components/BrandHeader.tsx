interface BrandHeaderProps {
  repoUrl: string;
  onFeedback: () => void;
}

const BRAND_ICON_URL =
  "https://github.com/user-attachments/assets/76c18199-f00a-4fb3-a12f-ce6c173727af";

export function BrandHeader({ repoUrl, onFeedback }: BrandHeaderProps) {
  return (
    <header className="brand-header">
      <div className="brand-lockup">
        <img
          src={BRAND_ICON_URL}
          className="brand-icon"
          alt="Pixie"
          loading="lazy"
          referrerPolicy="no-referrer"
        />
        <span className="brand-name">pixie</span>
      </div>
      <div className="brand-actions">
        <button type="button" className="btn-ghost" onClick={onFeedback}>
          Share feedback
        </button>
        <a
          className="btn-primary"
          href={repoUrl}
          target="_blank"
          rel="noreferrer"
        >
          ★ Star on GitHub
        </a>
      </div>
    </header>
  );
}
