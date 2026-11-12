import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { activeImportsQueryOptions } from "../queries/imports";

export function useActiveImports() {
  const client = useQueryClient();
  const active = useQuery(activeImportsQueryOptions);
  const seen = useRef(new Set<string>());
  useEffect(() => {
    if (!active.data) return;
    const now = new Set(active.data.map((row) => row.id));
    const finished = [...seen.current].some((id) => !now.has(id));
    seen.current = now;
    if (finished)
      for (const queryKey of [["documents"], ["profile"], ["portfolio"]])
        void client.invalidateQueries({ queryKey });
  }, [active.data, client]);
  return active;
}
