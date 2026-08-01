import { useModal } from "../../hooks/useModal";
import ProjectContent from "./ProjectContent";
import CreditContent from "./CreditContent";
import { IoMdCloseCircle } from "react-icons/io";
import { useSceneControl } from "../../hooks/useSceneControl";

export default function Modal() {
  const { modalState, dispatchModal } = useModal();
  const { state, dispatch } = useSceneControl();

  return (
    <>
      {modalState.isShow && (
        <div
          className="modal-overlay"
          style={{
            position: "absolute",
            width: "100%",
            height: "100%",
            zIndex: 1,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            // WebkitBackdropFilter: "blur(5px)",
            // backdropFilter: "blur(5px)",
          }}
        >
          <div
            className="content"
            style={{
              width: "60%",
              minWidth: "600px",
              maxWidth: "1040px",
              borderRadius: "20px",
              background: "rgba( 255, 255, 255, 0.25 )",
              boxShadow: "0 8px 32px 0 rgba( 31, 38, 135, 0.37 )",
              WebkitBackdropFilter: "blur(4px)",
              backdropFilter: "blur(4px)",
              border: "1px solid rgba( 255, 255, 255, 0.18 )",
              padding: "10px 20px",
              paddingBottom: "40px",
              overflowY: "scroll",
              scrollbarWidth: "none", // For Firefox
              WebkitOverflowScrolling: "touch", // For smooth scrolling on iOS devices
              msOverflowStyle: "none", // For Internet Explorer and Edge
              position: "relative",
            }}
          >
            <div style={{ marginBottom: "1rem" }}>
              <IoMdCloseCircle
                style={{ position: "absolute", right: "10px", top: "8px" }}
                size={35}
                onClick={(event) => {
                  event.stopPropagation();
                  dispatchModal({ type: "TOGGLE_CLOSE" });
                  if (state.specialIsLocked === false && state.focus === null) {
                    dispatch({ type: "SLOCK" });
                  }
                }}
              />
              {modalState.data.id === "project" ? (
                <ProjectContent content={modalState.data.content} />
              ) : modalState.data.id === "credit" ? (
                <CreditContent content={modalState.data.content} />
              ) : (
                <></>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
