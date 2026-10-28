import styles from "./Project.module.css";
import type { ModalInteraction } from "@/shared/ui/modal/modalStore";
import type { ProjectItem } from "@/features/portfolio/types";

interface ProjectProps {
  project: ProjectItem;
  handleModalInteraction: ModalInteraction;
}

function Project({ project, handleModalInteraction }: ProjectProps) {
  const { proj_name, short_desc, img_path } = project;

  return (
    <div
      className={styles.card}
      onClick={(event) => {
        event.stopPropagation();
        handleModalInteraction("TOGGLE_OPEN", {
          id: "project",
          content: project,
        });
      }}
    >
      <div className={styles.imgcontainer}>
        <img src={img_path} alt={img_path} className={styles.projimg} />
      </div>
      <div className={styles.projname}>
        <span>{proj_name}</span>
        <p className={styles.projshortname}>{short_desc}</p>
      </div>
    </div>
  );
}

export default Project;
