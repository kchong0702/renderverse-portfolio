import { useEffect } from "react";
import { useModal } from "../../hooks/useModal";
import { useSceneControl } from "../../hooks/useSceneControl";
// import { useChatControl } from "../../hooks/useChatControl";

export default function Credit() {
  const { dispatchModal } = useModal();
  const { state, dispatch } = useSceneControl();
  // const { chatState } = useChatControl();

  useEffect(() => {
    const handleCredit = (e) => {
      if ((e.key === "c" || e.code === 67) && !state.menuState) {
        dispatch({ type: "SUNLOCK" });
        dispatchModal({
          type: "TOGGLE_OPEN",
          payload: { id: "credit", content: {} },
        });
      }
    };

    document.addEventListener("keydown", handleCredit);
    return () => {
      document.removeEventListener("keydown", handleCredit);
    };
  });
}
