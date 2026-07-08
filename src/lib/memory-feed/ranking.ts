import type { MemoryFeedCard } from "./types";

const factorWeights = {
  Relevance: 0.3,
  Urgency: 0.25,
  Importance: 0.25,
  Recency: 0.15,
  Feedback: 0.05,
} as const;

export function scoreMemoryFeedCard(card: MemoryFeedCard): number {
  const weightedScore = card.factors.reduce((total, factor) => {
    return total + factor.value * factorWeights[factor.label];
  }, 0);

  const pinBoost = card.pinned ? 12 : 0;
  const statusPenalty = card.status === "snoozed" || card.status === "archived" ? 100 : 0;

  return Math.round((weightedScore + pinBoost - statusPenalty) * 10) / 10;
}

export function rankMemoryFeedCards(cards: MemoryFeedCard[], limit = 7): MemoryFeedCard[] {
  return [...cards]
    .map((card) => ({ ...card, score: scoreMemoryFeedCard(card) }))
    .filter((card) => card.status !== "archived" && card.status !== "snoozed")
    .sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      return (b.score ?? 0) - (a.score ?? 0);
    })
    .slice(0, limit);
}
