export function SeedBadge({ seed }: { seed?: number }) {
  if (seed == null) return null
  return (
    <span title="Deterministic seed" className="text-xs opacity-70">Seed: {seed}</span>
  )
}

