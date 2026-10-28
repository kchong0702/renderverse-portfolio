// Rejects AI attribution in commits and PRs, and enforces Conventional Commits.
// Shared by the husky hooks (.husky/) and the commit-policy GitHub workflow.
//
//   --message-file <path>  commit-msg hook: check the message being written
//   --pre-push <remote>    pre-push hook: check commits not yet on <remote> (refs on stdin)
//   --range <from>..<to>   CI: check every commit in the range, including identities
//   --pr                   CI: check the PR_TITLE and PR_BODY environment variables
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { parseArgs } from "node:util";

const AI_TOOL = String.raw`claude|anthropic|openai|chatgpt|gpt(?:-?\d[\w.-]*)?|codex|copilot|gemini|cursor|opencode|aider|devin|windsurf|codeium|tabnine|codewhisperer`;

const aiTool = new RegExp(String.raw`\b(?:${AI_TOOL})\b`, "i");
const aiEmail = new RegExp(
  String.raw`@(?:anthropic|openai)\.com\b|(?:^|[\s<+])(?:${AI_TOOL})(?:-[\w-]+)?(?:\[bot\])?@users\.noreply\.github\.com|\bcopilot@github\.com`,
  "i",
);
const aiName = new RegExp(
  String.raw`^(?:${AI_TOOL})(?:[\s-](?:code|agent|swe-agent|bot|assistant))?(?:\[bot\])?$`,
  "i",
);
const trailer =
  /^\s*(co-authored-by|generated-by|assisted-by|signed-off-by|ai-assisted-by|made-with)\s*:(.*)$/i;
const generatedLine = new RegExp(
  String.raw`^\s*(?:🤖\s*)?(?:generated|created|written|co-authored|assisted)\s+(?:with|by|using)\s+\[?(?:${AI_TOOL})\b`,
  "i",
);

const CONVENTIONAL = /^(feat|fix|refactor|chore)\([a-z0-9][a-z0-9.-]*\)!?: \S/;
const EXEMPT_SUBJECT = /^(Merge |Revert "|(fixup|squash|amend)! )/;
const ZERO_SHA = /^0+$/;

const { values: flags } = parseArgs({
  options: {
    "message-file": { type: "string" },
    "pre-push": { type: "string" },
    range: { type: "string" },
    pr: { type: "boolean" },
  },
});

function git(args) {
  return execFileSync("git", args, {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
}

function gitOk(args) {
  try {
    execFileSync("git", args, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

function findAttribution(text) {
  const reasons = [];
  for (const line of text.split("\n")) {
    const match = line.match(trailer);
    if (match && (aiTool.test(match[2]) || aiEmail.test(match[2]))) {
      reasons.push(`AI ${match[1]} trailer: "${line.trim()}"`);
    } else if (generatedLine.test(line)) {
      reasons.push(`AI "generated with" line: "${line.trim()}"`);
    } else if (aiEmail.test(line)) {
      reasons.push(`AI email address: "${line.trim()}"`);
    } else if (line.includes("🤖")) {
      reasons.push(`🤖 marker: "${line.trim()}"`);
    }
  }
  return reasons;
}

function checkSubject(message) {
  const subject = message.split("\n")[0];
  if (EXEMPT_SUBJECT.test(subject) || CONVENTIONAL.test(subject)) return [];
  return [
    `subject is not "type(scope): summary" with type feat, fix, refactor or chore: "${subject}"`,
  ];
}

function checkIdentity({ an, ae, cn, ce }) {
  const reasons = [];
  if (aiName.test(an) || aiEmail.test(ae))
    reasons.push(`AI author: ${an} <${ae}>`);
  if (aiName.test(cn) || aiEmail.test(ce))
    reasons.push(`AI committer: ${cn} <${ce}>`);
  return reasons;
}

function cleanMessage(raw) {
  const scissors = raw.search(/^# -+ >8 -+$/m);
  const text = scissors === -1 ? raw : raw.slice(0, scissors);
  return text
    .split("\n")
    .filter((line) => !line.startsWith("#"))
    .join("\n")
    .trim();
}

function readCommits(revArgs) {
  const out = git([
    "log",
    "--format=%H%x1f%P%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e",
    ...revArgs,
  ]);
  return out
    .split("\x1e")
    .filter((record) => record.trim())
    .map((record) => {
      const [sha, parents, an, ae, cn, ce, body] = record
        .replace(/^\n/, "")
        .split("\x1f");
      return {
        sha,
        parents: parents.split(" ").filter(Boolean),
        an,
        ae,
        cn,
        ce,
        message: body.trim(),
      };
    });
}

function checkCommits(commits) {
  return commits.map((commit) => ({
    label: `${commit.sha.slice(0, 7)} ${commit.message.split("\n")[0]}`,
    reasons: [
      ...checkIdentity(commit),
      ...findAttribution(commit.message),
      ...(commit.parents.length > 1 ? [] : checkSubject(commit.message)),
    ],
  }));
}

function prePushRevArgs(remote) {
  const remoteRefs = gitOk(["remote", "get-url", remote])
    ? `--remotes=${remote}`
    : "--remotes";
  const seen = new Set();
  const commits = [];
  for (const line of fs.readFileSync(0, "utf8").split("\n")) {
    const [, localSha] = line.trim().split(/\s+/);
    if (!localSha || ZERO_SHA.test(localSha)) continue;
    for (const commit of readCommits([localSha, "--not", remoteRefs])) {
      if (!seen.has(commit.sha)) {
        seen.add(commit.sha);
        commits.push(commit);
      }
    }
  }
  return commits;
}

function rangeCommits(range) {
  const [from, to] = range.split("..");
  if (
    !from ||
    ZERO_SHA.test(from) ||
    !gitOk(["cat-file", "-e", `${from}^{commit}`])
  ) {
    console.log(
      `Start of range ${from || "(none)"} is unknown; checking ${to} only.`,
    );
    return readCommits(["-1", to]);
  }
  return readCommits([`${from}..${to}`]);
}

let results;
if (flags["message-file"]) {
  const message = cleanMessage(fs.readFileSync(flags["message-file"], "utf8"));
  results = [
    {
      label: "commit message",
      reasons: [...findAttribution(message), ...checkSubject(message)],
    },
  ];
} else if (flags["pre-push"]) {
  results = checkCommits(prePushRevArgs(flags["pre-push"]));
} else if (flags.range) {
  results = checkCommits(rangeCommits(flags.range));
} else if (flags.pr) {
  results = [
    { label: "PR title", reasons: findAttribution(process.env.PR_TITLE ?? "") },
    {
      label: "PR description",
      reasons: findAttribution(process.env.PR_BODY ?? ""),
    },
  ];
} else {
  console.error(
    "Usage: check-ai-attribution.mjs --message-file <path> | --pre-push <remote> | --range <from>..<to> | --pr",
  );
  process.exit(2);
}

const failures = results.filter((result) => result.reasons.length);
if (!failures.length) process.exit(0);

for (const { label, reasons } of failures) {
  for (const reason of reasons) {
    if (process.env.GITHUB_ACTIONS)
      console.log(`::error title=${label}::${reason}`);
    else console.error(`✖ ${label}\n    ${reason}`);
  }
}
console.error(
  "\nCommits and PRs must not carry AI attribution and must follow Conventional Commits (see CLAUDE.md)." +
    "\nFix the message (git commit --amend, or git rebase -i for older commits) and try again.",
);
process.exit(1);
