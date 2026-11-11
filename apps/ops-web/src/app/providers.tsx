import { QueryClientProvider } from "@tanstack/react-query";
import { LucideProvider } from "lucide-react";
import type { ReactNode } from "react";
import { queryClient } from "@/shared/api/queryClient";

export default function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <LucideProvider size={17} strokeWidth={1.8}>
        {children}
      </LucideProvider>
    </QueryClientProvider>
  );
}
