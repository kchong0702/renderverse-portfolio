import { useTranslation } from "react-i18next";
import bubbleStyles from "./Chatbubble.module.css";
import styles from "./ChatTypingIndicator.module.css";

export default function ChatTypingIndicator() {
  const { t } = useTranslation();

  return (
    <div
      className={[bubbleStyles.chat__item, bubbleStyles.item_left].join(" ")}
      role="status"
      aria-label={t("chat.typing")}
    >
      <div className={bubbleStyles.chat__message}>
        <img
          src="/assets/images/ezbot.png"
          alt="ezbot image"
          width={40}
          height={40}
        ></img>
        <div
          className={[
            bubbleStyles.chat__bubble,
            bubbleStyles.chat__system,
            styles.dots,
          ].join(" ")}
        >
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}
