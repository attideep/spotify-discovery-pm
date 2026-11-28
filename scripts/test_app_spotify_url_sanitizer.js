const fs = require("fs");
const vm = require("vm");

const appCode = fs.readFileSync("web/app.js", "utf8")
  + "\n;globalThis.__testGetSpotifyTrackUrl = getSpotifyTrackUrl;";

function makeElement() {
  return {
    classList: {
      add() {},
      remove() {},
      toggle() {},
      contains() {
        return false;
      },
    },
    dataset: {},
    style: { setProperty() {} },
    addEventListener() {},
    querySelectorAll() {
      return [];
    },
    setAttribute() {},
    scrollIntoView() {},
    focus() {},
    value: "",
    innerHTML: "",
    textContent: "",
  };
}

const document = {
  body: { dataset: {}, addEventListener() {} },
  documentElement: { style: { setProperty() {} } },
  getElementById() {
    return makeElement();
  },
  querySelectorAll() {
    return [];
  },
  addEventListener() {},
};

const context = {
  window: {
    API_BASE: "",
    APP_VARIANT: "bridge-only",
    BRIDGE_ENHANCED: true,
    visualViewport: { height: 800, addEventListener() {} },
    addEventListener() {},
    BridgePlayer: { init() {} },
    BridgeExtras: { bindShortcuts() {} },
  },
  document,
  location: { hash: "", search: "", pathname: "/app", origin: "https://example.test" },
  history: { replaceState() {} },
  URL,
  URLSearchParams,
  TextDecoder,
  atob: (value) => Buffer.from(value, "base64").toString("binary"),
  fetch: async () => ({ ok: true, json: async () => ({}) }),
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
};

context.globalThis = context;
context.window.window = context.window;

vm.createContext(context);
vm.runInContext(appCode, context);

const cases = [
  {
    name: "accepts canonical Spotify track URLs",
    input: { spotify_url: "https://open.spotify.com/track/35KiiILklye1JRRctaLUb4?si=abc", track_id: "" },
    expected: "https://open.spotify.com/track/35KiiILklye1JRRctaLUb4?si=abc",
  },
  {
    name: "rejects arbitrary origins and falls back to track id",
    input: { spotify_url: "https://evil.example/login", track_id: "35KiiILklye1JRRctaLUb4" },
    expected: "https://open.spotify.com/track/35KiiILklye1JRRctaLUb4",
  },
  {
    name: "rejects javascript URLs without a track id fallback",
    input: { spotify_url: "javascript:alert(1)", track_id: "" },
    expected: "",
  },
  {
    name: "rejects non-HTTPS Spotify URLs",
    input: { spotify_url: "http://open.spotify.com/track/35KiiILklye1JRRctaLUb4", track_id: "" },
    expected: "",
  },
];

for (const testCase of cases) {
  const actual = context.__testGetSpotifyTrackUrl(testCase.input);
  if (actual !== testCase.expected) {
    throw new Error(`${testCase.name}: expected ${testCase.expected}, got ${actual}`);
  }
}

console.log("app Spotify URL sanitizer tests passed");
