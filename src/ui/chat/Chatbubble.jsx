import styles from "./Chatbubble.module.css";
import PropTypes from "prop-types";

export default function Chatbubble(props) {
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
            <span className={props.isAborted ? "aborted_message" : ""}>
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

Chatbubble.propTypes = {
  id: PropTypes.string,
  content: PropTypes.string,
  semantic: PropTypes.oneOf(["None", "LIKED", "DISLIKED"]),
  feedback: PropTypes.string,
  role: PropTypes.oneOf(["system", "user"]),
  question_id: PropTypes.string,
  isAborted: PropTypes.bool,
};
