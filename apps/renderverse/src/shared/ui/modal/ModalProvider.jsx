import { useReducer } from "react";
import PropTypes from "prop-types";
import { ModalContext } from "./useModal";

const reducer = (state, action) => {
  switch (action.type) {
    case "TOGGLE_OPEN":
      return {
        isShow: true,
        data: action.payload ? action.payload : null,
      };
    case "TOGGLE_CLOSE":
      return {
        isShow: false,
      };
    default:
      return state;
  }
};

export default function ModalProvider({ children }) {
  const [modalState, dispatchModal] = useReducer(reducer, {
    isShow: false,
    data: null,
  });

  return (
    <ModalContext.Provider value={{ modalState, dispatchModal }}>
      {children}
    </ModalContext.Provider>
  );
}

ModalProvider.propTypes = {
  children: PropTypes.any,
};
