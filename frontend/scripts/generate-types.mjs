import { access } from "node:fs/promises";
import { constants } from "node:fs";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(frontendDir, "..");
const backendDir = path.join(repoRoot, "backend");
const generatorScript = path.join(backendDir, "scripts", "generate_api_types.py");

async function exists(targetPath) {
  try {
    await access(targetPath, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

async function findCommand(command) {
  const probeCommand =
    process.platform === "win32"
      ? ["where.exe", [command]]
      : ["sh", ["-lc", `command -v ${command}`]];

  return new Promise((resolve) => {
    const child = spawn(probeCommand[0], probeCommand[1], {
      stdio: "ignore",
      shell: false,
    });

    child.on("error", () => resolve(null));
    child.on("exit", (code) => resolve(code === 0 ? command : null));
  });
}

async function main() {
  if (process.env.FARMATLAS_SKIP_GENERATE_TYPES === "1") {
    console.log("Skipping API type generation because FARMATLAS_SKIP_GENERATE_TYPES=1.");
    return;
  }

  const hasBackend = await exists(generatorScript);
  const uvCommand = await findCommand("uv");

  if (!hasBackend || !uvCommand) {
    const reasons = [];
    if (!hasBackend) reasons.push("backend generator files are not present");
    if (!uvCommand) reasons.push("uv is not installed");
    console.log(`Skipping API type generation: ${reasons.join(" and ")}.`);
    return;
  }

  await new Promise((resolve, reject) => {
    const child = spawn(
      uvCommand,
      ["run", "--directory", backendDir, "python", "scripts/generate_api_types.py"],
      {
        cwd: frontendDir,
        stdio: "inherit",
        shell: process.platform === "win32",
      }
    );

    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`Type generation failed with exit code ${code}.`));
    });
  });
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
