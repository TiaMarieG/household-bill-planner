import { BACKEND, migrate, requireSetup, run, startDatabase, step, venvPython } from "./lib.mjs";

requireSetup();
startDatabase();
migrate();

step("Loading sample data");
process.exit(run(venvPython(), ["-m", "app.seed", ...process.argv.slice(2)], { cwd: BACKEND }));
