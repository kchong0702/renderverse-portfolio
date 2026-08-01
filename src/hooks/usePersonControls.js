import { useEffect, useState } from "react";

export const usePersonControls = () => {
  const [movement, setMovement] = useState({
    forward: false,
    backward: false,
    left: false,
    right: false,
    jump: false,
  });

  useEffect(() => {
    const keys = {
      KeyW: "forward",
      KeyS: "backward",
      KeyA: "left",
      KeyD: "right",
      Space: "jump",
    };

    const moveFieldByKey = (key) => keys[key];

    const setMovementStatus = (code, status) => {
      setMovement((movement) => ({ ...movement, [code]: status }));
    };

    const handleKeyDown = (e) => {
      setMovementStatus(moveFieldByKey(e.code), true);
    };

    const handleKeyUp = (e) => {
      setMovementStatus(moveFieldByKey(e.code), false);
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("keyup", handleKeyUp);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("keyup", handleKeyUp);
    };
  }, []);

  return movement;
};
