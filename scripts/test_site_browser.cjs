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
      content: document.body.innerText.includes("Performance-first build manual"),
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
