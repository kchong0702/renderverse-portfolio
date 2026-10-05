import { extend, useLoader } from "@react-three/fiber";
import { FontLoader } from "three/examples/jsm/loaders/FontLoader";
import { TextGeometry } from "three/examples/jsm/geometries/TextGeometry";
import { useControls } from "leva";
import { MeshBasicMaterial } from "three";
import { addWordNewLine } from "../../utils/utility";
import { useTranslation } from "react-i18next";

extend({ TextGeometry });

// const textMaterials = [
//   new MeshPhongMaterial({ color: 0x171f27, flatShading: true }),
//   new MeshPhongMaterial({ color: 0xffffff }), // Example for another material
// ];

const textMaterials = [
  new MeshBasicMaterial({ color: 0x171f27 }),
  new MeshBasicMaterial({ color: 0x171f27 }), // Example for another material
];

const About = () => {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language.startsWith("zh");

  const fontEn = useLoader(FontLoader, "./fonts/minecraftia.json");
  const fontZh = useLoader(FontLoader, "./fonts/chineseSubset.json");
  const font = isZh ? fontZh : fontEn;

  const subtext = t("about.subtext");
  const abtText =
    t("about.title") +
    "\n\n" +
    addWordNewLine(subtext, 40);

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
      {textMaterials.map((material, index) => (
        <meshBasicMaterial key={index} attachArray="material" {...material} />
      ))}
    </mesh>
  );
};

export default About;
