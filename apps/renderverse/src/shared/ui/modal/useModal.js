import { createContext, useContext } from "react";

export const ModalContext = createContext();

export const useModal = () => {
  const context = useContext(ModalContext);
  if (context === undefined)
    throw new Error("ModalContext was used outside of the ModalProvider");
  return context;
};
