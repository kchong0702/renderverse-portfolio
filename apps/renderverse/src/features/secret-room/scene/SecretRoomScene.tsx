import { Suspense } from "react";
import type { SceneState } from "@/experience/state/sceneStore";
import ShinGodzillaModel from "@/experience/models/ShinGodzillaModel";

export default function SecretRoomScene({
  state,
}: {
  state: Pick<SceneState, "isTLocked" | "tInnerLight">;
}) {
  if (!state.isTLocked) return null;

  return (
    <Suspense>
      <ShinGodzillaModel state={state} />
    </Suspense>
  );
}
