import fs from "node:fs";
import path from "node:path";

const PROFILES_TAG = "seccomp/v0.2.3";
const SOURCE = `https://raw.githubusercontent.com/moby/profiles/refs/tags/${PROFILES_TAG}/seccomp/default.json`;
const OUTPUT = path.join(process.cwd(), "infra", "seccomp", "chromium.json");

const response = await fetch(SOURCE);
if (!response.ok) {
  throw new Error(`${SOURCE}: HTTP ${response.status}`);
}

const profile = await response.json();

profile.syscalls.push({
  names: ["clone", "setns", "unshare"],
  action: "SCMP_ACT_ALLOW",
});

fs.writeFileSync(OUTPUT, JSON.stringify(profile, null, 2) + "\n");

console.log(`wrote ${OUTPUT} from ${SOURCE}`);
