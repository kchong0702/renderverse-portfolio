import { Canvas } from "@react-three/fiber";
import { PerspectiveCamera } from "@react-three/drei";
import { OrbitControls } from "@react-three/drei";
import EzbotModel from "../../features/gltfmodel/EzbotModel";
import { Center } from "@react-three/drei";
import ChatRoomLighting from "../../features/staging/ChatRoomLighting";
import PropTypes from "prop-types";

export default function Ezbot(props) {
  return (
    <>
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 0, 8]} />
        <ChatRoomLighting
          isActive={props.isActive}
          isLightOff={props.isLightOff}
        />
        <Center>
          <EzbotModel isActive={props.isActive} />
        </Center>
        <OrbitControls enablePan={false} enableZoom={false} />
      </Canvas>
    </>
  );
}

Ezbot.propTypes = {
  isActive: PropTypes.bool,
  isLightOff: PropTypes.bool,
};
