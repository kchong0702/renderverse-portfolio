import styles from "./Chatbubble.module.css";

export interface ChatbubbleProps {
  id?: string;
  content: string;
  role: "system" | "user";
  isAborted?: boolean;
}

export default function Chatbubble(props: ChatbubbleProps) {
  if (props.role === "system") {
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
