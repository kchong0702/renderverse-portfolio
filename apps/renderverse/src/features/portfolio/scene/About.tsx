import { useLoader } from "@react-three/fiber";
import { FontLoader } from "three/examples/jsm/loaders/FontLoader.js";
import "./textGeometry";
import { useControls } from "leva";
import { addWordNewLine } from "@/shared/lib/utility";
import { useTranslation } from "react-i18next";

// const textMaterials = [
//   new MeshPhongMaterial({ color: 0x171f27, flatShading: true }),
//   new MeshPhongMaterial({ color: 0xffffff }), // Example for another material
// ];

const TEXT_COLOR = 0x171f27;

const About = () => {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language.startsWith("zh");

  const fontEn = useLoader(FontLoader, "./fonts/minecraftia.json");
  const fontZh = useLoader(FontLoader, "./fonts/chineseSubset.json");
  const font = isZh ? fontZh : fontEn;

  const subtext = t("about.subtext");
  const abtText = t("about.title") + "\n\n" + addWordNewLine(subtext, 40);

  const { position, rotation, dimension } = useControls("About Font", {
    position: {
      value: {
        x: -8.5,
        y: 7,
        z: 0,
      },
      joystick: "invertY",
    },
    rotation: {
      value: {
        x: 0,
        y: Math.PI / 2,
        z: 0,
      },
    },
    dimension: {
      value: {
        size: 0.15,
        height: 0.05,
      },
    },
  });
  return (
    <mesh
      // position={[position.x, position.y, position.z]}
      position={[position.x, 6.5, position.z]}
      rotation={[rotation.x, rotation.y, rotation.z]}
    >
      <textGeometry
        args={[
          abtText,
          { font: font, size: dimension.size, depth: dimension.height },
        ]}
      />
      <meshBasicMaterial color={TEXT_COLOR} />
    </mesh>
  );
};

export default About;
