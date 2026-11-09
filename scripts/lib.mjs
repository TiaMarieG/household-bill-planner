import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const BACKEND = path.join(ROOT, "backend");
export const FRONTEND = path.join(ROOT, "frontend");
export const ENV_FILE = path.join(ROOT, ".env");
export const IS_WINDOWS = process.platform === "win32";

/** Path to the Python inside backend/.venv, which differs between Windows and macOS/Linux. */
export function venvPython() {
  return IS_WINDOWS
    ? path.join(BACKEND, ".venv", "Scripts", "python.exe")
    : path.join(BACKEND, ".venv", "bin", "python");
}

/** Print a step heading so long output is easy to follow. */
export function step(message) {
  console.log(`\n\x1b[36m==> ${message}\x1b[0m`);
}

/** Print an error and exit with a non-zero status. */
export function fail(message) {
  console.error(`\n\x1b[31mError:\x1b[0m ${message}`);
  process.exit(1);
}

/** Run a program with live output; return its exit code. Arguments are passed without a shell, so paths with spaces are safe. */
export function run(command, args, { cwd = ROOT } = {}) {
  const result = spawnSync(command, args, { cwd, stdio: "inherit" });
  if (result.error) return 1;
  return result.status ?? 1;
}

/** Run a program and stop everything with a clear message if it fails. */
export function runOrFail(command, args, options, failureMessage) {
  if (run(command, args, options) !== 0) fail(failureMessage);
}

/** Run npm without a shell by calling its JavaScript entry point through the current Node. */
export function runNpm(args, options) {
  const npmCli = process.env.npm_execpath;
  if (!npmCli) fail("Run this through npm, e.g. `npm run setup`.");
  return run(process.execPath, [npmCli, ...args], options);
}

/** True when a program exists and exits successfully with the given arguments. */
export function succeeds(command, args) {
  const result = spawnSync(command, args, { stdio: "ignore" });
  return !result.error && result.status === 0;
}

/** Stop with setup instructions if setup has not been run yet. */
export function requireSetup() {
  if (!existsSync(ENV_FILE) || !existsSync(venvPython())) {
    fail("The project isn't set up yet. Run `npm run setup` first.");
  }
}

/** Read KEY=VALUE pairs from .env, ignoring comments, blank lines and Windows line endings. */
export function readEnv() {
  const values = {};
  for (const line of readFileSync(ENV_FILE, "utf8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (match) values[match[1]] = match[2];
  }
  return values;
}

/** Database name at the end of a connection URL such as postgresql+psycopg://u:p@host:5432/name. */
export function databaseNameFrom(url) {
  const name = decodeURIComponent(new URL(url.replace(/^[a-z+]+:/, "postgresql:")).pathname.slice(1));
  if (!/^[A-Za-z0-9_]+$/.test(name)) fail(`Unexpected database name "${name}" in TEST_DATABASE_URL.`);
  return name;
}

/** Run psql inside the database container and return its trimmed output, or null if it failed. */
function psql(env, sql) {
  const result = spawnSync(
    "docker",
    ["compose", "exec", "-T", "db", "psql", "-U", env.POSTGRES_USER, "-d", env.POSTGRES_DB, "-tAc", sql],
    { cwd: ROOT, encoding: "utf8" }
  );
  return result.status === 0 ? result.stdout.trim() : null;
}

/** Create the test database named in TEST_DATABASE_URL if it does not exist yet. */
function ensureTestDatabase() {
  const env = readEnv();
  if (!env.TEST_DATABASE_URL) return;
  const name = databaseNameFrom(env.TEST_DATABASE_URL);
  const exists = psql(env, `SELECT 1 FROM pg_database WHERE datname = '${name}'`);
  if (exists === null) fail("Could not query Postgres. See why with: docker compose logs db");
  if (exists === "1") return;
  if (psql(env, `CREATE DATABASE "${name}"`) === null) fail(`Could not create the ${name} database.`);
  console.log(`Created test database ${name}.`);
}

/** Start the Postgres container, wait until it accepts connections, and make sure the test database exists. */
export function startDatabase() {
  step("Starting Postgres (Docker)");
  if (!succeeds("docker", ["info"])) {
    fail("Docker isn't running. Start Docker Desktop, then try again.");
  }
  runOrFail(
    "docker",
    ["compose", "up", "-d", "--wait", "db"],
    {},
    "Postgres failed to start. See why with: docker compose logs db"
  );
  ensureTestDatabase();
}

/** Bring the database schema up to date. */
export function migrate() {
  step("Applying database migrations");
  runOrFail(venvPython(), ["-m", "alembic", "upgrade", "head"], { cwd: BACKEND }, "Migrations failed.");
}
