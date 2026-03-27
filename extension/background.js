const PAGE_WAIT_MS = 2000;
const activeRuns = new Map();
const CACHE_KEY = "linkedinEmailCache";
const PROFILE_SLEEP_MIN_MS = 3000;
const PROFILE_SLEEP_MAX_MS = 6000;

function configureSidePanelBehavior() {
  if (!chrome.sidePanel?.setPanelBehavior) {
    return;
  }
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }, () => {
    const message = chrome.runtime.lastError?.message || "";
    if (message) {
      console.log(`[LinkedIn Processor] Side panel setup warning: ${message}`);
    }
  });
}

configureSidePanelBehavior();
chrome.runtime.onInstalled.addListener(() => {
  configureSidePanelBehavior();
});
chrome.runtime.onStartup.addListener(() => {
  configureSidePanelBehavior();
});

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomBetween(min, max) {
  const safeMin = Math.ceil(min);
  const safeMax = Math.floor(max);
  return Math.floor(Math.random() * (safeMax - safeMin + 1)) + safeMin;
}

function updateTabUrl(tabId, url) {
  return new Promise((resolve, reject) => {
    chrome.tabs.update(tabId, { url }, (tab) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(tab);
    });
  });
}

function waitForTabComplete(tabId) {
  return new Promise((resolve) => {
    const listener = (updatedTabId, changeInfo) => {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
  });
}

function buildContactInfoUrl(profileUrl) {
  const clean = String(profileUrl || "").split("?")[0].split("#")[0].replace(/\/+$/, "");
  if (clean.includes("/overlay/contact-info")) {
    return `${clean}/`;
  }
  return `${clean}/overlay/contact-info/`;
}

function safeSendRuntimeMessage(payload) {
  try {
    chrome.runtime.sendMessage(payload, () => {
      const message = chrome.runtime.lastError?.message || "";
      if (message && !message.includes("Receiving end does not exist")) {
        console.log(`[LinkedIn Processor] Message warning: ${message}`);
      }
    });
  } catch (error) {
    console.log(`[LinkedIn Processor] Message send failed: ${error.message}`);
  }
}

function normalizeProfileUrl(profileUrl) {
  return String(profileUrl || "")
    .trim()
    .split("?")[0]
    .split("#")[0]
    .replace(/\/+$/, "");
}

function getCacheStore() {
  return new Promise((resolve) => {
    chrome.storage.local.get([CACHE_KEY], (result) => {
      const cache = result?.[CACHE_KEY];
      resolve(cache && typeof cache === "object" ? cache : {});
    });
  });
}

function setCacheStore(cache) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ [CACHE_KEY]: cache }, () => resolve());
  });
}

function runContactInfoScript(tabId) {
  return new Promise((resolve, reject) => {
    chrome.scripting.executeScript(
      {
        target: { tabId },
        func: async () => {
          const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

          const extractEmailsFromRoot = (root) => {
            const emailSet = new Set();
            const scope = root || document;
            const mailtoLinks = Array.from(scope.querySelectorAll("a[href^='mailto:']"));
            for (const link of mailtoLinks) {
              const href = link.getAttribute("href") || "";
              const email = href.replace(/^mailto:/i, "").split("?")[0].trim();
              if (email) {
                emailSet.add(email);
              }
            }

            const text = scope.innerText || "";
            const matches = text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [];
            for (const match of matches) {
              emailSet.add(match.trim());
            }

            return Array.from(emailSet);
          };

          const findContactDialog = () => {
            const dialogs = Array.from(document.querySelectorAll("dialog[open], [role='dialog']"));
            return dialogs.find((el) => {
              const title = (el.querySelector("h1,h2,h3,[aria-label]")?.innerText || "").toLowerCase();
              const text = (el.innerText || "").toLowerCase();
              return title.includes("contact info") || text.includes("contact info");
            });
          };

          const isOverlayPage = location.pathname.includes("/overlay/contact-info");
          let contactClicked = false;

          if (!isOverlayPage) {
            const contactLink = Array.from(document.querySelectorAll("a")).find((a) => {
              const text = (a.innerText || "").trim().toLowerCase();
              const href = (a.getAttribute("href") || "").toLowerCase();
              return text.includes("contact info") || href.includes("/overlay/contact-info");
            });
            if (contactLink) {
              contactLink.click();
              contactClicked = true;
            }
          }

          let dialog = findContactDialog();
          if (!isOverlayPage) {
            let attempts = 0;
            while (!dialog && attempts < 20) {
              await sleep(200);
              dialog = findContactDialog();
              attempts += 1;
            }
          }

          const rootForExtraction = isOverlayPage ? document.body : dialog;
          const primaryEmails = rootForExtraction ? extractEmailsFromRoot(rootForExtraction) : [];
          const fallbackEmails = primaryEmails.length ? [] : extractEmailsFromRoot(document.body);

          return {
            contactClicked,
            dialogOpened: Boolean(dialog),
            overlayPage: isOverlayPage,
            emails: primaryEmails.length ? primaryEmails : fallbackEmails,
          };
        },
      },
      (results) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(
          results?.[0]?.result || {
            contactClicked: false,
            dialogOpened: false,
            overlayPage: false,
            emails: [],
          }
        );
      }
    );
  });
}

async function processUrls({ tabId, urls, mode }) {
  if (!tabId || !Array.isArray(urls) || !urls.length) {
    throw new Error("Missing tab or URLs.");
  }

  const targets = mode === "single" ? urls.slice(0, 1) : urls;
  const report = [];
  const total = targets.length;
  let done = 0;
  let uncachedProcessedCount = 0;
  const cache = await getCacheStore();
  activeRuns.set(tabId, { cancelled: false });

  for (let index = 0; index < targets.length; index += 1) {
    const profileUrl = targets[index];
    const runState = activeRuns.get(tabId);
    if (runState?.cancelled) {
      console.log(`[LinkedIn Processor] Stopped by user for tab ${tabId}`);
      break;
    }

    const normalizedProfileUrl = normalizeProfileUrl(profileUrl);
    const cached = cache[normalizedProfileUrl];
    if (cached) {
      const result = {
        url: profileUrl,
        contactUrl: cached.contactUrl || buildContactInfoUrl(profileUrl),
        contactClicked: Boolean(cached.contactClicked),
        dialogOpened: Boolean(cached.dialogOpened),
        overlayPage: Boolean(cached.overlayPage),
        emails: Array.isArray(cached.emails) ? cached.emails : [],
        fromCache: true,
      };
      report.push(result);
      done += 1;
      safeSendRuntimeMessage({
        type: "PROCESS_PROGRESS",
        item: result,
        done,
        total,
        pending: total - done,
      });
      continue;
    }

    if (uncachedProcessedCount > 0) {
      const humanSleepMs = randomBetween(PROFILE_SLEEP_MIN_MS, PROFILE_SLEEP_MAX_MS);
      console.log(`[LinkedIn Processor] Human-like sleep ${humanSleepMs}ms before next uncached profile`);
      await delay(humanSleepMs);
    }

    const contactUrl = buildContactInfoUrl(profileUrl);
    await updateTabUrl(tabId, contactUrl);
    await waitForTabComplete(tabId);
    await delay(PAGE_WAIT_MS);
    try {
      const contactResult = await runContactInfoScript(tabId);
      const result = {
        url: profileUrl,
        contactUrl,
        contactClicked: contactResult.contactClicked,
        dialogOpened: contactResult.dialogOpened,
        overlayPage: contactResult.overlayPage,
        emails: contactResult.emails || [],
      };
      report.push(result);
      cache[normalizedProfileUrl] = {
        contactUrl,
        contactClicked: result.contactClicked,
        dialogOpened: result.dialogOpened,
        overlayPage: result.overlayPage,
        emails: result.emails,
        status: result.emails.length ? "found" : "not_found",
        updatedAt: Date.now(),
      };
      await setCacheStore(cache);
      if (result.emails.length > 0) {
        console.log(`[LinkedIn Processor] Email found for ${profileUrl}: ${result.emails.join(", ")}`);
      } else {
        console.log(`[LinkedIn Processor] No email found for ${profileUrl}`);
      }
      done += 1;
      uncachedProcessedCount += 1;
      safeSendRuntimeMessage({
        type: "PROCESS_PROGRESS",
        item: result,
        done,
        total,
        pending: total - done,
      });
    } catch (error) {
      const result = {
        url: profileUrl,
        contactUrl,
        contactClicked: false,
        dialogOpened: false,
        overlayPage: false,
        emails: [],
        error: error.message,
      };
      report.push(result);
      cache[normalizedProfileUrl] = {
        contactUrl,
        contactClicked: false,
        dialogOpened: false,
        overlayPage: false,
        emails: [],
        status: "error",
        error: error.message,
        updatedAt: Date.now(),
      };
      await setCacheStore(cache);
      console.log(`[LinkedIn Processor] Error for ${profileUrl}: ${error.message}`);
      done += 1;
      uncachedProcessedCount += 1;
      safeSendRuntimeMessage({
        type: "PROCESS_PROGRESS",
        item: result,
        done,
        total,
        pending: total - done,
      });
    }
  }

  const stopped = activeRuns.get(tabId)?.cancelled || false;
  activeRuns.delete(tabId);

  if (stopped) {
    safeSendRuntimeMessage({ type: "PROCESS_STOPPED", tabId });
  }

  return { report, stopped };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "STOP_PROCESSING") {
    const tabId = message?.payload?.tabId;
    if (!tabId || !activeRuns.has(tabId)) {
      sendResponse({ ok: true, stopped: false });
      return false;
    }
    const runState = activeRuns.get(tabId);
    runState.cancelled = true;
    activeRuns.set(tabId, runState);
    sendResponse({ ok: true, stopped: true });
    return false;
  }

  if (message?.type === "START_PROCESSING") {
    processUrls(message.payload)
      .then((result) => sendResponse({ ok: true, report: result.report, stopped: result.stopped }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));

    return true;
  }
  return false;
});
