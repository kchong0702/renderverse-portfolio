import { Html } from "@react-three/drei";
import { useControls } from "leva";
import styles from "./Skills.module.css";
import SkillCategory from "./SkillCategory";
import { MathJaxContext, MathJax } from "better-react-mathjax";
import { useTranslation } from "react-i18next";
import { useRef } from "react";
import { useFitFontSize } from "../../../hooks/useFitFontSize";

const DISTANCE_FACTOR = 2.4;

/**
 * CSS px per scene unit for this overlay, drei's <Html transform> draws
 * 1 CSS px as distanceFactor / 400 units, so 1 unit = 400 / distanceFactor px
 * (~166.67 at 2.4). Lowering DISTANCE_FACTOR renders the board at a higher
 * resolution in the same space.
 */
const PX_PER_UNIT = 400 / DISTANCE_FACTOR;

/**
 * Size the overlay to the whiteboard mesh whose geometry measures 3.18 (x) by
 * 4.855 (y) units. The overlay is rotated -90deg around z, so the mesh's y side
 * runs horizontally (width) and x side vertically (height).
 */
const BOARD_WIDTH_PX = Math.round(4.855 * PX_PER_UNIT);
const BOARD_HEIGHT_PX = Math.round(3.18 * PX_PER_UNIT);

const FONT_PX = { min: 14, max: 28 };

function Skills() {
  const { t } = useTranslation();
  const { position, rotation } = useControls("Skills html", {
    position: {
      value: {
        x: -0.4,
        y: 4.5,
        z: -7.156, // -7.156
      },
      joystick: "invertY",
    },
    rotation: {
      value: {
        x: 0,
        y: 0,
        z: -Math.PI / 2,
      },
    },
  });

  const skills = {
    [t("skills.categories.ai")]: [
      { name: t("skills.items.computerUseAgent"), rating: 5 },
      { name: t("skills.items.voiceAgent"), rating: 5 },
      { name: t("skills.items.bankingAgent"), rating: 5 },
    ],
    [t("skills.categories.frameworks")]: [
      { name: t("skills.items.langgraph"), rating: 5 },
      { name: t("skills.items.pytorch"), rating: 5 },
      { name: t("skills.items.springBoot"), rating: 5 },
      { name: t("skills.items.qt"), rating: 5 },
      { name: t("skills.items.angular"), rating: 5 },
      { name: t("skills.items.flutter"), rating: 5 },
    ],
    [t("skills.categories.telephony")]: [
      { name: t("skills.items.pbx"), rating: 5 },
      { name: t("skills.items.smpp"), rating: 5 },
      { name: t("skills.items.livekit"), rating: 5 },
      { name: t("skills.items.stuner"), rating: 5 },
    ],
    [t("skills.categories.language")]: [
      { name: t("skills.items.cpp"), rating: 5 },
      { name: t("skills.items.python"), rating: 5 },
      { name: t("skills.items.java"), rating: 5 },
      { name: t("skills.items.rust"), rating: 5 },
    ],
    [t("skills.categories.ops")]: [
      { name: t("skills.items.terraform"), rating: 5 },
      { name: t("skills.items.aws"), rating: 5 },
      { name: t("skills.items.gcp"), rating: 5 },
    ],
  };

  const contentRef = useRef(null);
  useFitFontSize(contentRef, FONT_PX, JSON.stringify(skills));

  return (
    <Html
      transform
      occlude="blending"
      distanceFactor={DISTANCE_FACTOR}
      position={[position.x, position.y, position.z]}
      rotation={[rotation.x, rotation.y, rotation.z]}
    >
      <div
        className={styles.skillContainer}
        style={{ width: BOARD_WIDTH_PX, height: BOARD_HEIGHT_PX }}
      >
        <div className={styles.formula}>
          <MathJaxContext>
            <MathJax style={{ transform: "rotate(-5deg)", fontSize: "1rem" }}>
              {
                "\\(W{x} = W{x} - \\alpha (\\frac{\\partial L}{\\partial W_{x}})\\)"
              }
            </MathJax>
          </MathJaxContext>
        </div>
        <div ref={contentRef} className={styles.content}>
          {Object.entries(skills).map(([key, value]) => (
            <SkillCategory category={key} contents={value} key={key} />
          ))}
        </div>
      </div>
    </Html>
  );
}

export default Skills;
