(paths) => {
  const expected = new Set(paths);
  const pageWidth = document.documentElement.clientWidth;
  const bound = new Set();
  const empty = new Set();
  const overflow = new Map();
  const lines = {};

  const countLines = (el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    const rects = [...range.getClientRects()]
      .filter((r) => r.width > 0 && r.height > 0)
      .sort((a, b) => a.top - b.top);
    let count = 0;
    let bottom = -Infinity;
    for (const r of rects) {
      if (r.top >= bottom - 2) {
        count += 1;
        bottom = r.bottom;
      } else {
        bottom = Math.max(bottom, r.bottom);
      }
    }
    return count;
  };

  for (const el of document.querySelectorAll("[data-field]")) {
    const field = el.getAttribute("data-field");
    if (!expected.has(field)) continue;
    if (
      !el.checkVisibility({ opacityProperty: true, visibilityProperty: true })
    )
      continue;
    if (el.textContent.trim() === "") {
      bound.add(field);
      empty.add(field);
      continue;
    }
    const box = el.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) continue;
    bound.add(field);
    lines[field] = Math.max(lines[field] ?? 0, countLines(el));

    if (overflow.has(field)) continue;
    if (getComputedStyle(el).display !== "inline") {
      if (el.scrollWidth > el.clientWidth + 1) {
        overflow.set(field, {
          field,
          needed_px: el.scrollWidth,
          available_px: el.clientWidth,
        });
        continue;
      }
      if (el.scrollHeight > el.clientHeight + 1) {
        overflow.set(field, {
          field,
          needed_px: el.scrollHeight,
          available_px: el.clientHeight,
        });
        continue;
      }
    }
    if (box.right > pageWidth + 1) {
      overflow.set(field, {
        field,
        needed_px: box.width,
        available_px: Math.max(0, pageWidth - box.left),
      });
    }
  }

  return {
    bound: [...bound],
    empty: [...empty],
    overflow: [...overflow.values()],
    lines,
  };
};
