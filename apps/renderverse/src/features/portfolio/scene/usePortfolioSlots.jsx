import { handleHoverIndicator } from "@/shared/lib/event-handler";
import Skills from "./Skills/Skills";
import Projects from "./Projects/Projects";
import Contacts from "./Contacts/Contacts";

// RoomModel slots for the portfolio boards: Skills on the whiteboard,
// Projects on the projector and Contacts on the phone. Boards are hidden
// while the secret room is open; their click targets stay active.
export const usePortfolioSlots = ({
  state,
  handlePLInteraction,
  handleModalInteraction,
}) => {
  const showBoards = !state.isTLocked;

  return {
    Whiteboard_Surface001: {
      children: showBoards && <Skills />,
    },
    Projector_Screen001: {
      onPointerEnter: () => handleHoverIndicator("enter", "viewindicator"),
      onPointerLeave: () => handleHoverIndicator("leave", "viewindicator"),
      onClick: (event) => {
        event.stopPropagation();
        handlePLInteraction("SUNLOCK", {
          look: { x: 8.296, y: 4.577, z: 0 },
          pos: { x: 0, y: 5, z: 0 },
        });
      },
      children: showBoards && (
        <Projects
          handlePLInteraction={handlePLInteraction}
          handleModalInteraction={handleModalInteraction}
          state={state}
        />
      ),
    },
    Phone_Screen001: {
      onPointerEnter: () => handleHoverIndicator("enter", "contactindicator"),
      onPointerLeave: () => handleHoverIndicator("leave", "contactindicator"),
      onClick: (event) => {
        event.stopPropagation();
        handlePLInteraction("SUNLOCK", {
          look: { x: -4, y: 3.368, z: 7.295 },
          pos: { x: 0, y: 5, z: 1 },
        });
      },
      children: showBoards && (
        <Contacts handlePLInteraction={handlePLInteraction} state={state} />
      ),
    },
  };
};
