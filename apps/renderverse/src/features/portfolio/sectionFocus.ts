import type { CameraFocus } from "@/experience/state/sceneStore";
import { ROOM_CAMERA_FOV } from "@/experience/camera/constants";
import { SECTION_FIT, SECTION_FOCUS } from "./constants";
import type { PortfolioSection } from "./types";

/** Camera focus for a section, framed to fit a viewport of this aspect ratio */
export const sectionFocus = (
  section: PortfolioSection,
  aspect: number,
): CameraFocus => {
  const focus = SECTION_FOCUS[section];
  const fit = SECTION_FIT[section];
  if (!fit) return focus;

  const tanHalfFov = Math.tan((ROOM_CAMERA_FOV * Math.PI) / 360);
  const distance = Math.min(
    Math.max(
      Math.max(fit.height / 2, fit.width / 2 / aspect) / tanHalfFov,
      fit.minDistance ?? 0,
    ),
    fit.maxDistance,
  );
  const { look } = focus;
  const { facing } = fit;
  return {
    ...focus,
    pos: {
      x: look.x + facing.x * distance,
      y: look.y + facing.y * distance + fit.rise * distance,
      z: look.z + facing.z * distance,
    },
  };
};
