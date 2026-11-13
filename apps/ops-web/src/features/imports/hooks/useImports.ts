import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import type { ImportRecord } from "../api/imports";
import { activeImportsQueryOptions } from "../queries/imports";

export function useActiveImports() {
  const client = useQueryClient();
  const active = useQuery(activeImportsQueryOptions);
  const seen = useRef<ImportRecord[]>(undefined);
  useEffect(() => {
    if (!active.data) return;
    const before = seen.current;
    seen.current = active.data;
    if (!before) return;
    const finished = before.some(
      (row) => !active.data.some((now) => now.id === row.id),
    );
    for (const queryKey of finished
      ? [["documents"], ["profile"], ["portfolio"]]
      : [
          ["documents", "imports"],
          ["profile", "imports"],
        ])
      void client.invalidateQueries({ queryKey });
  }, [active.data, client]);
  return active;
}
