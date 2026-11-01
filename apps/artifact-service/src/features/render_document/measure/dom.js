(paths) => {
  const expected = new Set(paths);
  const pageWidth = document.documentElement.clientWidth;
  const bound = new Set();
  const empty = new Set();
  const overflow = new Map();
  const lines = {};
  const lowContrast = new Map();

  const canvas = new OffscreenCanvas(1, 1).getContext("2d", {
    willReadFrequently: true,
  });

  const rgba = (color) => {
    canvas.clearRect(0, 0, 1, 1);
    canvas.fillStyle = "#000";
    canvas.fillStyle = color;
    canvas.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = canvas.getImageData(0, 0, 1, 1).data;
    return [r, g, b, a / 255];
  };

  const paintOver = ([r, g, b, a], [br, bg, bb, ba]) => {
    const alpha = a + ba * (1 - a);
    const mix = (top, bottom) => (top * a + bottom * ba * (1 - a)) / alpha;
    return [mix(r, br), mix(g, bg), mix(b, bb), alpha];
  };

  const luminance = ([r, g, b]) => {
    const linear = (c) => {
      const s = c / 255;
      return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
  };

  const contrast = (el) => {
    const chain = [];
    for (let node = el; node; node = node.parentElement) chain.unshift(node);
    let background = [255, 255, 255, 1];
    for (const node of chain) {
      const style = getComputedStyle(node);
      if (style.backgroundImage !== "none") return null;
      background = paintOver(rgba(style.backgroundColor), background);
    }
    const text = paintOver(rgba(getComputedStyle(el).color), background);
    const [light, dark] = [luminance(text), luminance(background)].sort(
      (a, b) => b - a,
    );
    return (light + 0.05) / (dark + 0.05);
  };

  const minimumContrast = (el) => {
    const style = getComputedStyle(el);
    const size = parseFloat(style.fontSize);
    const bold = parseInt(style.fontWeight, 10) >= 700;
    return size >= 24 || (bold && size >= 18.66) ? 3 : 4.5;
  };

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

    const ratio = lowContrast.has(field) ? null : contrast(el);
    if (ratio !== null && ratio < minimumContrast(el)) {
      lowContrast.set(field, { field, ratio: Math.round(ratio * 100) / 100 });
    }

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
    low_contrast: [...lowContrast.values()],
  };
};
