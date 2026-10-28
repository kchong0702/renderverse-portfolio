import { execSync } from "node:child_process";
import { parseArgs } from "node:util";
import { pipeline } from "node:stream/promises";
import { Readable } from "node:stream";
import os from "node:os";
import path from "node:path";
import fs from "node:fs";
import https from "node:https";
import http from "node:http";

const MIN_PYTHON_MAJOR = 3;
const MIN_PYTHON_MINOR = 13;

const DEFAULT_PYTHON_VERSION = "3.13.0";

const root = process.cwd();

const pythonDir = path.join(root, ".python");
const venvDir = path.join(root, ".venv");

const platform = os.platform();
const arch = os.arch();
const isWin = platform === "win32";

const { values: flags } = parseArgs({
  options: {
    "python-version": { type: "string" },
    "python-tag": { type: "string" },
    help: { type: "boolean", short: "h" },
  },
  strict: false,
});

if (flags.help) {
  console.log(`Usage: node scripts/bootstrap-python.mjs [options]
    Options:
      --python-version <ver>   Python version to use  (default: ${DEFAULT_PYTHON_VERSION})
      --python-tag <tag>       indygreg release tag    (default: auto)
      -h, --help               Show this help`);
  process.exit(0);
}

// portable python binary
const VERSION_TAG_MAP = {
  "3.13.0": "20241016",
  "3.13.1": "20241016",
  "3.13.2": "20250214",
};

function resolveTag(version) {
  return flags["python-tag"] || VERSION_TAG_MAP[version] || "20241016";
}

function getDownloadUrl(version, tag) {
  let targetTriple = "";
  if (platform === "darwin") {
    targetTriple =
      arch === "arm64" ? "aarch64-apple-darwin" : "x86_64-apple-darwin";
  } else if (platform === "linux") {
    targetTriple = "x86_64-unknown-linux-gnu";
  } else if (platform === "win32") {
    targetTriple =
      arch === "arm64" ? "aarch64-pc-windows-msvc" : "x86_64-pc-windows-msvc";
  } else {
    throw new Error(`Unsupported platform: ${platform}`);
  }

  return `https://github.com/indygreg/python-build-standalone/releases/download/${tag}/cpython-${version}+${tag}-${targetTriple}-install_only.tar.gz`;
}

function getPythonBin() {
  return isWin
    ? path.join(pythonDir, "python.exe")
    : path.join(pythonDir, "bin", "python3");
}

async function downloadFile(url, destPath) {
  const res = await fetch(url, { redirect: "follow" });

  if (!res.ok) {
    throw new Error(`Download failed: HTTP ${res.status} ${res.statusText}`);
  }

  await pipeline(Readable.fromWeb(res.body), fs.createWriteStream(destPath));
}

function extractTarGz(archivePath, destDir) {
  fs.mkdirSync(destDir, { recursive: true });
  execSync(`tar -xzf "${archivePath}" -C "${destDir}"`, { stdio: "inherit" });
}

function findSystemPython() {
  const candidates = isWin ? ["python3", "python"] : ["python3", "python"];

  for (const cmd of candidates) {
    try {
      const output = execSync(`${cmd} --version`, {
        encoding: "utf-8",
        windowsHide: true,
      }).trim();

      const match = output.match(/Python\s+(\d+)\.(\d+)(?:\.(\d+))?/i);
      if (!match) continue;

      const major = parseInt(match[1], 10);
      const minor = parseInt(match[2], 10);

      if (
        major > MIN_PYTHON_MAJOR ||
        (major === MIN_PYTHON_MAJOR && minor >= MIN_PYTHON_MINOR)
      ) {
        try {
          execSync(`${cmd} -c "import venv"`, {
            windowsHide: true,
            stdio: "ignore",
          });
        } catch {
          console.log(
            `System Python ${output} found, but 'venv' module is missing (e.g. python3-venv).`,
          );
          continue;
        }

        console.log(`Found compatible system Python: ${output}`);
        return cmd;
      }
      console.log(
        `System Python too old: ${output} (need >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR})`,
      );
    } catch {
      continue;
    }
  }

  return null;
}

async function installPortablePython(version, tag) {
  const url = getDownloadUrl(version, tag);
  const archivePath = path.join(root, `.python-${version}.tar.gz`);

  console.log(`\nDownloading portable Python ${version}...`);
  console.log(`   URL: ${url}`);
  console.log(`   Platform: ${platform} (${arch})\n`);

  try {
    await downloadFile(url, archivePath);
    console.log("Download complete\n");

    console.log(`Extracting to ${pythonDir}...\n`);

    const extractDir = path.join(root, ".python-extract");
    if (fs.existsSync(extractDir)) {
      fs.rmSync(extractDir, { recursive: true, force: true });
    }
    fs.mkdirSync(extractDir, { recursive: true });

    extractTarGz(archivePath, extractDir);

    const entries = fs.readdirSync(extractDir);
    if (entries.length !== 1) {
      throw new Error(`Unexpected archive contents: ${entries.join(", ")}`);
    }

    const pythonRoot = path.join(extractDir, entries[0]);

    if (fs.existsSync(pythonDir)) {
      fs.rmSync(pythonDir, { recursive: true, force: true });
    }

    fs.renameSync(pythonRoot, pythonDir);

    fs.rmSync(extractDir, { recursive: true, force: true });
    if (fs.existsSync(archivePath)) fs.unlinkSync(archivePath);

    const pythonBin = getPythonBin();
    console.log(`Portable Python installed at: ${pythonBin}\n`);

    const versionOutput = execSync(`"${pythonBin}" --version`, {
      encoding: "utf-8",
      windowsHide: true,
    }).trim();
    console.log(`   ${versionOutput}\n`);

    return pythonBin;
  } catch (err) {
    if (fs.existsSync(archivePath)) fs.unlinkSync(archivePath);
    const extractDir = path.join(root, ".python-extract");
    if (fs.existsSync(extractDir))
      fs.rmSync(extractDir, { recursive: true, force: true });
    throw err;
  }
}

function createVenv(pythonBin) {
  if (fs.existsSync(venvDir)) {
    console.log(`Removing existing .venv...`);
    fs.rmSync(venvDir, { recursive: true, force: true });
  }

  console.log(`Creating virtual environment at .venv...\n`);

  execSync(`"${pythonBin}" -m venv "${venvDir}"`, {
    stdio: "inherit",
    windowsHide: true,
  });

  console.log(`\nVirtual environment created`);
}

function printActivationInstructions() {
  console.log(`\n──────────────────────────────────────────────`);
  console.log(`  Activate the virtual environment:`);
  console.log(`──────────────────────────────────────────────`);

  if (isWin) {
    console.log(`\n  PowerShell:`);
    console.log(`    .\\.venv\\Scripts\\Activate.ps1`);
    console.log(`\n  Command Prompt:`);
    console.log(`    .venv\\Scripts\\activate.bat`);
    console.log(`\n  Git Bash (MINGW):`);
    console.log(`    source .venv/Scripts/activate`);
  } else {
    console.log(`\n  bash / zsh:`);
    console.log(`source .venv/bin/activate`);
  }

  console.log(`\n──────────────────────────────────────────────\n`);
}

const pythonVersion =
  flags["python-version"] ||
  process.env.PYTHON_VERSION ||
  DEFAULT_PYTHON_VERSION;
const tag = resolveTag(pythonVersion);

console.log(`╔══════════════════════════════════════════════╗`);
console.log(
  `║     Python Bootstrap (>= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR})`,
);
console.log(`╚══════════════════════════════════════════════╝\n`);
console.log(`Requested version: ${pythonVersion}`);
console.log(`Platform: ${platform} (${arch})\n`);

const systemPython = findSystemPython();

let pythonBin;

if (systemPython) {
  pythonBin = systemPython;
} else {
  const existingPython = getPythonBin();
  if (fs.existsSync(existingPython)) {
    try {
      const output = execSync(`"${existingPython}" --version`, {
        encoding: "utf-8",
        windowsHide: true,
      }).trim();
      const match = output.match(/Python\s+(\d+)\.(\d+)/i);
      if (match) {
        const major = parseInt(match[1], 10);
        const minor = parseInt(match[2], 10);
        if (
          major > MIN_PYTHON_MAJOR ||
          (major === MIN_PYTHON_MAJOR && minor >= MIN_PYTHON_MINOR)
        ) {
          console.log(`Found existing portable Python: ${output}`);
          pythonBin = existingPython;
        }
      }
    } catch {}
  }

  if (!pythonBin) {
    console.log("No compatible system Python found.");
    console.log(
      `Installing portable Python ${pythonVersion} (tag: ${tag})...\n`,
    );

    pythonBin = await installPortablePython(pythonVersion, tag);
  }
}

createVenv(pythonBin);

printActivationInstructions();

console.log("✨ Bootstrap complete!\n");
