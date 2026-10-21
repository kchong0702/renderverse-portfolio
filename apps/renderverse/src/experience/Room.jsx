import Arena from "@/experience/player/Arena";
import Model from "@/experience/models/Model";
import { AdaptiveDpr, AdaptiveEvents, Bvh } from "@react-three/drei";
import { Physics } from "@react-three/rapier";
import Person from "@/experience/player/Person";
import EzbotCompanion from "@/features/ezbot/scene/EzbotCompanion";
import Title from "@/features/portfolio/scene/Title";
import About from "@/features/portfolio/scene/About";
import { Skybox } from "@/experience/environment/Skybox";
import PropTypes from "prop-types";
import { useSceneControl } from "@/experience/state/useSceneControl";
import { useModal } from "@/shared/ui/modal/useModal";
import Camera from "@/experience/camera/Camera";
import { displayInitialHiddenHtml } from "@/shared/lib/event-handler";
import { useSceneLoader } from "@/experience/state/useSceneLoader";

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
      <AdaptiveDpr pixelated />
      <AdaptiveEvents />
      <Camera state={state} fpv={fpv} />
      <Skybox />
      <Physics gravity={[0, -20, 0]}>
        <Arena />
        {fpv && <Person pointerState={state} />}
      </Physics>
      {fpv && <EzbotCompanion />}
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
