export function VehicleSilhouette({ vehicle }: { vehicle: string | null }) {
  const kind = (vehicle ?? "").toLowerCase();
  if (kind.includes("heavy")) return <FalconHeavy />;
  if (kind.includes("starship")) return <Starship />;
  return <Falcon9 />;
}

function Falcon9() {
  return (
    <svg viewBox="0 0 80 320" className="h-72 w-auto text-paper/80" aria-hidden>
      <rect x="36" y="18" width="8" height="210" fill="currentColor" />
      <polygon points="40,2 52,22 28,22" fill="currentColor" />
      <rect x="28" y="70" width="24" height="6" fill="#6d8aa8" />
      <rect x="34" y="228" width="12" height="28" fill="#8b93a7" />
      <rect x="22" y="252" width="12" height="18" fill="currentColor" />
      <rect x="46" y="252" width="12" height="18" fill="currentColor" />
      <rect x="34" y="256" width="12" height="22" fill="currentColor" />
    </svg>
  );
}

function FalconHeavy() {
  return (
    <svg viewBox="0 0 120 320" className="h-72 w-auto text-paper/80" aria-hidden>
      <rect x="26" y="40" width="10" height="190" fill="currentColor" opacity="0.8" />
      <rect x="84" y="40" width="10" height="190" fill="currentColor" opacity="0.8" />
      <rect x="54" y="18" width="12" height="210" fill="currentColor" />
      <polygon points="60,2 74,22 46,22" fill="currentColor" />
      <rect x="20" y="230" width="18" height="28" fill="#8b93a7" />
      <rect x="50" y="228" width="20" height="30" fill="#8b93a7" />
      <rect x="82" y="230" width="18" height="28" fill="#8b93a7" />
    </svg>
  );
}

function Starship() {
  return (
    <svg viewBox="0 0 90 330" className="h-72 w-auto text-paper/80" aria-hidden>
      <polygon points="45,4 62,70 28,70" fill="currentColor" />
      <rect x="30" y="70" width="30" height="110" fill="currentColor" />
      <polygon points="18,175 45,155 72,175 72,250 18,250" fill="#9aa7b8" />
      <rect x="22" y="250" width="46" height="50" fill="currentColor" />
      <rect x="14" y="298" width="12" height="16" fill="#6d8aa8" />
      <rect x="39" y="300" width="12" height="18" fill="#6d8aa8" />
      <rect x="64" y="298" width="12" height="16" fill="#6d8aa8" />
    </svg>
  );
}
