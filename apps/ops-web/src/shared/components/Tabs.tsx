import * as RadixTabs from "@radix-ui/react-tabs";
import { createContext, useContext, type ComponentProps } from "react";
import { cn } from "@/shared/lib/cn";
import { pillItem, pillTrack } from "./pill";

export type TabsVariant = "underline" | "pill";

const lists: Record<TabsVariant, string> = {
  underline: "border-hair flex flex-wrap gap-7 border-b",
  pill: pillTrack,
};

const tabs: Record<TabsVariant, string> = {
  underline:
    "text-ink-3 data-[state=active]:border-amber data-[state=active]:text-ink -mb-px min-h-11 cursor-pointer border-b-2 border-transparent font-medium data-[state=active]:font-semibold",
  pill: cn(
    pillItem,
    "data-[state=active]:bg-panel data-[state=active]:text-ink data-[state=active]:shadow-card data-[state=active]:font-semibold",
  ),
};

const VariantContext = createContext<TabsVariant>("underline");

export const Tabs = RadixTabs.Root;
export const TabPanel = RadixTabs.Content;

interface TabListProps extends ComponentProps<typeof RadixTabs.List> {
  variant?: TabsVariant;
}

/** A row of tabs, underlined on a rule or as pills on a chip track */
export function TabList({
  variant = "underline",
  className,
  ...props
}: TabListProps) {
  return (
    <VariantContext.Provider value={variant}>
      <RadixTabs.List className={cn(lists[variant], className)} {...props} />
    </VariantContext.Provider>
  );
}

export function Tab({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.Trigger>) {
  const variant = useContext(VariantContext);
  return (
    <RadixTabs.Trigger className={cn(tabs[variant], className)} {...props} />
  );
}
