import { useContext } from "react";
import { EditingContext } from "../editing/context";
import type { RichValue } from "../generated/document";

export const RichText = (props: { path: string; value: RichValue }) => {
  const { RichText: Slot } = useContext(EditingContext);
  return <Slot {...props} />;
};
