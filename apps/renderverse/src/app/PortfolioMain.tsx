import { Canvas } from "@react-three/fiber";
import { Leva } from "leva";
// import { Perf } from "r3f-perf";
import Crosshair from "@/experience/ui/Crosshair";
import FocusBackButton from "@/experience/ui/FocusBackButton";
import ProjectModal from "@/features/portfolio/ui/ProjectModal";
import Audio from "@/features/audio/ui/Audio";
import Menu from "@/features/menu/ui/Menu";
import ChatScreen from "@/features/ezbot/ui/ChatScreen";
import FigureRoom from "@/features/secret-room/ui/FigureRoom";
import { Suspense, lazy } from "react";
import Loader from "@/shared/ui/loader/Loader";
import { delay } from "@/shared/lib/utility";
import SceneLoader from "@/experience/ui/SceneLoader";
import { useBackToChat } from "@/features/ezbot/hooks/useBackToChat";
import { CONFIG } from "./config";

const Room = lazy(() => delay(import("@/experience/Room")));

function PortfolioMain() {
  const backToChat = useBackToChat();

  return (
    <>
      <Menu />
      {CONFIG.isChatbotEnabled && <ChatScreen />}
      <Audio />
      <FigureRoom />
      <Crosshair />
      <FocusBackButton onBack={backToChat} />
      <ProjectModal />
      <Leva collapsed hidden />
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
    </>
  );
}

export default PortfolioMain;
