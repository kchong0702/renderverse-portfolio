import { queryOptions } from "@tanstack/react-query";
import { fetchActiveImports } from "../api/imports";

export const activeImportsQueryOptions = queryOptions({
  queryKey: ["imports", "active"],
  queryFn: ({ signal }) => fetchActiveImports(signal),
  refetchInterval: ({ state }) => (state.data?.length ? 3000 : false),
});
