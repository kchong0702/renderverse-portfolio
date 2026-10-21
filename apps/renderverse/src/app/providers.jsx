import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import PropTypes from "prop-types";
import { queryClient } from "./queryClient";

export default function AppProviders({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

AppProviders.propTypes = {
  children: PropTypes.node,
};
