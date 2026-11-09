import { useTranslation } from "react-i18next";
import { IoMdArrowBack } from "react-icons/io";
import styles from "./FocusBackButton.module.css";
import { useSceneStore } from "@/experience/state/sceneStore";

interface FocusBackButtonProps {
  onBack?: () => void;
}

export default function FocusBackButton({ onBack }: FocusBackButtonProps) {
  const { t } = useTranslation();
  const showBack = useSceneStore(
    (s) => s.specialIsLocked === false && s.focus?.showBack === true,
  );
  const dispatch = useSceneStore((s) => s.dispatch);

  if (!showBack) return null;

  return (
    <button
      type="button"
      className={styles.back}
      onClick={(event) => {
        event.stopPropagation();
        if (onBack) onBack();
        else dispatch({ type: "SLOCK" });
      }}
    >
      <IoMdArrowBack size={18} />
      <span>{t("navigation.back")}</span>
    </button>
  );
}
