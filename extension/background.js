const NATIVE_HOST = "com.vvitovec.codex_work_gate";
const STATUS_URL = "http://127.0.0.1:18732/status";
const DEFAULT_BLOCKED_HOSTS = [
  "youtube.com",
  "youtu.be",
  "netflix.com",
  "reddit.com",
  "x.com",
  "twitter.com",
  "instagram.com",
  "tiktok.com",
  "twitch.tv"
];
const RULE_ID_BASE = 1000;
const FALLBACK_POLL_MS = 3000;

let pollTimer = null;
let lastRuleIds = [];
let lastStatus = {
  allowed: true,
  state: "starting",
  reason: "waiting_for_first_status",
  checkedAt: null,
  blockedHosts: DEFAULT_BLOCKED_HOSTS
};

function normalizeHosts(hosts) {
  if (!Array.isArray(hosts)) {
    return DEFAULT_BLOCKED_HOSTS;
  }
  return hosts
    .filter((host) => typeof host === "string" && host.trim().length > 0)
    .map((host) => host.trim().toLowerCase().replace(/^\*\./, ""));
}

function buildRule(host, index) {
  return {
    id: RULE_ID_BASE + index,
    priority: 1,
    action: {
      type: "redirect",
      redirect: {
        extensionPath: "/blocked.html"
      }
    },
    condition: {
      urlFilter: `||${host}^`,
      resourceTypes: ["main_frame"]
    }
  };
}

function hostMatches(hostname, blockedHost) {
  return hostname === blockedHost || hostname.endsWith(`.${blockedHost}`);
}

function isBlockedUrl(url, hosts) {
  try {
    const parsed = new URL(url);
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return false;
    }
    const hostname = parsed.hostname.toLowerCase();
    return normalizeHosts(hosts).some((host) => hostMatches(hostname, host));
  } catch (_error) {
    return false;
  }
}

async function redirectOpenBlockedTabs(hosts) {
  const tabs = await chrome.tabs.query({});
  const blockedUrl = chrome.runtime.getURL("blocked.html");
  await Promise.all(
    tabs
      .filter((tab) => tab.id && tab.url && isBlockedUrl(tab.url, hosts))
      .map((tab) => chrome.tabs.update(tab.id, { url: blockedUrl }).catch(() => undefined))
  );
}

async function queryHttpGate() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1000);
  try {
    const response = await fetch(STATUS_URL, {
      cache: "no-store",
      signal: controller.signal
    });
    if (!response.ok) {
      throw new Error(`http_${response.status}`);
    }
    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

function queryNativeGate() {
  return new Promise((resolve) => {
    chrome.runtime.sendNativeMessage(NATIVE_HOST, { action: "status" }, (response) => {
      if (chrome.runtime.lastError) {
        resolve({
          allowed: false,
          state: "unknown",
          reason: `native_host_error:${chrome.runtime.lastError.message}`,
          checkedAt: new Date().toISOString(),
          blockedHosts: DEFAULT_BLOCKED_HOSTS,
          pollIntervalMs: FALLBACK_POLL_MS
        });
        return;
      }
      resolve(response || {
        allowed: false,
        state: "unknown",
        reason: "empty_native_response",
        checkedAt: new Date().toISOString(),
        blockedHosts: DEFAULT_BLOCKED_HOSTS,
        pollIntervalMs: FALLBACK_POLL_MS
      });
    });
  });
}

async function queryGate() {
  try {
    return await queryHttpGate();
  } catch (error) {
    const nativeStatus = await queryNativeGate();
    if (nativeStatus.reason?.startsWith("native_host_error")) {
      nativeStatus.reason = `http_error:${error.message};${nativeStatus.reason}`;
    }
    return nativeStatus;
  }
}

async function setBlocked(blocked, hosts) {
  const removeRuleIds = lastRuleIds.length > 0
    ? lastRuleIds
    : Array.from({ length: DEFAULT_BLOCKED_HOSTS.length + 50 }, (_, index) => RULE_ID_BASE + index);
  const addRules = blocked ? normalizeHosts(hosts).map(buildRule) : [];
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds,
    addRules
  });
  lastRuleIds = addRules.map((rule) => rule.id);
}

async function applyStatus(status) {
  lastStatus = status;
  await chrome.storage.local.set({ gateStatus: status });
  await setBlocked(!status.allowed, status.blockedHosts);
  if (!status.allowed) {
    await redirectOpenBlockedTabs(status.blockedHosts);
  }
}

async function refreshGate() {
  const status = await queryGate();
  await applyStatus(status);
  const pollMs = Number(status.pollIntervalMs) > 0 ? Number(status.pollIntervalMs) : FALLBACK_POLL_MS;
  schedulePoll(pollMs);
}

function schedulePoll(delayMs = FALLBACK_POLL_MS) {
  if (pollTimer) {
    clearTimeout(pollTimer);
  }
  pollTimer = setTimeout(refreshGate, delayMs);
}

chrome.runtime.onInstalled.addListener(() => {
  refreshGate();
});

chrome.runtime.onStartup.addListener(() => {
  refreshGate();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.action !== "refreshGate") {
    return false;
  }
  refreshGate()
    .then(() => chrome.storage.local.get("gateStatus"))
    .then(({ gateStatus }) => sendResponse(gateStatus))
    .catch((error) => sendResponse({
      allowed: false,
      state: "unknown",
      reason: `refresh_error:${error.message}`,
      checkedAt: new Date().toISOString()
    }));
  return true;
});

refreshGate();
