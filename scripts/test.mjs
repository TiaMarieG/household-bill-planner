import { BACKEND, FRONTEND, requireSetup, run, runNpm, startDatabase, step, venvPython } from "./lib.mjs";

requireSetup();
startDatabase();

step("Backend tests (pytest)");
const backendStatus = run(venvPython(), ["-m", "pytest"], { cwd: BACKEND });

step("Frontend tests (vitest)");
const frontendStatus = runNpm(["test"], { cwd: FRONTEND });

step("Results");
console.log(`backend:  ${backendStatus === 0 ? "passed" : "FAILED"}`);
console.log(`frontend: ${frontendStatus === 0 ? "passed" : "FAILED"}`);
process.exit(backendStatus === 0 && frontendStatus === 0 ? 0 : 1);
