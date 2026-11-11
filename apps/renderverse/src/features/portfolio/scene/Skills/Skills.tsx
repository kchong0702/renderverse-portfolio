import { Html } from "@react-three/drei";
import { useControls } from "leva";
import styles from "./Skills.module.css";
import SkillCategory from "./SkillCategory";
import { MathJaxContext, MathJax } from "better-react-mathjax";
import { useTranslation } from "react-i18next";
import { useRef } from "react";
import { useFitFontSize } from "@/shared/hooks/useFitFontSize";
import { useRelease } from "@/features/portfolio/hooks/useRelease";

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

  const { data: release, isLoading } = useRelease();
  const skills: Record<string, string[]> = isLoading
    ? {}
    : release
      ? release.skills.reduce<Record<string, string[]>>(
          (groups, { group, name }) => ({
            ...groups,
            [group]: [...(groups[group] ?? []), name],
          }),
          {},
        )
      : {
          [t("skills.categories.ai")]: [
            t("skills.items.computerUseAgent"),
            t("skills.items.voiceAgent"),
            t("skills.items.bankingAgent"),
          ],
          [t("skills.categories.frameworks")]: [
            t("skills.items.langgraph"),
            t("skills.items.pytorch"),
            t("skills.items.springBoot"),
            t("skills.items.qt"),
            t("skills.items.angular"),
            t("skills.items.flutter"),
          ],
          [t("skills.categories.telephony")]: [
            t("skills.items.pbx"),
            t("skills.items.smpp"),
            t("skills.items.livekit"),
            t("skills.items.stuner"),
          ],
          [t("skills.categories.language")]: [
            t("skills.items.cpp"),
            t("skills.items.python"),
            t("skills.items.java"),
            t("skills.items.rust"),
          ],
          [t("skills.categories.ops")]: [
            t("skills.items.terraform"),
            t("skills.items.aws"),
            t("skills.items.gcp"),
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
