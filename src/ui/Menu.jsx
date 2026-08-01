import { useTranslation } from "react-i18next";
import { FaGamepad } from "react-icons/fa6";
import { useSceneControl } from "../hooks/useSceneControl";
import { useEffect, useCallback } from "react";
import { MdRunCircle } from "react-icons/md";
import { useCooldown } from "../../src/hooks/useCooldown";
import { CONFIG } from "../config-global";

export default function Menu() {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language.startsWith("zh");
  useCooldown();

  const { state, dispatch } = useSceneControl();

  const memoizedDispatch = useCallback(dispatch, [dispatch]);

  useEffect(() => {
    if (state.isLocked === true)
      document.getElementById("overlay").style.display = "none";
    else document.getElementById("overlay").style.display = "flex";
  }, [state.isLocked]);

  /* Escape Key Control */
  useEffect(() => {
    const handlePointerLockChange = () => {
      if (
        document.pointerLockElement === null &&
        state.isLocked &&
        (state.specialIsLocked === true || state.specialIsLocked === null)
      ) {
        memoizedDispatch({ type: "UNLOCK" });
      } else if (
        !state.isLocked &&
        (state.specialIsLocked === true || state.specialIsLocked === null)
      ) {
        memoizedDispatch({ type: "LOCK" });
      }
    };

    document.addEventListener("pointerlockchange", handlePointerLockChange);

    return () => {
      document.removeEventListener(
        "pointerlockchange",
        handlePointerLockChange,
      );

      document.removeEventListener("keydown", handlePointerLockChange);
    };
  }, [memoizedDispatch, state.isLocked, state.specialIsLocked]);

  return (
    <div
      id="overlay"
      style={{
        position: "absolute",
        width: "100%",
        height: "100%",
        background: "rgba(0, 0, 0, 0.5)",
        zIndex: 10,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        opacity: 0,
      }}
    >
      <div
        style={{
          padding: "1rem",
          position: "relative",
        }}
      >
        <div
          id="instructions"
          style={{ color: "white", fontFamily: "var(--font-primary)" }}
        >
          {CONFIG.isChatbotEnabled && (
            <span style={{ display: "block", marginBottom: "1rem" }}>
              {t("menu.chatWithEzbot")}
            </span>
          )}
          <span style={{ display: "block", marginBottom: "1rem" }}>
            {t("menu.move")}
          </span>
          <span style={{ display: "block", marginBottom: "1rem" }}>
            {t("menu.look")}
          </span>
          <span style={{ display: "block", marginBottom: "1rem" }}>
            {t("menu.interact")}
          </span>
          <span style={{ display: "block", marginBottom: "1rem" }}>
            {t("menu.music")}
          </span>
          {/* <span style={{ display: "block", marginBottom: "1rem" }}>
            Credit: C
          </span> */}
          {/* <span
            style={{
              display: "block",
              marginBottom: "1rem",
              // fontSize: "0.7rem",
            }}
          >
            FPS CD: 1.25sec
          </span> */}
          <div
            style={{
              position: "absolute",
              top: "-15px",
              left: 0,
              display: "flex",
              alignItems: "center",
              fontSize: "0.7rem",
              width: "max-content",
            }}
          >
            <MdRunCircle size={18} style={{ marginRight: "3px" }} />
            <span>{t("menu.escToExit")}</span>
          </div>
        </div>
        <button
          id="enter"
          style={{
            fontFamily: "var(--font-gami)",
            background: "#FFB52E",
            borderRadius: "15px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          onClick={(event) => {
            event.stopPropagation();
          }}
        >
          <FaGamepad size={30} />
          <h4
            style={{
              margin: 0,
              marginLeft: "0.5rem",
              marginTop: isZh ? 0 : "3px",
            }}
          >
            {t("menu.enter")}
          </h4>
        </button>
      </div>
    </div>
  );
}
