import styles from "./Crosshair.module.css";
import { useSceneControl } from "../../hooks/useSceneControl";

function Crosshair() {
  const { state } = useSceneControl();

  return (
    <div
      className={
        state.showCrosshair
          ? styles.crosshair
          : `${styles.crosshair} ${styles.inactive}`
      }
    ></div>
  );
}

export default Crosshair;
