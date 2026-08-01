import Arena from "../firstperson/Arena";
import Model from "../gltfmodel/Model";
import { AdaptiveDpr, AdaptiveEvents, Bvh } from "@react-three/drei";
import { Physics } from "@react-three/rapier";
import Person from "../firstperson/Person";
import Title from "../portfolio/Title";
import About from "../portfolio/About";
import { Skybox } from "../skybox/Skybox";
import PropTypes from "prop-types";
import { useSceneControl } from "../../hooks/useSceneControl";
import { useModal } from "../../hooks/useModal";
import Camera from "../camera/Camera";
import { displayInitialHiddenHtml } from "../../utils/event-handler";
import { useSceneLoader } from "../../hooks/useSceneLoader";

function Room({ fpv }) {
  const { state, dispatch } = useSceneControl();
  const { dispatchModal } = useModal();
  const { dispatchSceneLoader } = useSceneLoader();

  const handlePLInteraction = (type, payload) => {
    if (!state.cooldown) dispatch({ type: type, payload: payload });
  };

  const handleModalInteraction = (type, payload) => {
    dispatchModal({ type: type, payload: payload });
  };

  const handleSceneLoaderInteraction = (type) => {
    if (!state.cooldown) dispatchSceneLoader({ type: type });
  };

  /**
   * hack to avoid flickering of html element
   * before room complete suspense
   * element initial opacity should be 0
   */
  displayInitialHiddenHtml();

  return (
    <Bvh firstHitOnly>
      {/* Not sure what they do, but document say it is for raycaster performances */}
      <AdaptiveDpr pixelated />
      <AdaptiveEvents />
      <Camera state={state} fpv={fpv} />
      <Skybox />
      <Physics gravity={[0, -20, 0]}>
        <Arena />
        {fpv && <Person pointerState={state} />}
      </Physics>
      <Model
        handlePLInteraction={handlePLInteraction}
        handleModalInteraction={handleModalInteraction}
        handleSceneLoaderInteraction={handleSceneLoaderInteraction}
        state={state}
      />
      <Title />
      <About />
    </Bvh>
  );
}

Room.propTypes = {
  fpv: PropTypes.bool,
};

export default Room;
