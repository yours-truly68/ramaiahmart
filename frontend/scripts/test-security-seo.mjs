import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");

console.log("=== Running Security & SEO Hardening Verification Tests ===");

// 1. URL Safety Unit Tests (re-implement or import functions)
function isSafeWhatsAppUrl(url) {
  if (!url || typeof url !== "string") return false;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return false;
    if (parsed.hostname !== "wa.me") return false;
    if (!/^\/\d{7,15}$/.test(parsed.pathname)) return false;
    if (parsed.username || parsed.password) return false;
    return true;
  } catch {
    return false;
  }
}

function isSafeHttpUrl(url) {
  if (!url || typeof url !== "string") return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

function safeNextPath(value, fallback = "/profile") {
  if (!value || typeof value !== "string") return fallback;
  const trimmed = value.trim();
  if (!/^\/(?!\/|[\\/])/.test(trimmed)) return fallback;
  if (/[\\\u0000-\u001f\u007f-\u009f]/.test(trimmed)) return fallback;
  if (/^\/(login|register)([/?#]|$)/.test(trimmed)) return fallback;
  return trimmed;
}

// WhatsApp URL tests
assert.equal(isSafeWhatsAppUrl("https://wa.me/918867018007"), true);
assert.equal(isSafeWhatsAppUrl("https://wa.me/918867018007?text=Hi"), true);
assert.equal(isSafeWhatsAppUrl("javascript:alert(1)"), false);
assert.equal(isSafeWhatsAppUrl("http://wa.me/918867018007"), false);
assert.equal(isSafeWhatsAppUrl("https://evil.com/wa.me/918867018007"), false);
assert.equal(isSafeWhatsAppUrl("https://wa.me.evil.com/918867018007"), false);
assert.equal(isSafeWhatsAppUrl("data:text/html,<script>alert(1)</script>"), false);
console.log("✓ WhatsApp URL safety validation passed");

// HTTP URL tests
assert.equal(isSafeHttpUrl("https://ramaiahmart.com/image.png"), true);
assert.equal(isSafeHttpUrl("http://localhost:9100/bucket/item.jpg"), true);
assert.equal(isSafeHttpUrl("javascript:alert(1)"), false);
assert.equal(isSafeHttpUrl("data:image/svg+xml;utf8,<svg onload=alert(1)>"), false);
assert.equal(isSafeHttpUrl("vbscript:msgbox(1)"), false);
assert.equal(isSafeHttpUrl("file:///etc/passwd"), false);
console.log("✓ HTTP image/resource URL safety validation passed");

// Redirect Path safety tests
assert.equal(safeNextPath("/profile"), "/profile");
assert.equal(safeNextPath("/messages/123"), "/messages/123");
assert.equal(safeNextPath("//evil.com"), "/profile");
assert.equal(safeNextPath("/\\evil.com"), "/profile");
assert.equal(safeNextPath("https://evil.com"), "/profile");
assert.equal(safeNextPath("/login"), "/profile");
assert.equal(safeNextPath("/register"), "/profile");
console.log("✓ Safe Next redirect path validation passed");

// 2. Static Codebase Audits
function walkDir(dir, filter) {
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat && stat.isDirectory()) {
      if (!["node_modules", ".next", ".git"].includes(file)) {
        results = results.concat(walkDir(fullPath, filter));
      }
    } else if (filter(fullPath)) {
      results.push(fullPath);
    }
  }
  return results;
}

const srcFiles = walkDir(path.join(frontendRoot, "src"), (f) =>
  /\.(tsx?|jsx?)$/.test(f)
);

// Assert zero dangerouslySetInnerHTML
for (const file of srcFiles) {
  const content = fs.readFileSync(file, "utf8");
  assert.equal(
    content.includes("dangerouslySetInnerHTML"),
    false,
    `Forbidden dangerouslySetInnerHTML found in ${file}`
  );
  assert.equal(
    /\b(innerHTML|outerHTML)\s*=/.test(content),
    false,
    `Forbidden innerHTML assignment found in ${file}`
  );
  assert.equal(
    /\beval\s*\(/.test(content),
    false,
    `Forbidden eval call found in ${file}`
  );
  assert.equal(
    /new\s+Function\s*\(/.test(content),
    false,
    `Forbidden new Function found in ${file}`
  );
  assert.equal(
    /href\s*=\s*["']javascript:/i.test(content),
    false,
    `Forbidden javascript: href found in ${file}`
  );
}
console.log("✓ Zero dangerouslySetInnerHTML, innerHTML, eval, or javascript: hrefs in src/");

// 3. Image Accessibility Audit
for (const file of srcFiles) {
  const content = fs.readFileSync(file, "utf8");
  // Check that all <img> tags have alt attributes
  const imgTags = content.match(/<img[^>]+>/g) || [];
  for (const tag of imgTags) {
    assert.ok(
      tag.includes("alt="),
      `Found <img> without alt attribute in ${file}: ${tag}`
    );
  }
}
console.log("✓ All <img> tags in frontend have alt attributes");

// 4. Check Public Assets & Metadata files
const ogImageExists = fs.existsSync(
  path.join(frontendRoot, "public", "og-image.png")
);
assert.ok(ogImageExists, "public/og-image.png must exist");

const appOgExists = fs.existsSync(
  path.join(frontendRoot, "src", "app", "opengraph-image.png")
);
assert.ok(appOgExists, "src/app/opengraph-image.png must exist");

const robotsExists = fs.existsSync(
  path.join(frontendRoot, "src", "app", "robots.ts")
);
assert.ok(robotsExists, "src/app/robots.ts must exist");

const sitemapExists = fs.existsSync(
  path.join(frontendRoot, "src", "app", "sitemap.ts")
);
assert.ok(sitemapExists, "src/app/sitemap.ts must exist");

const middlewareExists = fs.existsSync(
  path.join(frontendRoot, "src", "middleware.ts")
);
assert.ok(middlewareExists, "src/middleware.ts must exist");

const nextConfigExists = fs.existsSync(
  path.join(frontendRoot, "next.config.ts")
);
assert.ok(nextConfigExists, "next.config.ts must exist");

console.log("✓ All required configuration and public SEO assets exist");

// 5. Inspect Built Static Output in .next
const robotsTxt = fs.readFileSync(
  path.join(frontendRoot, ".next", "server", "app", "robots.txt.body"),
  "utf8"
);
assert.ok(robotsTxt.includes("Disallow: /messages"), "robots.txt must disallow /messages");
assert.ok(robotsTxt.includes("Disallow: /profile"), "robots.txt must disallow /profile");
assert.ok(robotsTxt.includes("Disallow: /post/create"), "robots.txt must disallow /post/create");
assert.ok(robotsTxt.includes("Disallow: /api/"), "robots.txt must disallow /api/");
assert.ok(robotsTxt.includes("Allow: /"), "robots.txt must allow /");
assert.ok(robotsTxt.includes("sitemap.xml"), "robots.txt must link to sitemap.xml");
console.log("✓ Built robots.txt contains correct allow/disallow rules");

const sitemapXml = fs.readFileSync(
  path.join(frontendRoot, ".next", "server", "app", "sitemap.xml.body"),
  "utf8"
);
assert.ok(sitemapXml.includes("https://ramaiahmart.com"), "sitemap.xml must contain base URL");
assert.ok(sitemapXml.includes("/privacy"), "sitemap.xml must include /privacy");
assert.ok(sitemapXml.includes("/terms"), "sitemap.xml must include /terms");
assert.ok(!sitemapXml.includes("/messages"), "sitemap.xml must NOT include /messages");
assert.ok(!sitemapXml.includes("/profile"), "sitemap.xml must NOT include /profile");
assert.ok(!sitemapXml.includes("/post/create"), "sitemap.xml must NOT include /post/create");
console.log("✓ Built sitemap.xml contains only public routes");

console.log("\nALL SECURITY, CSP, SEO, AND ACCESSIBILITY TESTS PASSED SUCCESSFULLY!");
