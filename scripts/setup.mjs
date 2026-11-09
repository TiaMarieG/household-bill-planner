import { randomBytes } from "node:crypto";
import { copyFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import {
  BACKEND,
  ENV_FILE,
  FRONTEND,
  IS_WINDOWS,
  ROOT,
  fail,
  migrate,
  runNpm,
  runOrFail,
  startDatabase,
  step,
  succeeds,
  venvPython,
} from "./lib.mjs";

const PLACEHOLDER_PASSWORD = "change-me";
const MIN_PYTHON_CHECK = "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)";

/** Find a Python 3.11+ to build the virtual environment with, skipping Windows' Store placeholder. */
function findPython() {
  const candidates = IS_WINDOWS
    ? [["py", ["-3"]], ["python", []], ["python3", []]]
    : [["python3", []], ["python", []]];
  for (const [command, prefix] of candidates) {
    if (succeeds(command, [...prefix, "-c", MIN_PYTHON_CHECK])) return [command, prefix];
  }
  return null;
}

/** Create .env from the example with a random local database password, unless it already exists. */
function createEnvFile() {
  step("Checking .env");
  if (existsSync(ENV_FILE)) {
    console.log(".env already exists; leaving it unchanged.");
    return;
  }
  copyFileSync(path.join(ROOT, ".env.example"), ENV_FILE);
  const password = randomBytes(18).toString("base64url");
  const contents = readFileSync(ENV_FILE, "utf8")
    .replaceAll("\r\n", "\n")
    .replaceAll(PLACEHOLDER_PASSWORD, password);
  writeFileSync(ENV_FILE, contents);
  console.log("Created .env with a random local database password.");
}

/** Create backend/.venv if needed and install the backend's Python packages into it. */
function installBackend(python) {
  step("Installing backend packages");
  if (!existsSync(venvPython())) {
    const [command, prefix] = python;
    runOrFail(command, [...prefix, "-m", "venv", ".venv"], { cwd: BACKEND }, "Could not create backend/.venv.");
  }
  runOrFail(
    venvPython(),
    ["-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-dev.txt"],
    { cwd: BACKEND },
    "pip install failed."
  );
}

/** Install the root dev runner and the frontend's npm packages. */
function installNodePackages() {
  step("Installing npm packages");
  if (runNpm(["install"], { cwd: ROOT }) !== 0) fail("npm install failed in the repo root.");
  if (runNpm(["install"], { cwd: FRONTEND }) !== 0) fail("npm install failed in frontend/.");
}

step("Checking prerequisites");
const python = findPython();
if (!python) fail("Python 3.11 or newer was not found. Install it from python.org, then rerun.");
if (!succeeds("docker", ["--version"])) fail("Docker was not found. Install Docker Desktop, then rerun.");
console.log(`Using ${python.flat().join(" ")} to create the virtual environment.`);

createEnvFile();
installBackend(python);
installNodePackages();
startDatabase();
migrate();

step("Setup complete");
console.log("Start the app with: npm run dev");
console.log("If a package-lock.json changed, commit it so you both install the same versions.");
