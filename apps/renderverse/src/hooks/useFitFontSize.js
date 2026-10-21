import { useLayoutEffect } from "react";

const overflows = (el) =>
  el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;

export const useFitFontSize = (ref, { min, max, step = 0.5 }, contentKey) => {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const fit = () => {
      el.style.fontSize = `${max}px`;
      if (!overflows(el)) return;

      // Invariant: `low` is the best candidate so far, `high` overflows
      let low = min;
      let high = max;
      while (high - low > step) {
        const mid = low + Math.floor((high - low) / step / 2) * step;
        el.style.fontSize = `${mid}px`;
        if (overflows(el)) high = mid;
        else low = mid;
      }
      el.style.fontSize = `${low}px`;

      if (import.meta.env.DEV && overflows(el)) {
        console.warn(
          `useFitFontSize: content still overflows at the ${min}px minimum and is clipped`,
        );
      }
    };

    fit();

    let cancelled = false;
    document.fonts?.ready.then(() => !cancelled && fit());

    const observer = new ResizeObserver(fit);
    observer.observe(el);

    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [ref, min, max, step, contentKey]);
};
