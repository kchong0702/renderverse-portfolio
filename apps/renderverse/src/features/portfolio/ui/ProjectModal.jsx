import Modal from "@/shared/ui/modal/Modal";
import { useModalStore } from "@/shared/ui/modal/modalStore";
import { useSceneStore } from "@/experience/state/sceneStore";
import ProjectContent from "./ProjectContent";

export default function ProjectModal() {
  const isShow = useModalStore((s) => s.isShow);
  const data = useModalStore((s) => s.data);
  const dispatchModal = useModalStore((s) => s.dispatch);

  if (!isShow || data?.id !== "project") return null;

  const close = () => {
    dispatchModal({ type: "TOGGLE_CLOSE" });
    const { specialIsLocked, focus, dispatch } = useSceneStore.getState();
    if (specialIsLocked === false && focus === null) {
      dispatch({ type: "SLOCK" });
    }
  };

  return (
    <Modal onClose={close}>
      <ProjectContent content={data.content} />
    </Modal>
  );
}
