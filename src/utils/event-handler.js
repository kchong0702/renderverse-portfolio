import styles from "../ui/indicator/Indicator.module.css";

export const handleHoverIndicator = (type, domele) => {
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

  ids.map((id) => {
    const ele = document.getElementById(id);
    ele.style.opacity = 1;
  });
};

export const initEventListener = (type, callback) => {
  document.addEventListener(type, callback);
  return () => {
    document.removeEventListener(type, callback);
  };
};
