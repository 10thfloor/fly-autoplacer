// @ts-nocheck

// This is a Deno script the executes the start of the placer-service and placer-dashboard
// From the command line run `deno -A local-dev.ts`
let node_modules: Deno.Process | null = null;
let poetry_lock: Deno.Process | null = null;

try {
  node_modules = await Deno.stat("./placer-dashboard/node_modules");
} catch (error) {
  console.log("node_modules not found, installing dependencies");
  node_modules = new Deno.Command("deno", {
    args: ["install", "--allow-scripts"],
    cwd: "./placer-dashboard",
    stdin: "inherit",
    stdout: "inherit",
    stderr: "inherit",
  }).spawn();
}

try {
  poetry_lock = await Deno.stat("./placer-service/poetry.lock");
} catch (error) {
  console.log("poetry.lock not found, installing dependencies");
  poetry_lock = new Deno.Command("poetry", {
    args: ["install"],
    cwd: "./placer-service",
    stdin: "inherit",
    stdout: "inherit",
    stderr: "inherit",
  }).spawn();
}

const result = await Promise.all([node_modules.status, poetry_lock.status]);

if (result[0] && result[0].code !== 0) {
  console.log("Failed to install dependencies in Placer Dashboard");
  Deno.exit(1);
}

if (result[1] && result[1].code !== 0) {
  console.log("Failed to install dependencies in Placer Service");
  Deno.exit(1);
}

// Start the placer-service
const placerService = new Deno.Command("poetry", {
  args: ["run", "python3", "main.py"],
  cwd: "./placer-service",
  stdin: "inherit",
  stdout: "inherit",
  stderr: "inherit",
}).spawn();

// Start the placer-dashboard
const placerDashboard = new Deno.Command("deno", {
  args: ["task", "dev"],
  cwd: "./placer-dashboard",
  stdin: "inherit",
  stdout: "inherit",
  stderr: "inherit",
}).spawn();

// Wait for both processes to exit
await Promise.all([placerService.status, placerDashboard.status]);
