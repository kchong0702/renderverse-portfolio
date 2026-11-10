import type { TemplateSpec } from "@renderverse/document-renderer";
import { sideColumn, structureOf } from "../lib/templates";

const line = (width: string) => (
  <span className="h-[3px] rounded-sm bg-[#E7E5E4]" style={{ width }} />
);

export default function TemplateThumbnail({
  template,
}: {
  template: TemplateSpec;
}) {
  const accent = template.accent;
  const structure = structureOf(template);
  const flow = (sideColumn(template) ?? 1) === 1 ? "row" : "row-reverse";

  if (structure === "band")
    return (
      <span className="flex flex-1" style={{ flexDirection: flow }}>
        <span
          className="flex w-[34%] flex-col items-center gap-1 px-[5px] py-[7px]"
          style={{ background: accent }}
        >
          <span className="size-[18px] rounded-full bg-white" />
          <span className="h-[5px] w-[80%] rounded-sm bg-white" />
          <span className="h-[3px] w-[60%] rounded-sm bg-white/60" />
          <span className="mt-[3px] h-[3px] w-[70%] rounded-sm bg-white/60" />
          <span className="h-[3px] w-[55%] rounded-sm bg-white/60" />
        </span>
        <span className="flex flex-1 flex-col gap-1 px-[7px] py-2">
          {line("100%")}
          <span
            className="mt-[3px] h-1 w-[40%] rounded-sm"
            style={{ background: accent }}
          />
          {line("100%")}
          {line("80%")}
          <span
            className="mt-[3px] h-1 w-[40%] rounded-sm"
            style={{ background: accent }}
          />
          {line("70%")}
        </span>
      </span>
    );

  if (structure === "header")
    return (
      <>
        <span className="flex items-center gap-1.5 border-b border-[#E7E5E4] pb-[5px]">
          <span className="flex flex-1 flex-col gap-[3px]">
            <span className="h-1.5 w-[80%] rounded-sm bg-[#1E3A5F]" />
            <span
              className="h-[3px] w-1/2 rounded-sm"
              style={{ background: accent }}
            />
          </span>
          <span
            className="size-5 flex-none rounded-full border-2 bg-[#D6DEE7]"
            style={{ borderColor: accent }}
          />
          <span className="flex flex-1 flex-col items-end gap-[3px]">
            <span className="h-[3px] w-[70%] rounded-sm bg-[#D6D3D1]" />
            <span className="h-[3px] w-[60%] rounded-sm bg-[#D6D3D1]" />
          </span>
        </span>
        <span className="flex flex-1 gap-1.5">
          <span className="flex flex-[2] flex-col gap-1">
            <span
              className="h-1 w-[45%] border-l-[3px] bg-[#44403C]"
              style={{ borderColor: accent }}
            />
            {line("100%")}
            {line("80%")}
          </span>
          <span className="flex flex-1 flex-col gap-1 border-l border-[#E7E5E4] pl-[5px]">
            <span className="h-1 w-[60%] bg-[#44403C]" />
            <span className="flex gap-0.5">
              <span className="h-[5px] w-[40%] rounded-[3px] bg-[#7A93B5]" />
              <span className="h-[5px] w-[35%] rounded-[3px] bg-[#7A93B5]" />
            </span>
          </span>
        </span>
      </>
    );

  const align =
    template.regions.top?.align === "center" ? "center" : "flex-start";
  const titleAlign =
    template.regions.main?.title === "rule-both" ? "center" : "flex-start";
  return (
    <>
      <span
        className="h-[7px] w-[46%] rounded-sm"
        style={{ alignSelf: align, background: accent }}
      />
      <span
        className="h-1 w-[30%] rounded-sm bg-[#D6D3D1]"
        style={{ alignSelf: align }}
      />
      <span className="mt-1 flex flex-1 flex-col gap-1">
        <span
          className="h-1 w-[34%] rounded-sm"
          style={{ alignSelf: titleAlign, background: accent }}
        />
        {line("100%")}
        {line("86%")}
        <span
          className="mt-1 h-1 w-[34%] rounded-sm"
          style={{ alignSelf: titleAlign, background: accent }}
        />
        {line("100%")}
        {line("72%")}
      </span>
    </>
  );
}
