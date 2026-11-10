import {
  DocumentView,
  PAGE_MM,
  pageCss,
  templates,
} from "@renderverse/document-renderer";
import "@renderverse/document-renderer/fonts.css";
import "@renderverse/document-renderer/styles.css";
import {
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type HTMLAttributes,
} from "react";
import { cn } from "@/shared/lib/cn";
import type { DocumentRecord } from "../api/documents";

const PX_PER_MM = 96 / 25.4;

export default function ResumePreview({
  document,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & { document: DocumentRecord["body"] }) {
  const id = useId();
  const box = useRef<HTMLDivElement>(null);
  const [available, setAvailable] = useState(0);
  const design = document.design;
  const template = templates[design.template] ?? templates.classic;
  const [width, height] = PAGE_MM[design.page_size];

  useLayoutEffect(() => {
    const observer = new ResizeObserver(() =>
      setAvailable(box.current!.clientWidth),
    );
    observer.observe(box.current!);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={box}
      data-preview={id}
      className={cn("overflow-hidden bg-white text-[#1C1917]", className)}
      {...props}
    >
      <style>{`[data-preview="${id}"] { ${pageCss(document, template)} }`}</style>
      <div
        ref={(node) => node?.setAttribute("inert", "")}
        className="pagedjs_page"
        style={{
          zoom: available / (width * PX_PER_MM) || 1,
          width: `${width}mm`,
          minHeight: `${height}mm`,
          padding: `${design.margins_mm}mm 0`,
          boxSizing: "border-box",
        }}
      >
        <DocumentView
          document={document}
          template={template}
          assetUrl={(hash) => document.assets?.[hash]?.uri ?? ""}
        />
      </div>
    </div>
  );
}
