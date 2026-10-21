import { Suspense } from "react";
import PropTypes from "prop-types";
import ShinGodzillaModel from "@/experience/models/ShinGodzillaModel";

export default function SecretRoomScene({ state }) {
  if (!state.isTLocked) return null;

  return (
    <Suspense>
      <ShinGodzillaModel state={state} />
    </Suspense>
  );
}

SecretRoomScene.propTypes = {
  state: PropTypes.object.isRequired,
};
