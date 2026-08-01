export const isAuthenticated = () => {
  return sessionStorage.getItem("authenticatedUser") === "guest";
};

export const setAuthenticationUser = () => {
  sessionStorage.setItem("authenticatedUser", "guest");
};
