import concurrently from "concurrently";
import { BACKEND, FRONTEND, migrate, requireSetup, startDatabase, step, venvPython } from "./lib.mjs";

requireSetup();
startDatabase();
migrate();

step("Starting API (http://localhost:8000/docs) and web app (http://localhost:5173)");
const { result } = concurrently(
  [
    {
      name: "api",
      command: `"${venvPython()}" -m uvicorn app.main:app --reload --port 8000`,
      cwd: BACKEND,
      prefixColor: "magenta",
    },
    { name: "web", command: "npm run dev -- --port 5173 --strictPort", cwd: FRONTEND, prefixColor: "cyan" },
  ],
  { killOthersOn: ["failure", "success"], restartTries: 0 }
);

result.then(
  () => process.exit(0),
  () => process.exit(1)
);
