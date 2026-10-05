import { Canvas } from "@react-three/fiber";
import { Leva } from "leva";
// import { Perf } from "r3f-perf";
import Crosshair from "./crosshair/Crosshair";
import { SceneControlProvider } from "../hooks/useSceneControl";
import Modal from "./modal/Modal";
import { ModalProvider } from "../hooks/useModal";
import Audio from "./Audio";
import Menu from "./Menu";
import ChatScreen from "./chat/ChatScreen";
import FigureRoom from "../features/figureroom/FigureRoom";
import { Suspense, lazy } from "react";
import Loader from "./loader/Loader";
import { delay } from "../utils/utility";
import { SceneLoaderProvider } from "../hooks/useSceneLoader";
import SceneLoader from "./loader/SceneLoader";
import { ChatControlProvider } from "../hooks/useChatControl";
import { CONFIG } from "../config-global";

function PortfolioMain() {
  const Room = lazy(() => delay(import("../features/room/Room")));

  return (
    <SceneControlProvider>
      <ModalProvider>
        <Menu />
        <ChatControlProvider>
          {CONFIG.isChatbotEnabled && <ChatScreen />}
          <Audio />
        </ChatControlProvider>
        <FigureRoom />
        <Crosshair />
        <Modal />
        <Leva collapsed hidden />
        <SceneLoaderProvider>
          <SceneLoader />
          <Suspense fallback={<Loader />}>
            <div id="canvas-container">
              <Canvas
                flat
                camera={{
                  fov: 45,
                  near: 0.1,
                  far: 100,
                  position: [1, 2, 6],
                }}
              >
                {/* <Perf position="top-left" style={{ zIndex: 9999999 }} /> */}
                {/* <axesHelper args={[5]} position={[1, 16, -19.8]} /> */}
                <Room fpv={true} />
              </Canvas>
            </div>
          </Suspense>
        </SceneLoaderProvider>
      </ModalProvider>
    </SceneControlProvider>
  );
}

export default PortfolioMain;
