import { createContext, useContext, useReducer } from "react";
import PropTypes from "prop-types";

// 1. Create context
const ChatControlContext = createContext();

// 2. Create reducer
const reducer = (state, action) => {
  switch (action.type) {
    case "OPEN":
      return {
        ...state,
        isOpen: true,
      };
    case "CLOSE":
      return {
        ...state,
        isOpen: false,
      };
    default:
      return state;
  }
};

// 3. Create provider
const ChatControlProvider = ({ children }) => {
  const [chatState, chatDispatch] = useReducer(reducer, {
    isOpen: false,
  });

  return (
    <ChatControlContext.Provider value={{ chatState, chatDispatch }}>
      {children}
    </ChatControlContext.Provider>
  );
};

// 4. Custom Hook
const useChatControl = () => {
  const context = useContext(ChatControlContext);
  if (context === undefined)
    throw new Error(
      "ChatControlContext was used outside of the ChatControlProvider",
    );
  return context;
};

export { ChatControlProvider, useChatControl };

// Props validation
ChatControlProvider.propTypes = {
  children: PropTypes.any,
};
