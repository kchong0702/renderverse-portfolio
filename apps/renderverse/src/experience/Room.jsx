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
import { useSceneStore } from "@/experience/state/sceneStore";
import { useModalStore } from "@/shared/ui/modal/modalStore";
import Camera from "@/experience/camera/Camera";
import { displayInitialHiddenHtml } from "@/shared/lib/event-handler";
import { useSceneLoaderStore } from "@/experience/state/sceneLoaderStore";

function Room({ fpv }) {
  // Whole scene state: it is drilled into Camera, Person and Model
  const state = useSceneStore();
  const { dispatch } = state;
  const dispatchModal = useModalStore((s) => s.dispatch);
  const dispatchSceneLoader = useSceneLoaderStore((s) => s.dispatch);

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
