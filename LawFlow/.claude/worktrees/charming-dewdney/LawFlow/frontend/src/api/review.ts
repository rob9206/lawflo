import api from "@/lib/api";

export interface FlashCard {
  id: string;
  chunk_id: string | null;
  subject: string;
  topic: string | null;
  front: string;
  back: string;
  card_type: "concept" | "rule" | "case_holding" | "element_list";
  ease_factor: number;
  interval_days: number;
  repetitions: number;
  next_review: string | null;
  last_reviewed: string | null;
}

export interface CardStats {
  total: number;
  due: number;
  new: number;
  learning: number;
  mature: number;
}

export async function getDueCards(subject?: string, limit = 20): Promise<FlashCard[]> {
  const { data } = await api.get("/review/due", {
    params: { subject: subject || undefined, limit },
  });
  return data;
}

export async function getCardStats(subject?: string): Promise<CardStats> {
  const { data } = await api.get("/review/stats", {
    params: { subject: subject || undefined },
  });
  return data;
}

export async function getAllCards(subject?: string, topic?: string): Promise<FlashCard[]> {
  const { data } = await api.get("/review/cards", {
    params: { subject: subject || undefined, topic: topic || undefined },
  });
  return data;
}

export async function answerCard(
  cardId: string,
  quality: number
): Promise<FlashCard> {
  const { data } = await api.post("/review/complete", {
    card_id: cardId,
    quality,
  });
  return data;
}

export async function generateCardsForSubject(
  subject: string,
  maxChunks = 5
): Promise<{ generated: number; cards: FlashCard[] }> {
  const { data } = await api.post(
    `/review/generate/subject/${subject}`,
    null,
    { params: { max_chunks: maxChunks } }
  );
  return data;
}

export async function deleteCard(cardId: string): Promise<void> {
  await api.delete(`/review/cards/${cardId}`);
}

export async function completeFlashcardSession(
  cardsReviewed: number,
  avgQuality: number
): Promise<Record<string, unknown>> {
  const { data } = await api.post("/review/complete-session", {
    cards_reviewed: cardsReviewed,
    avg_quality: avgQuality,
  });
  return data;
}
