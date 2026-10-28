import type { CameraFocus } from "@/experience/state/sceneStore";
import type { PortfolioSection, SectionFit } from "./types";

export const SECTION_FOCUS: Record<PortfolioSection, CameraFocus> = {
  skills: {
    look: { x: 3.791, y: 4.17, z: -7.37 },
    pos: { x: 3.791, y: 4.17, z: -3.6 },
    showBack: true,
  },
  projects: {
    look: { x: 8.216, y: 4.537, z: -0.203 },
    pos: { x: 0, y: 5, z: -0.203 },
  },
  about: {
    look: { x: -8.475, y: 5.4, z: -3.4 },
    pos: { x: -4.3, y: 5.4, z: -3.4 },
    showBack: true,
  },
  contact: {
    look: { x: -4, y: 3.368, z: 7.295 },
    pos: { x: 0, y: 5, z: 1 },
  },
};

const FIT_MARGIN = 1.1;

/**
 * Sections framed for the viewport: the camera backs off until the whole
 * target fits, since a fixed distance crops it on narrow screens. Line of
 * sight was raycast against room.glb out to each `maxDistance`.
 */
export const SECTION_FIT: Partial<Record<PortfolioSection, SectionFit>> = {
  // Whiteboard mesh, 4.855 x 3.18
  skills: {
    facing: { x: 0, y: 0, z: 1 },
    width: 4.855 * FIT_MARGIN,
    height: 3.18 * FIT_MARGIN,
    rise: 0,
    maxDistance: 11.2,
  },
  // English About text, the larger locale, ~6.93 x 2.85. The rise keeps the
  // desk globe off its last line as the camera backs away.
  about: {
    facing: { x: 1, y: 0, z: 0 },
    width: 6.93 * FIT_MARGIN,
    height: 2.85 * FIT_MARGIN,
    rise: 0.16,
    maxDistance: 15.25,
  },
  // Projects overlay, 1285 x 635 px at distanceFactor 2.5 = 8.03 x 3.97. The
  // original view stood 8.2 back, slightly raised; keep it as the closest so
  // wide screens look the same. Past 16 the camera reaches the back wall.
  projects: {
    facing: { x: -1, y: 0, z: 0 },
    width: 8.03 * FIT_MARGIN,
    height: 3.97 * FIT_MARGIN,
    rise: 0.056,
    minDistance: 8.216,
    maxDistance: 16,
  },
};
