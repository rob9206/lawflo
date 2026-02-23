import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getRewardsSummary, getAchievements } from "@/api/rewards";
import type { RewardsSummary, Achievement } from "@/types";

/**
 * Returns a callback that fetches fresh reward data, diffs against
 * the stale cache, and fires toast notifications for XP earned,
 * achievements unlocked, and level-ups.
 *
 * Call the returned function inside mutation onSuccess handlers.
 * Failures are silently swallowed — rewards must never break study flows.
 *
 * @param prevSnapshot — optional pre-captured RewardsSummary. Pass this
 *   when there is an async gap between the XP-awarding API call and the
 *   toast call (e.g. `.then()` chains) to prevent background refetches
 *   from updating the cache baseline before we can diff against it.
 */
export function useRewardToast() {
  const queryClient = useQueryClient();

  return useCallback(async (prevSnapshot?: RewardsSummary) => {
    try {
      // Use caller-provided snapshot if available, otherwise read from cache
      const prevSummary = prevSnapshot ?? queryClient.getQueryData<RewardsSummary>(["rewards-summary"]);
      const prevAchievements = queryClient.getQueryData<Achievement[]>(["achievements"]) ?? [];
      const prevUnlockedKeys = new Set(
        prevAchievements.filter((a) => a.unlocked).map((a) => a.achievement_key)
      );

      // Cold-cache guard — no baseline means no meaningful diff.
      // Warm the cache silently so the next call can diff correctly.
      if (!prevSummary) {
        void queryClient.prefetchQuery({
          queryKey: ["rewards-summary"],
          queryFn: getRewardsSummary,
        });
        return;
      }

      // Fetch fresh data (updates the cache automatically)
      const [freshSummary, freshAchievements] = await Promise.all([
        queryClient.fetchQuery({
          queryKey: ["rewards-summary"],
          queryFn: getRewardsSummary,
          staleTime: 0,
        }),
        queryClient.fetchQuery({
          queryKey: ["achievements"],
          queryFn: getAchievements,
          staleTime: 0,
        }),
      ]);

      const xpDelta = freshSummary.total_earned - prevSummary.total_earned;
      const leveledUp = freshSummary.level > prevSummary.level;

      // Level-up toast (highest priority)
      if (leveledUp) {
        toast.success(`Level ${freshSummary.level} reached!`, {
          description: freshSummary.active_title,
          duration: 6000,
        });
      } else if (xpDelta > 0) {
        // XP toast
        const pct = Math.round(freshSummary.level_progress * 100);
        toast.success(`+${xpDelta} XP`, {
          description: `Level ${freshSummary.level} · ${pct}% to next level`,
          duration: 3500,
        });
      }

      // Achievement unlock toasts
      freshAchievements
        .filter((a) => a.unlocked && !prevUnlockedKeys.has(a.achievement_key))
        .forEach((a) => {
          toast("Achievement Unlocked!", {
            description: `${a.title} · +${a.points_awarded} XP`,
            duration: 7000,
          });
        });
    } catch {
      // Silently swallow — rewards must never break the study flow
    }
  }, [queryClient]);
}
