import { handleHoverIndicator } from "@/shared/lib/event-handler";
import Skills from "./Skills/Skills";
import Projects from "./Projects/Projects";
import Contacts from "./Contacts/Contacts";
import { SECTION_FOCUS } from "@/features/portfolio/constants";
import { sectionFocus } from "@/features/portfolio/sectionFocus";
import type { ThreeEvent } from "@react-three/fiber";
import type { RoomSlots } from "@/experience/models/RoomModel";
import type {
  SceneInteraction,
  SceneState,
} from "@/experience/state/sceneStore";
import type { ModalInteraction } from "@/shared/ui/modal/modalStore";

interface PortfolioSlotsOptions {
  state: SceneState;
  handlePLInteraction: SceneInteraction;
  handleModalInteraction: ModalInteraction;
}

export const usePortfolioSlots = ({
  state,
  handlePLInteraction,
  handleModalInteraction,
}: PortfolioSlotsOptions): RoomSlots => {
  const showBoards = !state.isTLocked;

  return {
    Whiteboard_Surface001: {
      children: showBoards && <Skills />,
    },
    Projector_Screen001: {
      onPointerEnter: () => handleHoverIndicator("enter", "viewindicator"),
      onPointerLeave: () => handleHoverIndicator("leave", "viewindicator"),
      onClick: (event: ThreeEvent<MouseEvent>) => {
        event.stopPropagation();
        handlePLInteraction(
          "SUNLOCK",
          sectionFocus("projects", window.innerWidth / window.innerHeight),
        );
      },
      children: showBoards && (
        <Projects
          handlePLInteraction={handlePLInteraction}
          handleModalInteraction={handleModalInteraction}
        />
      ),
    },
    Phone_Screen001: {
      onPointerEnter: () => handleHoverIndicator("enter", "contactindicator"),
      onPointerLeave: () => handleHoverIndicator("leave", "contactindicator"),
      onClick: (event: ThreeEvent<MouseEvent>) => {
        event.stopPropagation();
        handlePLInteraction("SUNLOCK", SECTION_FOCUS.contact);
      },
      children: showBoards && (
        <Contacts handlePLInteraction={handlePLInteraction} state={state} />
      ),
    },
  };
};
