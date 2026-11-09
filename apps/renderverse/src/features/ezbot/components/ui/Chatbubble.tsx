import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { IoIosArrowForward } from "react-icons/io";
import styles from "./Chatbubble.module.css";
import type { PortfolioSection } from "@/features/portfolio";

export interface ChatbubbleProps {
  id?: string;
  content: ReactNode;
  role: "system" | "user";
  isAborted?: boolean;
  intent?: PortfolioSection | null;
  canNavigate?: boolean;
  onNavigate?: (section: PortfolioSection) => void;
}

export default function Chatbubble(props: ChatbubbleProps) {
  const { t } = useTranslation();

  if (props.role === "system") {
    const { intent, onNavigate } = props;
    return (
      <div className={[styles.chat__item, styles.item_left].join(" ")}>
        <div className={styles.chat__message}>
          <img
            src="/assets/images/ezbot.png"
            alt="ezbot image"
            width={40}
            height={40}
          ></img>
          <div className={[styles.chat__bubble, styles.chat__system].join(" ")}>
            <span className={props.isAborted ? styles.aborted_message : ""}>
              {props.content}
            </span>
          </div>
        </div>
        {intent && onNavigate && (
          <button
            type="button"
            className={styles.navigate}
            disabled={!props.canNavigate}
            onClick={(event) => {
              event.stopPropagation();
              onNavigate(intent);
            }}
          >
            {t(`chat.navigate.${intent}`)}
            <IoIosArrowForward size={14} />
          </button>
        )}
        <div className={styles.toolbar}>{/* Text to speech */}</div>
      </div>
    );
  } else {
    return (
      <div className={[styles.chat__item, styles.item_left].join(" ")}>
        <div className={[styles.chat__bubble, styles.chat__user].join(" ")}>
          <span>{props.content}</span>
        </div>
      </div>
    );
  }
}
