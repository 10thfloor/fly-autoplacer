// Start both applications with their committed dependency locks.
// Run: deno run -A local-dev.ts
async function run(command: string, args: string[], cwd: string): Promise<void> {
  const result = await new Deno.Command(command, {
    args, cwd, stdin: "inherit", stdout: "inherit", stderr: "inherit",
  }).output();
  if (!result.success) throw new Error(`${command} failed with exit code ${result.code}`);
}

async function findPython(): Promise<string> {
  for (const candidate of [Deno.env.get("PYTHON"), "python3.12", "python3.11", "python3"].filter(Boolean) as string[]) {
    try {
      const result = await new Deno.Command(candidate, {
        args: ["-c", "import sys; sys.exit(not ((3, 11) <= sys.version_info[:2] < (3, 13)))"],
        stdout: "null", stderr: "null",
      }).output();
      if (result.success) return candidate;
    } catch { /* Try the next installed interpreter. */ }
  }
  throw new Error("Python 3.11 or 3.12 is required. Install one, or set PYTHON to its path.");
}

const children: Deno.ChildProcess[] = [];
let stopping = false;
function stopChildren() {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    try { child.kill("SIGTERM"); } catch { /* Already exited. */ }
  }
}

try {
  for (const path of ["placer-service/.env", "placer-dashboard/.env"]) {
    try { await Deno.stat(path); }
    catch { throw new Error(`Create ${path} using the README configuration before starting.`); }
  }
  const python = await findPython();
  await run(python, ["-m", "venv", ".venv"], "./placer-service");
  const venvPython = Deno.build.os === "windows" ? ".venv/Scripts/python.exe" : ".venv/bin/python";
  await run(venvPython, ["-m", "pip", "install", "--require-hashes", "-r", "requirements-dev.txt"], "./placer-service");
  await run("deno", ["install", "--frozen", "--allow-scripts=npm:esbuild"], "./placer-dashboard");

  for (const signal of ["SIGINT", "SIGTERM"] as const) Deno.addSignalListener(signal, stopChildren);
  children.push(new Deno.Command(venvPython, {
    args: ["main.py"], cwd: "./placer-service", stdin: "inherit", stdout: "inherit", stderr: "inherit",
  }).spawn());
  children.push(new Deno.Command("deno", {
    args: ["task", "dev"], cwd: "./placer-dashboard", stdin: "inherit", stdout: "inherit", stderr: "inherit",
  }).spawn());
  const first = await Promise.race(children.map((child) => child.status));
  stopChildren();
  const shutdownTimeout = setTimeout(() => {
    for (const child of children) { try { child.kill("SIGKILL"); } catch { /* Already exited. */ } }
  }, 10000);
  await Promise.all(children.map((child) => child.status));
  clearTimeout(shutdownTimeout);
  Deno.exit(first.code);
} catch (error) {
  stopChildren();
  console.error(error instanceof Error ? error.message : String(error));
  Deno.exit(1);
}
