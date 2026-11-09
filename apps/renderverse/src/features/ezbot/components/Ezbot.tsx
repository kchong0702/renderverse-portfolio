import { Canvas } from "@react-three/fiber";
import { PerspectiveCamera } from "@react-three/drei";
import { OrbitControls } from "@react-three/drei";
import PointerFollowingEzbot from "@/features/ezbot/scene/PointerFollowingEzbot";
import { Center } from "@react-three/drei";
import ChatRoomLighting from "@/features/ezbot/scene/ChatRoomLighting";
interface EzbotProps {
  isActive: boolean;
  isLightOff: boolean;
}

export default function Ezbot(props: EzbotProps) {
  return (
    <>
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 0, 8]} />
        <ChatRoomLighting
          isActive={props.isActive}
          isLightOff={props.isLightOff}
        />
        <Center>
          <PointerFollowingEzbot isActive={props.isActive} />
        </Center>
        <OrbitControls enablePan={false} enableZoom={false} />
      </Canvas>
    </>
  );
}
