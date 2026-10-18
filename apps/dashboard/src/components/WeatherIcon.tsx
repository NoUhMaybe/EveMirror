export function WeatherIcon({ condition }: { condition?: string | null }) {
  const rain = /rain|drizzle|shower|storm/i.test(condition ?? "");
  const cloud = /cloud|fog|overcast/i.test(condition ?? "") || rain;
  return (
    <svg
      className="weather-icon"
      viewBox="0 0 48 48"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    >
      {!cloud && (
        <>
          <circle cx="24" cy="24" r="9" />
          <path d="M24 5v5m0 28v5M5 24h5m28 0h5M10 10l4 4m20 20l4 4M10 38l4-4m20-20l4-4" />
        </>
      )}
      {cloud && (
        <path d="M13 32a8 8 0 1 1 1-16 11 11 0 0 1 21 3 7 7 0 0 1 0 14H13" />
      )}
      {rain && <path d="M17 38l-2 5m11-5l-2 5m11-5l-2 5" />}
    </svg>
  );
}
