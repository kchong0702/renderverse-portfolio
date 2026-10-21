import { useRef } from "react";
import { isAuthenticated, setAuthenticationUser } from "../lib/auth";

const CLICKS_TO_UNLOCK = 20;

export const useSecretRoomSlots = ({
  handlePLInteraction,
  handleSceneLoaderInteraction,
}) => {
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
