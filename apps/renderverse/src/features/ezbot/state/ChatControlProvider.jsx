import { useReducer } from "react";
import PropTypes from "prop-types";
import { ChatControlContext } from "@/features/ezbot/hooks/useChatControl";

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
    case "REPLYING":
      return {
        ...state,
        isReplying: action.payload,
      };
    default:
      return state;
  }
};

export default function ChatControlProvider({ children }) {
  const [chatState, chatDispatch] = useReducer(reducer, {
    isOpen: false,
    isReplying: false,
  });

  return (
    <ChatControlContext.Provider value={{ chatState, chatDispatch }}>
      {children}
    </ChatControlContext.Provider>
  );
}

ChatControlProvider.propTypes = {
  children: PropTypes.any,
};
