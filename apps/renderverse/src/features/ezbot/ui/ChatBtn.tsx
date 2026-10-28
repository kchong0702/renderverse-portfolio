import { useTranslation } from "react-i18next";
import { BsFillChatTextFill } from "react-icons/bs";

export default function ChatBtn() {
  const { t } = useTranslation();
  return (
    <div
      id="chat-btn"
      style={{
        position: "fixed",
        zIndex: 1,
        bottom: "12px",
        right: "12px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        opacity: 0,
      }}
    >
      <BsFillChatTextFill
        size={30}
        style={{
          color: "rgba(63, 193, 191, 0.9)",
          marginBottom: "5px",
        }}
        onClick={(event) => {
          event.stopPropagation();
          const e = new KeyboardEvent("keydown", {
            key: "c",
            code: "KeyC",
            keyCode: 67,
            charCode: 99,
            bubbles: true,
            cancelable: true,
          });

          document.dispatchEvent(e);
        }}
      />
      <span
        style={{
          display: "block",
          fontSize: "0.65rem",
        }}
      >
        {t("chatBtn.poweredBy")}
      </span>
    </div>
  );
}
