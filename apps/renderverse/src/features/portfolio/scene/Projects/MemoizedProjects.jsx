import { useMemo } from "react";
import Projects from "./Projects";
import PropTypes from "prop-types";

export default function MemoizedProjects({
  state,
  handlePLInteraction,
  handleModalInteraction,
}) {
  return useMemo(() => {
    if (!state.isTLocked) {
      return (
        <Projects
          handlePLInteraction={handlePLInteraction}
          handleModalInteraction={handleModalInteraction}
          state={state}
        />
      );
    }
    return null;
  }, [state, handlePLInteraction, handleModalInteraction]);
}

MemoizedProjects.propTypes = {
  handlePLInteraction: PropTypes.func,
  handleModalInteraction: PropTypes.func,
  state: PropTypes.object,
};
