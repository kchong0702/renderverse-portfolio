import { useQuery } from "@tanstack/react-query";
import { CONFIG } from "@/app/config";
import type { Release } from "@/features/portfolio/types";

/** The live release query; data stays undefined when there is no release */
export const useRelease = () =>
  useQuery({
    queryKey: ["portfolio", "release"],
    queryFn: async ({ signal }): Promise<Release> => {
      const response = await fetch(
        `${CONFIG.portfolioBucketUrl}/sites/${CONFIG.portfolioUserId}/release/current.json`,
        { signal, cache: "no-cache" },
      );
      if (!response.ok) throw new Error(`No release (${response.status})`);
      return response.json();
    },
    enabled: Boolean(CONFIG.portfolioUserId),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    retry: false,
  });
