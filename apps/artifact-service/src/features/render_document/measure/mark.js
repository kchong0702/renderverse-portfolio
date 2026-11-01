(host) => {
  for (const el of document.querySelectorAll("[data-field]")) {
    const field = encodeURIComponent(el.getAttribute("data-field"));
    for (const where of ["start", "end"]) {
      const marker = document.createElement("a");
      marker.href = `${host}${where}/${field}`;
      marker.style.cssText =
        "position: absolute; width: 1px; height: 1px; overflow: hidden";
      marker.textContent = " ";
      if (where === "start") {
        el.prepend(marker);
      } else {
        el.append(marker);
      }
    }
  }
};
