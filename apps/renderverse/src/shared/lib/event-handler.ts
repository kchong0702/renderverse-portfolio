import styles from "@/shared/ui/indicator/Indicator.module.css";

export const handleHoverIndicator = (
  type: "enter" | "leave",
  domele: string,
) => {
  const ele = document.getElementById(domele);

  if (ele) {
    if (type == "enter") {
      ele.classList.add(styles["active"]);
    } else {
      ele.classList.remove(styles["active"]);
    }
  }
};

export const displayInitialHiddenHtml = () => {
  const ids = ["overlay", "audio-overlay"]; // elements to opac 1

  ids.forEach((id) => {
    const ele = document.getElementById(id);
    if (ele) ele.style.opacity = "1";
  });
};

export const initEventListener = <K extends keyof DocumentEventMap>(
  type: K,
  callback: (event: DocumentEventMap[K]) => void,
) => {
  document.addEventListener(type, callback);
  return () => {
    document.removeEventListener(type, callback);
  };
};
