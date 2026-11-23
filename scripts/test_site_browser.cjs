#!/usr/bin/env node
/* Exercise the generated site through the same repository path GitHub Pages uses. */
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const puppeteer = require("puppeteer");

const repo = path.resolve(__dirname, "..");
const site = path.join(repo, "site");
const basePath = "/open-weight-agent-stack/";
// The manual's diagram count, stated once. It appeared as five separate literals
// in this file, which is the same drift risk the count invariants exist to remove.
const EXPECTED_DIAGRAMS = 20;
const simulateMermaidFailure = process.argv.includes("--simulate-mermaid-failure");
const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".css", "text/css; charset=utf-8"],
]);

function closeServer(server) {
  if (!server.listening) return Promise.resolve();
  return new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
}

function createSiteServer() {
  return http.createServer((request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");
    if (!url.pathname.startsWith(basePath)) {
      response.writeHead(404).end("outside Pages repository path");
      return;
    }
    let relativePath;
    try {
      relativePath = decodeURIComponent(url.pathname.slice(basePath.length)) || "index.html";
    } catch {
      response.writeHead(400).end("invalid URL encoding");
      return;
    }
    const file = path.resolve(site, relativePath);
    if (file !== site && !file.startsWith(`${site}${path.sep}`)) {
      response.writeHead(403).end("path traversal rejected");
      return;
    }
    try {
      const body = fs.readFileSync(file);
      response.writeHead(200, { "Content-Type": contentTypes.get(path.extname(file)) || "application/octet-stream" });
      response.end(body);
    } catch (error) {
      if (error && error.code === "ENOENT") {
        response.writeHead(404).end("not found");
        return;
      }
      response.writeHead(500).end("could not serve test fixture");
    }
  });
}

async function listen(server) {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("hermetic browser server did not receive a TCP port");
  }
  return `http://127.0.0.1:${address.port}${basePath}`;
}

function collectBrowserSignals(page, baseUrl) {
  const consoleErrors = [];
  const failedRequests = [];
  const failedResponses = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(`page error: ${error.message}`));
  page.on("requestfailed", (request) => failedRequests.push(`${request.url()}: ${request.failure()?.errorText || "unknown failure"}`));
  page.on("response", (response) => {
    if (response.url().startsWith(baseUrl) && response.status() >= 400) {
      failedResponses.push(`${response.status()} ${response.url()}`);
    }
  });
  return { consoleErrors, failedRequests, failedResponses };
}

// WCAG 2.x contrast for every visible text element, measured from computed styles.
// Backgrounds are resolved by walking ancestors and compositing translucent layers
// (colours and gradient stops) over the nearest opaque one; the worst stop wins.
// Mermaid's own SVG internals are drawn on Mermaid's node fills, so they are
// excluded; HTML labels inside them are checked to inherit their colour instead.
function auditContrastInPage() {
  const parse = (value) => {
    const m = value.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const colours = (value) => (value.match(/rgba?\([^)]+\)/g) || []).map(parse);
  const over = (top, under) => {
    const a = top.a;
    return { r: top.r * a + under.r * (1 - a), g: top.g * a + under.g * (1 - a), b: top.b * a + under.b * (1 - a), a: 1 };
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const ratio = (x, y) => { const [a, b] = [lum(x), lum(y)].sort((m, n) => n - m); return (a + 0.05) / (b + 0.05); };
  const mix = (x, y, t) => ({ r: x.r + (y.r - x.r) * t, g: x.g + (y.g - x.g) * t, b: x.b + (y.b - x.b) * t, a: x.a + (y.a - x.a) * t });
  // A top-to-bottom linear gradient is sampled at the text's own height; any other
  // gradient contributes all of its stops, so the worst one decides.
  const sampleGradient = (gradient, el, textY) => {
    const stops = Array.from(gradient.matchAll(/(rgba?\([^)]+\))\s*(-?[\d.]+)%/g), (m) => ({ c: parse(m[1]), at: Number(m[2]) / 100 }));
    const vertical = /^linear-gradient\(\s*(rgba?\(|180deg|to bottom)/.test(gradient);
    if (!vertical || stops.length < 2) return colours(gradient);
    const box = el.getBoundingClientRect();
    const t = Math.min(1, Math.max(0, (textY - box.top) / (box.height || 1)));
    for (let i = 1; i < stops.length; i += 1) {
      if (t <= stops[i].at) {
        const span = stops[i].at - stops[i - 1].at || 1;
        return [mix(stops[i - 1].c, stops[i].c, Math.max(0, (t - stops[i - 1].at) / span))];
      }
    }
    return [stops[stops.length - 1].c];
  };
  const layersOf = (el, textY) => {
    const style = getComputedStyle(el);
    const layers = [];
    const image = style.backgroundImage;
    if (image && image !== "none") {
      // Each top-level comma-separated gradient is a layer; the first listed is painted on top.
      const gradients = [];
      let depth = 0;
      let start = 0;
      for (let i = 0; i < image.length; i += 1) {
        if (image[i] === "(") depth += 1;
        else if (image[i] === ")") depth -= 1;
        else if (image[i] === "," && depth === 0) { gradients.push(image.slice(start, i).trim()); start = i + 1; }
      }
      gradients.push(image.slice(start).trim());
      for (const g of gradients.reverse()) {
        const stops = sampleGradient(g, el, textY);
        if (stops.length) layers.push(stops);
      }
    }
    const bg = parse(style.backgroundColor);
    if (bg && bg.a > 0) layers.unshift([bg]);
    return layers; // bottom to top
  };
  const backgroundsFor = (el) => {
    const own = el.getBoundingClientRect();
    const textY = own.top + own.height / 2;
    const stack = [];
    for (let node = el; node; node = node.parentElement) {
      const layers = layersOf(node, textY);
      for (let i = layers.length - 1; i >= 0; i -= 1) {
        stack.push(layers[i]);
        if (layers[i].every((c) => c.a >= 1)) {
          let candidates = layers[i];
          for (let j = stack.length - 2; j >= 0; j -= 1) {
            candidates = candidates.flatMap((under) => stack[j].map((top) => over(top, under)));
          }
          return candidates;
        }
      }
    }
    return [{ r: 255, g: 255, b: 255, a: 1 }];
  };
  const visible = (el) => {
    const box = el.getBoundingClientRect();
    if (box.width <= 1 || box.height <= 1) return false;
    for (let node = el; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return false;
    }
    return true;
  };
  const failures = [];
  let checked = 0;
  const elements = Array.from(document.querySelectorAll("body *")).filter((el) => {
    if (el.closest(".plate-body svg, .figview-body svg")) return false;
    if (el.closest("svg") && el.tagName.toLowerCase() !== "text") return false;
    return Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim());
  });
  for (const el of elements) {
    if (!visible(el)) continue;
    const style = getComputedStyle(el);
    const isSvgText = el.tagName.toLowerCase() === "text";
    const fg = parse(isSvgText ? style.fill : style.color);
    if (!fg) continue;
    const backgrounds = backgroundsFor(el);
    const ink = fg.a < 1 ? over(fg, backgrounds[0]) : fg;
    const worst = Math.min(...backgrounds.map((bg) => ratio(ink, bg)));
    const size = parseFloat(style.fontSize);
    const bold = Number(style.fontWeight) >= 700;
    const large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5;
    checked += 1;
    if (worst < need) {
      const name = el.tagName.toLowerCase() + (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).join(".") : "");
      failures.push(`${name} "${el.textContent.trim().slice(0, 40)}" ${worst.toFixed(2)}:1 (needs ${need}:1)`);
    }
  }
  for (const strong of document.querySelectorAll(".plate-body svg strong, .figview-body svg strong")) {
    if (getComputedStyle(strong).color !== getComputedStyle(strong.parentElement).color) {
      failures.push("a Mermaid label's <strong> does not inherit its label colour");
      break;
    }
  }
  return { checked, failures: Array.from(new Set(failures)) };
}

async function auditContrast(page, label) {
  const failures = [];
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => {
      document.documentElement.setAttribute("data-theme", value);
      // Buttons transition their background, so settle every animation before measuring.
      for (const animation of document.getAnimations()) animation.finish();
    }, theme);
    const result = await page.evaluate(auditContrastInPage);
    if (result.checked < 20) failures.push(`${label} ${theme}: only ${result.checked} text elements were measured`);
    failures.push(...result.failures.map((message) => `${label} ${theme}: ${message}`));
  }
  await page.evaluate(() => document.documentElement.setAttribute("data-theme", "light"));
  return failures;
}

async function inspectNormalSite(page) {
  await page.waitForFunction((expected) => {
    const plates = Array.from(document.querySelectorAll(".plate-body"));
    return plates.length === expected && plates.every((plate) => plate.querySelector("svg"));
  }, { timeout: 30000 }, EXPECTED_DIAGRAMS);

  return page.evaluate(() => {
    const plates = Array.from(document.querySelectorAll(".plate-body"));
    const svgs = Array.from(document.querySelectorAll(".plate-body svg"));
    const hidden = svgs.filter((svg) => {
      const box = svg.getBoundingClientRect();
      const style = getComputedStyle(svg);
      return box.width < 10 || box.height < 10 || style.display === "none" || style.visibility === "hidden";
    }).length;
    const images = Array.from(document.images).filter((image) => !image.complete || image.naturalWidth === 0).length;
    const unsafeLinks = Array.from(document.querySelectorAll("a[href]"))
      .map((anchor) => anchor.getAttribute("href"))
      .filter((href) => href && (href.startsWith("docs/") || href.startsWith("/") || href.startsWith("../")));
    return {
      plates: plates.length,
      svgs: svgs.length,
      hidden,
      images,
      unsafeLinks,
      csp: Boolean(document.querySelector('meta[http-equiv="Content-Security-Policy"]')),
      content: document.body.innerText.includes("Task-to-model routing"),
      fallbackCount: document.querySelectorAll(".mermaid-fallback").length,
      sections: Array.from(document.querySelectorAll("main > section")).map((section) => {
        const style = getComputedStyle(section);
        return {
          id: section.id,
          opacity: style.opacity,
          visibility: style.visibility,
          text: section.innerText,
        };
      }),
    };
  });
}

// At desktop width the contents list is sticky beside the manual, so a diagram must start to its
// right, and Mermaid must not lay one edge label over another.
async function inspectDesktopLayout(page, baseUrl) {
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(baseUrl, { waitUntil: "networkidle0" });
  await page.waitForFunction(() => document.querySelectorAll(".plate-body svg").length > 0, { timeout: 30000 });
  return page.evaluate(() => {
    const failures = [];
    const toc = document.querySelector("nav.toc");
    const tocRight = toc.getBoundingClientRect().right;
    for (const body of document.querySelectorAll(".plate-body")) {
      if (body.getBoundingClientRect().left < tocRight) {
        const label = body.closest("figure").querySelector(".fno")?.textContent || "a figure";
        failures.push(`${label} starts under the contents list`);
      }
    }
    for (const svg of document.querySelectorAll(".plate-body svg")) {
      const labels = Array.from(svg.querySelectorAll(".edgeLabel p"))
        .filter((label) => label.textContent.trim())
        .map((label) => ({ text: label.textContent.trim(), box: label.getBoundingClientRect() }));
      for (let i = 0; i < labels.length; i += 1) {
        for (let j = i + 1; j < labels.length; j += 1) {
          const a = labels[i].box;
          const b = labels[j].box;
          if (a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1) {
            failures.push(`diagram labels overlap: "${labels[i].text}" and "${labels[j].text}"`);
          }
        }
      }
    }
    return failures;
  });
}

async function inspectMermaidFailure(page) {
  await page.waitForFunction((expected) => document.querySelectorAll(".mermaid-fallback").length === expected, { timeout: 30000 }, EXPECTED_DIAGRAMS);
  return page.evaluate(() => Array.from(document.querySelectorAll(".mermaid-fallback"), (element) => ({
    text: element.textContent,
    visible: element.getBoundingClientRect().width > 10 && element.getBoundingClientRect().height > 10,
  })));
}

async function run() {
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "owas-browser-"));
  const server = createSiteServer();
  let browser;
  try {
    const baseUrl = await listen(server);
    browser = await puppeteer.launch({
      headless: true,
      executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || await puppeteer.executablePath(),
      userDataDir,
    });
    const page = await browser.newPage();
    const signals = collectBrowserSignals(page, baseUrl);
    const interceptionErrors = [];
    if (simulateMermaidFailure) {
      await page.setRequestInterception(true);
      page.on("request", (request) => {
        if (request.url() === `${baseUrl}mermaid.min.js`) {
          void request.respond({
            status: 200,
            contentType: "text/javascript; charset=utf-8",
            body: "window.mermaid={initialize(){},run(){return Promise.reject(new Error('synthetic Mermaid run failure'));}};",
          }).catch((error) => interceptionErrors.push(`could not inject Mermaid failure: ${error.message}`));
          return;
        }
        void request.continue().catch((error) => interceptionErrors.push(`could not continue request: ${error.message}`));
      });
    }
    await page.goto(baseUrl, { waitUntil: "networkidle0" });

    if (simulateMermaidFailure) {
      const fallbacks = await inspectMermaidFailure(page);
      const unexpectedErrors = signals.consoleErrors.filter((message) => !message.includes("Mermaid failed to render diagrams"));
      const failures = [
        ...(fallbacks.length === EXPECTED_DIAGRAMS ? [] : [`expected ${EXPECTED_DIAGRAMS} Mermaid fallbacks, saw ${fallbacks.length}`]),
        ...fallbacks.filter((item) => !item.visible || item.text !== "Diagram unavailable: Mermaid rendering failed. See the manual source.")
          .map(() => "Mermaid fallback was not safely visible with its expected text"),
        ...(signals.consoleErrors.some((message) => message.includes("Mermaid failed to render diagrams")) ? [] : ["synthetic Mermaid failure was not logged"]),
        ...unexpectedErrors.map((message) => `unexpected console error: ${message}`),
        ...signals.failedRequests.map((message) => `failed request: ${message}`),
        ...signals.failedResponses.map((message) => `failed response: ${message}`),
        ...interceptionErrors,
      ];
      if (failures.length) throw new Error(failures.join("\n"));
      console.log(`browser failure-path passed: synthetic Mermaid run failure produced ${EXPECTED_DIAGRAMS} visible safe fallbacks`);
      return;
    }

    const result = await inspectNormalSite(page);
    const section23 = result.sections.find((section) => section.id === "23-platform-and-sdk-choice");
    const section27 = result.sections.find((section) => section.id === "27-sources-and-verification");
    const hiddenSections = result.sections.filter((section) => section.opacity !== "1" || section.visibility === "hidden");
    const failures = [
      ...(result.plates === EXPECTED_DIAGRAMS && result.svgs === EXPECTED_DIAGRAMS ? [] : [`expected all ${EXPECTED_DIAGRAMS} Mermaid diagrams as SVGs, saw ${result.svgs}/${result.plates}`]),
      ...(result.hidden ? [`${result.hidden} Mermaid SVGs are not visible`] : []),
      ...(result.images ? [`${result.images} images did not load`] : []),
      ...(result.unsafeLinks.length ? [`deploy-unsafe links: ${result.unsafeLinks.join(", ")}`] : []),
      ...(result.csp ? [] : ["generated site is missing its meta CSP"]),
      ...(result.content ? [] : ["generated manual content is missing"]),
      ...(result.fallbackCount ? [`normal Mermaid rendering unexpectedly used ${result.fallbackCount} fallbacks`] : []),
      ...(result.sections.length === 27 ? [] : [`expected 27 numbered sections, saw ${result.sections.length}`]),
      ...(hiddenSections.length ? [`sections hidden from view: ${hiddenSections.map((section) => section.id).join(", ")}`] : []),
      ...(section23 && section23.text.includes("Claude Agent SDK") && section23.text.includes("23.5 Where it runs in the cloud") ? [] : ["section 23 is missing its platform and SDK content"]),
      ...(section27 && section27.text.includes("Last verified") && section27.text.includes("27.7 Deployment memory catalogue") ? [] : ["section 27 is missing its sources and verification content"]),
      ...signals.consoleErrors.map((message) => `console error: ${message}`),
      ...signals.failedRequests.map((message) => `failed request: ${message}`),
      ...signals.failedResponses.map((message) => `failed response: ${message}`),
    ];
    if (failures.length) throw new Error(failures.join("\n"));
    console.log(`browser normal-path passed: all ${EXPECTED_DIAGRAMS} Mermaid diagrams rendered with deploy-safe links and no failed requests`);

    const contrastFailures = await auditContrast(page, "index.html");
    await page.click(".plate-zoom");
    await page.waitForSelector("dialog.figview[open] .figview-body svg");
    contrastFailures.push(...await auditContrast(page, "index.html full-size viewer"));
    await page.click(".figview-close");

    for (const companion of ["architecture.html", "models.html"]) {
      await page.goto(`${baseUrl}${companion}`, { waitUntil: "networkidle0" });
      const companionResult = await page.evaluate(() => ({
        csp: Boolean(document.querySelector('meta[http-equiv="Content-Security-Policy"]')),
        title: document.title,
        unsafeLinks: Array.from(document.querySelectorAll("a[href]"))
          .map((anchor) => anchor.getAttribute("href"))
          .filter((href) => href && (href.startsWith("docs/") || href.startsWith("/") || href.startsWith("../"))),
      }));
      const companionFailures = [
        ...(companionResult.csp ? [] : [`${companion} is missing its meta CSP`]),
        ...(companionResult.title ? [] : [`${companion} has an empty title`]),
        ...(companionResult.unsafeLinks.length ? [`${companion} deploy-unsafe links: ${companionResult.unsafeLinks.join(", ")}`] : []),
      ];
      if (companionFailures.length) throw new Error(companionFailures.join("\n"));
      contrastFailures.push(...await auditContrast(page, companion));
    }
    if (contrastFailures.length) throw new Error(`text below WCAG AA contrast:\n${contrastFailures.join("\n")}`);
    console.log("browser contrast-path passed: every visible text element meets WCAG AA in light and dark themes");
    console.log("browser companion-path passed: architecture.html and models.html are deploy-safe");

    const layoutFailures = await inspectDesktopLayout(page, baseUrl);
    if (layoutFailures.length) throw new Error(`desktop layout:\n${layoutFailures.join("\n")}`);
    console.log("browser layout-path passed: diagrams clear the contents list and no edge labels overlap at 1440px");
  } finally {
    if (browser) await browser.close();
    await closeServer(server);
    fs.rmSync(userDataDir, { recursive: true, force: true });
  }
}

run().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
