/**
 * Adds a probe span per question for each mixed-font field, each tagged with a
 * data-glyph-probe id, and returns each field's distinct characters.
 * glyphs.py then asks CDP which fonts drew each span. For "René" in Inter,
 * which lacks é, that gives:
 *
 * drawn_by = {
 *     "0:font":    {"Inter", "Times"},   # A: "René" in Inter alone, Times filled in é
 *     "0:default": {"Times"},            # B: "René" in the default font
 *     "0:0":       {"Inter"},            # "R" in Inter
 *     "0:1":       {"Inter"},            # "e"
 *     "0:2":       {"Inter"},            # "n"
 *     "0:3":       {"Times"},            # "é", which Inter couldn't draw
 * }
 *
 * NOTE. family is css name which CDP understand abd translate, but output render will be CDP own's family name
 */
(fields) => {
  const chars = fields.map(({ field, family }, i) => {
    const el = document.querySelector(`[data-field="${CSS.escape(field)}"]`);
    const style = getComputedStyle(el);
    const distinct = [...new Set([...el.textContent].filter((c) => c.trim()))];
    const addProbe = (id, text, fontFamily) => {
      const probe = document.createElement("span");
      probe.dataset.glyphProbe = id; // data-glyph-probe
      probe.textContent = text;
      probe.style.fontFamily = fontFamily;
      for (const name of ["fontWeight", "fontStyle", "fontStretch"]) {
        probe.style[name] = style[name];
      }
      document.body.append(probe);
    };
    addProbe(`${i}:font`, distinct.join(""), family);
    addProbe(`${i}:default`, distinct.join(""), "initial");
    distinct.forEach((char, j) => addProbe(`${i}:${j}`, char, family)); // i = field position, j = char position
    return distinct;
  });
  document.body.getBoundingClientRect();
  return chars;
};
