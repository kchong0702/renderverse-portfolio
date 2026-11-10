const AMBER = "#B45309";

export const REWORDED = "rgba(245, 158, 11, 0.24)";

export const unzoom = "[zoom:var(--unzoom)]";

export const toolbarClass = `${unzoom} bg-panel border-hair text-ink-2 absolute z-[9] flex gap-0.5 rounded-[10px] border p-1 font-sans text-xs leading-none whitespace-nowrap shadow-[0_6px_16px_rgba(28,25,23,0.16)]`;

export const toolButtonClass =
  "inline-flex h-[30px] min-w-[30px] cursor-pointer items-center justify-center gap-1.5 rounded-md border-0 bg-transparent text-inherit";

export const dashedPillClass =
  "inline-flex cursor-pointer items-center rounded-full border border-dashed border-[#D6D3D1] bg-white px-2.5 font-sans text-[11px] font-semibold text-[#57534E]";

export const hoverOutline = (selected: boolean, hovered: boolean) =>
  selected
    ? `calc(1.5px * var(--unzoom)) solid ${AMBER}`
    : hovered
      ? "calc(1px * var(--unzoom)) dashed rgba(180, 83, 9, 0.45)"
      : undefined;

export const dropLine = "0 calc(-3px * var(--unzoom)) 0 #B45309";
