import { createContext, useContext, useReducer } from "react";
import PropTypes from "prop-types";

// 1. Create context
const ModalContext = createContext();

// 2. Create reducer
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

// 3. Create provider
const ModalProvider = ({ children }) => {
  const [modalState, dispatchModal] = useReducer(reducer, {
    isShow: false,
    data: null,
  });

  return (
    <ModalContext.Provider value={{ modalState, dispatchModal }}>
      {children}
    </ModalContext.Provider>
  );
};

// 4. Custom Hook
const useModal = () => {
  const context = useContext(ModalContext);
  if (context === undefined)
    throw new Error("ModalContext was used outside of the ModalProvider");
  return context;
};

export { ModalProvider, useModal };

// Props validation
ModalProvider.propTypes = {
  children: PropTypes.any,
};
