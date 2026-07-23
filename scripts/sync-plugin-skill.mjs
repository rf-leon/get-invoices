import { copyFile, mkdir, readFile, readdir, unlink } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const packageRoot = resolve(repoRoot, "skills/get-invoices");

async function listFiles(directory, base = directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) return listFiles(path, base);
      return [relative(base, path)];
    }),
  );
  return nested.flat().sort();
}

const sourceDirectories = ["agents", "providers", "references", "scripts"];
// Add personal provider recipes (account-specific state) here so they never
// ship in the packaged skill. Better: keep them in ~/.config/get-invoices/providers/.
const excludedFiles = new Set([
  "scripts/sync-plugin-skill.mjs",
  "scripts/lint-providers.py",
]);
const isGeneratedFile = (path) => path.includes("/__pycache__/") || path.endsWith(".pyc");
const files = [
  "SKILL.md",
  ...(
    await Promise.all(
      sourceDirectories.map(async (directory) =>
        (await listFiles(resolve(repoRoot, directory), repoRoot)).map((path) => path),
      ),
    )
  ).flat(),
]
  .filter((path) => !excludedFiles.has(path) && !isGeneratedFile(path))
  .sort();

async function check() {
  const packagedFiles = await listFiles(packageRoot, packageRoot);
  if (JSON.stringify(packagedFiles) !== JSON.stringify(files)) {
    throw new Error(
      `Packaged file list differs. Expected ${files.length}, found ${packagedFiles.length}.`,
    );
  }

  for (const path of files) {
    const [source, packaged] = await Promise.all([
      readFile(resolve(repoRoot, path)),
      readFile(resolve(packageRoot, path)),
    ]);
    if (!source.equals(packaged)) throw new Error(`Packaged copy is stale: ${path}`);
  }

  console.log(`Packaged skill matches ${files.length} source files.`);
}

async function sync() {
  for (const path of files) {
    const destination = resolve(packageRoot, path);
    await mkdir(dirname(destination), { recursive: true });
    await copyFile(resolve(repoRoot, path), destination);
  }

  // Prune anything in the mirror that is no longer expected (deleted or newly
  // excluded source files) so a plain sync never leaves sensitive files behind.
  const expected = new Set(files);
  const packagedFiles = await listFiles(packageRoot, packageRoot);
  const stale = packagedFiles.filter((path) => !expected.has(path));
  for (const path of stale) await unlink(resolve(packageRoot, path));

  console.log(
    `Synced ${files.length} files into skills/get-invoices/${stale.length ? ` (pruned ${stale.length} stale)` : ""}.`,
  );
}

if (process.argv.includes("--check")) {
  await check();
} else {
  await sync();
}
