import Arena from "@/experience/player/Arena";
import RoomModel from "@/experience/models/RoomModel";
import Clock from "@/features/clock/scene/Clock";
import { usePortfolioSlots } from "@/features/portfolio/scene/usePortfolioSlots";
import { useSecretRoomSlots } from "@/features/secret-room/scene/useSecretRoomSlots";
import SecretRoomScene from "@/features/secret-room/scene/SecretRoomScene";
import { AdaptiveDpr, AdaptiveEvents, Bvh } from "@react-three/drei";
import { Physics } from "@react-three/rapier";
import Person from "@/experience/player/Person";
import EzbotCompanion from "@/features/ezbot/scene/EzbotCompanion";
import Title from "@/features/portfolio/scene/Title";
import About from "@/features/portfolio/scene/About";
import { Skybox } from "@/experience/environment/Skybox";
import {
  useSceneStore,
  type SceneInteraction,
} from "@/experience/state/sceneStore";
import {
  useModalStore,
  type ModalAction,
  type ModalInteraction,
} from "@/shared/ui/modal/modalStore";
import Camera from "@/experience/camera/Camera";
import { displayInitialHiddenHtml } from "@/shared/lib/event-handler";
import {
  useSceneLoaderStore,
  type SceneLoaderInteraction,
} from "@/experience/state/sceneLoaderStore";
import type { RoomSlots } from "@/experience/models/RoomModel";

interface RoomProps {
  fpv: boolean;
}

function Room({ fpv }: RoomProps) {
  const state = useSceneStore();
  const { dispatch } = state;
  const dispatchModal = useModalStore((s) => s.dispatch);
  const dispatchSceneLoader = useSceneLoaderStore((s) => s.dispatch);

  const handlePLInteraction: SceneInteraction = (type, payload) => {
    if (!state.cooldown)
      dispatch({ type, payload } as Parameters<typeof dispatch>[0]);
  };

  const handleModalInteraction: ModalInteraction = (type, payload) => {
    dispatchModal({ type, payload } as ModalAction);
  };

  const handleSceneLoaderInteraction: SceneLoaderInteraction = (type) => {
    if (!state.cooldown) dispatchSceneLoader({ type: type });
  };

  const portfolioSlots = usePortfolioSlots({
    state,
    handlePLInteraction,
    handleModalInteraction,
  });
  const secretRoomSlots = useSecretRoomSlots({
    handlePLInteraction,
    handleSceneLoaderInteraction,
  });
  const slots: RoomSlots = {
    ...portfolioSlots,
    ...secretRoomSlots,
    Clock_Screen001: { children: !state.isTLocked && <Clock /> },
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
      <RoomModel slots={slots} />
      <SecretRoomScene state={state} />
      <Title />
      <About />
    </Bvh>
  );
}

export default Room;
