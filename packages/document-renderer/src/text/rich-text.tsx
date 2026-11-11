import type { RichValue } from "../generated/document";

export const RichText = ({ value }: { value: RichValue }) => (
  <div
    className="dr-rich"
    style={value.align ? { textAlign: value.align } : undefined}
    dangerouslySetInnerHTML={{ __html: value.html }}
  />
);
