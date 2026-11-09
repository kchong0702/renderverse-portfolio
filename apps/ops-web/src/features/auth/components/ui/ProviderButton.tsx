import { useTranslation } from "react-i18next";
import { oauthLoginUrl, type OAuthProvider } from "../../api/auth";
import { GitHubMark, GoogleMark } from "./brandIcons";

const providerMarks = { google: GoogleMark, github: GitHubMark };

export default function ProviderButton({
  provider,
  next,
}: {
  provider: OAuthProvider;
  next: string;
}) {
  const { t } = useTranslation();
  const Mark = providerMarks[provider];
  return (
    <a
      href={oauthLoginUrl(provider, next)}
      className="border-hair bg-ground text-ink hover:bg-well flex min-h-11 items-center justify-center gap-2.5 rounded-lg border text-sm font-medium no-underline"
    >
      <Mark />
      {t(`auth.continueWith.${provider}`)}
    </a>
  );
}
