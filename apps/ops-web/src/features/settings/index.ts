export { default as SettingsPage } from "./pages/SettingsPage";
export { default as GoogleNotice } from "./components/GoogleNotice";
export {
  useGoogleAccount,
  useSettings,
  useUpdateSettings,
} from "./hooks/useSettings";
export type { Automation, ModelFamily, Settings } from "./api/settings";
