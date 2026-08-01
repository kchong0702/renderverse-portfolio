import { FaGamepad } from "react-icons/fa6";
import { useSceneControl } from "../hooks/useSceneControl";
import { useEffect, useCallback } from "react";
import { MdRunCircle } from "react-icons/md";
import { useCooldown } from "../../src/hooks/useCooldown";

export default function Menu() {
  useCooldown(); // Reset cooldown (GLOBAL)

  const { state, dispatch } = useSceneControl();

  const memoizedDispatch = useCallback(dispatch, [dispatch]);

  useEffect(() => {
    if (state.isLocked === true)
      document.getElementById("overlay").style.display = "none";
    else document.getElementById("overlay").style.display = "flex";
  }, [state.isLocked]);

  /* Escape Key Control */
  useEffect(() => {
    // const handlePointerLockChange = () => {
    //   if (
    //     document.pointerLockElement === null &&
    //     state.isLocked &&
    //     (state.specialIsLocked === true || state.specialIsLocked === null)
    //   ) {
    //     memoizedDispatch({ type: "UNLOCK" });
    //   } else if (!state.isLocked && (state.specialIsLocked === true || state.specialIsLocked === null)) {
    //     memoizedDispatch({ type: "LOCK" });
    //   }
    // };

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
          <span style={{ display: "block", marginBottom: "1rem" }}>
            Chat with Ezbot: C
          </span>
          <span style={{ display: "block", marginBottom: "1rem" }}>
            Move: WASD
          </span>
          <span style={{ display: "block", marginBottom: "1rem" }}>
            Look: MOUSE
          </span>
          <span style={{ display: "block", marginBottom: "1rem" }}>
            Interact: LMB
          </span>
          <span style={{ display: "block", marginBottom: "1rem" }}>
            Music: M
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
            <span>ESC to exit</span>
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
            event.stopPropagation;
          }}
        >
          <FaGamepad size={30} />
          <h4
            style={{
              margin: 0,
              marginLeft: "0.5rem",
              paddingTop: "0.5rem",
            }}
          >
            Enter
          </h4>
        </button>
      </div>
    </div>
  );
}
