import { useEffect, useState } from "react";

interface Movement {
  forward: boolean;
  backward: boolean;
  left: boolean;
  right: boolean;
  jump: boolean;
}

const keys: Record<string, keyof Movement> = {
  KeyW: "forward",
  KeyS: "backward",
  KeyA: "left",
  KeyD: "right",
  Space: "jump",
};

export const usePersonControls = () => {
  const [movement, setMovement] = useState<Movement>({
    forward: false,
    backward: false,
    left: false,
    right: false,
    jump: false,
  });

  useEffect(() => {
    const setMovementStatus = (code: string, status: boolean) => {
      const field = keys[code];
      if (!field) return;
      setMovement((movement) => ({ ...movement, [field]: status }));
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      setMovementStatus(e.code, true);
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      setMovementStatus(e.code, false);
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
