import { Canvas } from "@react-three/fiber";
import { Leva } from "leva";
// import { Perf } from "r3f-perf";
import Crosshair from "@/shared/ui/crosshair/Crosshair";
import SceneControlProvider from "@/experience/state/SceneControlProvider";
import Modal from "@/shared/ui/modal/Modal";
import ModalProvider from "@/shared/ui/modal/ModalProvider";
import Audio from "@/features/audio/ui/Audio";
import Menu from "@/features/menu/ui/Menu";
import ChatScreen from "@/features/ezbot/ui/ChatScreen";
import FigureRoom from "@/features/secret-room/ui/FigureRoom";
import { Suspense, lazy } from "react";
import Loader from "@/shared/ui/loader/Loader";
import { delay } from "@/shared/lib/utility";
import SceneLoaderProvider from "@/experience/state/SceneLoaderProvider";
import SceneLoader from "@/experience/ui/SceneLoader";
import ChatControlProvider from "@/features/ezbot/state/ChatControlProvider";
import { CONFIG } from "./config";

function PortfolioMain() {
  const Room = lazy(() => delay(import("@/experience/Room")));

  return (
    <SceneControlProvider>
      <ModalProvider>
        <ChatControlProvider>
          <Menu />
          {CONFIG.isChatbotEnabled && <ChatScreen />}
          <Audio />
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
        </ChatControlProvider>
      </ModalProvider>
    </SceneControlProvider>
  );
}

export default PortfolioMain;
