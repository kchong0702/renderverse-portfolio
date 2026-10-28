import styles from "./SceneLoader.module.css";
import { useSceneLoaderStore } from "@/experience/state/sceneLoaderStore";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export default function SceneLoader() {
  const isActive = useSceneLoaderStore((s) => s.isActive);
  const dispatch = useSceneLoaderStore((s) => s.dispatch);
  const { t } = useTranslation();

  useEffect(() => {
    if (isActive) {
      const timer = setTimeout(() => {
        dispatch({ type: "TOGGLE_INACTIVE" });
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [isActive, dispatch]);

  return isActive ? (
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
      <h1>{t("loader.redirecting")}</h1>
    </div>
  ) : (
    <></>
  );
}
