import styles from "./Crosshair.module.css";
import { useSceneStore } from "@/experience/state/sceneStore";

function Crosshair() {
  const showCrosshair = useSceneStore((s) => s.showCrosshair);

  return (
    <div
      className={
        showCrosshair
          ? styles.crosshair
          : `${styles.crosshair} ${styles.inactive}`
      }
    ></div>
  );
}

export default Crosshair;
