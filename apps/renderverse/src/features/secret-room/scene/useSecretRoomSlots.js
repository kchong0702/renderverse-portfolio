import { useRef } from "react";
import { isAuthenticated, setAuthenticationUser } from "../lib/auth";

const CLICKS_TO_UNLOCK = 20;

// RoomModel slots for the secret room doors: the room door unlocks after
// CLICKS_TO_UNLOCK clicks (once per tab session), the figurine door leads back
export const useSecretRoomSlots = ({
  handlePLInteraction,
  handleSceneLoaderInteraction,
}) => {
  // A ref, not state: the count is never rendered, and side effects must not
  // run inside a state updater (StrictMode calls those twice)
  const doorClicks = useRef(0);

  const enterSecretRoom = () => {
    handleSceneLoaderInteraction("TOGGLE_ACTIVE");
    handlePLInteraction("TLOCK");
  };

  return {
    Door: {
      onClick: (event) => {
        event.stopPropagation();
        doorClicks.current += 1;
        if (doorClicks.current < CLICKS_TO_UNLOCK && !isAuthenticated()) return;

        doorClicks.current = 0;
        if (!isAuthenticated()) setAuthenticationUser();
        enterSecretRoom();
      },
    },
    Figurine_Door: {
      onClick: (event) => {
        event.stopPropagation();
        handleSceneLoaderInteraction("TOGGLE_ACTIVE");
        handlePLInteraction("TUNLOCK");
      },
    },
  };
};
