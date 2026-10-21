import { useRef } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import type { RoomSlots } from "@/experience/models/RoomModel";
import type { SceneInteraction } from "@/experience/state/sceneStore";
import type { SceneLoaderInteraction } from "@/experience/state/sceneLoaderStore";
import { isAuthenticated, setAuthenticationUser } from "../lib/auth";

interface SecretRoomSlotsOptions {
  handlePLInteraction: SceneInteraction;
  handleSceneLoaderInteraction: SceneLoaderInteraction;
}

const CLICKS_TO_UNLOCK = 20;

export const useSecretRoomSlots = ({
  handlePLInteraction,
  handleSceneLoaderInteraction,
}: SecretRoomSlotsOptions): RoomSlots => {
  const doorClicks = useRef(0);

  const enterSecretRoom = () => {
    handleSceneLoaderInteraction("TOGGLE_ACTIVE");
    handlePLInteraction("TLOCK");
  };

  return {
    Door: {
      onClick: (event: ThreeEvent<MouseEvent>) => {
        event.stopPropagation();
        doorClicks.current += 1;
        if (doorClicks.current < CLICKS_TO_UNLOCK && !isAuthenticated()) return;

        doorClicks.current = 0;
        if (!isAuthenticated()) setAuthenticationUser();
        enterSecretRoom();
      },
    },
    Figurine_Door: {
      onClick: (event: ThreeEvent<MouseEvent>) => {
        event.stopPropagation();
        handleSceneLoaderInteraction("TOGGLE_ACTIVE");
        handlePLInteraction("TUNLOCK");
      },
    },
  };
};
