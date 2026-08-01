import styles from "./SceneLoader.module.css";
import { useSceneLoader } from "../../hooks/useSceneLoader";
import { useEffect, useCallback } from "react";

export default function SceneLoader() {
  const { sceneLoaderState, dispatchSceneLoader } = useSceneLoader();

  const memoizedDispatch = useCallback(dispatchSceneLoader, [
    dispatchSceneLoader,
  ]);

  useEffect(() => {
    if (sceneLoaderState.isActive) {
      const timer = setTimeout(() => {
        memoizedDispatch({ type: "TOGGLE_INACTIVE" });
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [sceneLoaderState.isActive, memoizedDispatch]);

  return sceneLoaderState.isActive ? (
    <div className={styles.loadercontainer}>
      <div className={styles.body}>
        <span>
          <span>
            <span>
              <span>
                <span></span>
              </span>
            </span>
          </span>
        </span>
        <div className={styles.base}>
          <span></span>
          <div className={styles.face}></div>
        </div>
      </div>
      <div className={styles.longfazers}>
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>
      <h1>Redirecting...</h1>
    </div>
  ) : (
    <></>
  );
}
