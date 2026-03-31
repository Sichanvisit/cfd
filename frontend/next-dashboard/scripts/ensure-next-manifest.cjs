const fs = require("fs");
const path = require("path");

const root = process.cwd();
const serverDir = path.join(root, ".next", "server");
const manifestPath = path.join(serverDir, "middleware-manifest.json");

const defaultManifest = {
  version: 2,
  middleware: {},
  functions: {},
  sortedMiddleware: [],
};

try {
  if (!fs.existsSync(serverDir)) {
    fs.mkdirSync(serverDir, { recursive: true });
  }

  if (!fs.existsSync(manifestPath)) {
    fs.writeFileSync(manifestPath, JSON.stringify(defaultManifest, null, 2), "utf8");
    console.log("[ensure-next-manifest] created .next/server/middleware-manifest.json");
  }
} catch (err) {
  console.warn("[ensure-next-manifest] failed:", err?.message || err);
}

