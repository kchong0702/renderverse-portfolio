import { useCallback } from "react";
import { useSceneStore } from "@/experience/state/sceneStore";
import { sectionFocus, type PortfolioSection } from "@/features/portfolio";
import { useChatStore } from "../state/chatStore";

export const useNavigateToSection = () => {
  const isTLocked = useSceneStore((s) => s.isTLocked);
  const dispatch = useSceneStore((s) => s.dispatch);
  const chatDispatch = useChatStore((s) => s.dispatch);

  const navigate = useCallback(
    (section: PortfolioSection) => {
      if (isTLocked) return;
      chatDispatch({ type: "NAVIGATE" });
      dispatch({
        type: "SUNLOCK",
        payload: {
          ...sectionFocus(section, window.innerWidth / window.innerHeight),
          showBack: true,
        },
      });
    },
    [isTLocked, dispatch, chatDispatch],
  );

  return { navigate, canNavigate: !isTLocked };
};
