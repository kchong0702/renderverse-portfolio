import { Html } from "@react-three/drei";
import styles from "./Projects.module.css";
import { useControls } from "leva";
import Indicator from "../../../ui/indicator/Indicator";
import { BsProjectorFill } from "react-icons/bs";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import Navbar from "./Navbar";
import Project from "./Project";
import Searchbar from "./Searchbar";
// import CooldownLoader from "../../../ui/loader/CooldownLoader";

function Projects({
  handlePLInteraction,
  handleModalInteraction,
  // state
}) {
  const { t } = useTranslation();

  const { position, rotation } = useControls("Project html", {
    position: {
      value: {
        x: -0.04,
        y: 0.08,
        z: 0.01,
      },
      joystick: "invertY",
    },
    rotation: {
      value: {
        x: -Math.PI / 2,
        y: 0,
        z: -Math.PI / 2,
      },
    },
  });

  const projects = [
    {
      proj_id: 1,
      proj_name: t("projects.portfolio3D.name"),
      short_desc: t("projects.portfolio3D.shortDesc"),
      proj_desc: t("projects.portfolio3D.desc"),
      proj_link: "",
      github_link: null,
      img_path: "/assets/images/project/renderverse-portfolio.png",
      proj_stack: ["ReactJS", "R3F", "Blender", "Threejs"],
      vid_path: "/assets/video/renderverse-portfolio.mp4",
    },
  ];
  return (
    <>
      <Indicator
        settings={{
          position: [-0.25, 0.3, 0],
          rotation: [Math.PI / 2, 0, -Math.PI / 2],
          icon: <BsProjectorFill size={40} />,
          id: "viewindicator",
        }}
      />
      <Html
        transform
        occlude="blending"
        distanceFactor={2.5}
        position={[position.x, position.y, position.z]}
        rotation={[rotation.x, rotation.y, rotation.z]}
      >
        <div className={styles.content}>
          {/* {state.cooldown && <CooldownLoader />} */}
          <Navbar handlePLInteraction={handlePLInteraction} />
          <div className={styles.maincontent}>
            <Searchbar />
            <div className={styles.projcontent}>
              {projects.map((proj) => (
                <Project
                  project={proj}
                  key={proj.proj_id}
                  handleModalInteraction={handleModalInteraction}
                />
              ))}
            </div>
          </div>
        </div>
      </Html>
    </>
  );
}

Projects.propTypes = {
  handlePLInteraction: PropTypes.func,
  handleModalInteraction: PropTypes.func,
  state: PropTypes.object,
};

export default Projects;
