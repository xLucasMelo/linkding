const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

// Load the real component. Only its browser boundary and base element are fakes;
// no production source is rewritten and no network or external tabs are used.
async function setup(action, bookmarks = []) {
  const opened = [];
  const copied = [];
  const requests = [];
  const confirmCalls = [];
  const alerts = [];
  const failures = { status: 200, fetch: null, read: null };
  let confirmResult = true;
  const confirmation = new Map([["data-confirm", ""]]);
  const acrossClasses = new Set();
  const acrossCheckbox = { checked: true };
  const form = { action: "/bookmarks/action" };
  let Component;
  const context = vm.createContext({
    customElements: {
      define(name, value) {
        assert.equal(name, "ld-bookmark-page");
        Component = value;
      },
    },
    window: {
      open: (...args) => opened.push(args),
      alert: (message) => alerts.push(message),
      confirm: (msg) => {
        confirmCalls.push(msg);
        return confirmResult;
      },
    },
    navigator: { clipboard: { writeText: async (text) => copied.push(text) } },
    FormData: class {
      constructor(owner, submitter) {
        this.owner = owner;
        this.submitter = submitter;
      }
    },
    fetch: async (...args) => {
      requests.push(args);
      if (failures.fetch) throw failures.fetch;
      return {
        ok: failures.status >= 200 && failures.status < 300,
        status: failures.status,
        text: async () => {
          if (failures.read) throw failures.read;
          return "https://example.com/copied";
        },
      };
    },
  });
  const filename = path.join(__dirname, "../components/bookmark-page.js");
  const module = new vm.SourceTextModule(readFileSync(filename, "utf8"), {
    context,
    identifier: "bookmarks/frontend/components/bookmark-page.js",
  });
  await module.link((specifier) => {
    assert.equal(specifier, "../utils/element.js");
    return new vm.SyntheticModule(
      ["HeadlessElement"],
      function () {
        this.setExport("HeadlessElement", class {});
      },
      { context },
    );
  });
  await module.evaluate();
  const element = new Component();
  element.dataset = {};
  element.actionSelect = { value: action };
  element.allCheckbox = { checked: true };
  element.selectAcross = {
    classList: {
      add: (value) => acrossClasses.add(value),
      remove: (value) => acrossClasses.delete(value),
    },
    querySelector: () => acrossCheckbox,
  };
  element.executeButton = {
    removeAttribute: (name) => confirmation.delete(name),
    setAttribute: (name, value) => confirmation.set(name, value),
    closest: (selector) => {
      assert.equal(selector, "form");
      return form;
    },
  };
  element.bookmarkCheckboxes = bookmarks.map(({ checked, url }) => ({
    checked,
    closest: (selector) => {
      assert.equal(selector, "li");
      return {
        querySelector: (anchorSelector) => {
          assert.equal(anchorSelector, ".title > a");
          return url ? { href: url } : null;
        },
      };
    },
  }));
  const events = { prevented: 0, stopped: 0 };
  const event = {
    preventDefault: () => events.prevented++,
    stopPropagation: () => events.stopped++,
  };
  return {
    element,
    event,
    events,
    opened,
    copied,
    requests,
    confirmCalls,
    alerts,
    failures,
    setConfirmResult: (v) => {
      confirmResult = v;
    },
    confirmation,
    acrossCheckbox,
    acrossClasses,
    form,
  };
}

test("regression: copying URLs still posts the form and writes the clipboard", async () => {
  const f = await setup("bulk_copy_urls");
  f.element.onBulkActionChange();
  await f.element.onExecuteBulkAction(f.event);
  assert.equal(f.confirmation.has("data-confirm"), false);
  assert.equal(f.requests.length, 1);
  const [url, options] = f.requests[0];
  assert.equal(url, f.form.action);
  assert.equal(options.method, "POST");
  assert.equal(options.body.owner, f.form);
  assert.equal(options.body.submitter, f.element.executeButton);
  assert.deepEqual(f.copied, ["https://example.com/copied"]);
  assert.deepEqual(f.opened, []);
  assert.deepEqual(f.events, { prevented: 1, stopped: 1 });
});

test("regression: delete retains confirmation and its normal form submission", async () => {
  const f = await setup("bulk_delete");
  f.element.onBulkActionChange();
  await f.element.onExecuteBulkAction(f.event);
  assert.equal(f.confirmation.has("data-confirm"), true);
  assert.deepEqual(f.events, { prevented: 0, stopped: 0 });
  assert.deepEqual(f.requests, []);
  assert.deepEqual(f.opened, []);
  assert.deepEqual(f.copied, []);
});

test("cycle 9: opens one selected bookmark synchronously without posting or copying", async () => {
  const url = "https://example.com/selected?x=1#section";
  const f = await setup("bulk_open_urls", [
    { checked: false, url: "https://example.com/not-selected" },
    { checked: true, url },
  ]);
  f.element.onBulkActionChange();
  const pending = f.element.onExecuteBulkAction(f.event);
  // Must happen in the click handler, before any asynchronous network work.
  assert.deepEqual(f.opened, [[url, "_blank", "noopener,noreferrer"]]);
  await pending;
  assert.deepEqual(f.events, { prevented: 1, stopped: 1 });
  assert.deepEqual(f.requests, []);
  assert.deepEqual(f.copied, []);
  assert.equal(f.confirmation.has("data-confirm"), false);
  assert.equal(f.acrossCheckbox.checked, false);
  assert.equal(f.acrossClasses.has("d-none"), true);
  // Switching back preserves cross-page selection for the existing copy action.
  f.element.actionSelect.value = "bulk_copy_urls";
  f.element.onBulkActionChange();
  assert.equal(f.acrossClasses.has("d-none"), false);
});

test("cycle 10: opens all selected URLs in page order and skips unchecked or missing links", async () => {
  const first = "https://example.com/first?a=1&b=2#fragment";
  const second = "https://example.org/second";
  const f = await setup("bulk_open_urls", [
    { checked: false, url: "https://example.com/unchecked" },
    { checked: true, url: first },
    { checked: true, url: null },
    { checked: true, url: second },
  ]);
  f.element.onBulkActionChange();
  const pending = f.element.onExecuteBulkAction(f.event);
  assert.deepEqual(f.opened, [
    [first, "_blank", "noopener,noreferrer"],
    [second, "_blank", "noopener,noreferrer"],
  ]);
  await pending;
  assert.deepEqual(f.events, { prevented: 1, stopped: 1 });
  assert.deepEqual(f.requests, []);
  assert.deepEqual(f.copied, []);
});

test("cycle 10: an empty selection opens no tabs and does not submit the form", async () => {
  const f = await setup("bulk_open_urls", [
    { checked: false, url: "https://example.com/unchecked" },
  ]);
  f.element.onBulkActionChange();
  await f.element.onExecuteBulkAction(f.event);
  assert.deepEqual(f.opened, []);
  assert.deepEqual(f.requests, []);
  assert.deepEqual(f.copied, []);
  assert.deepEqual(f.events, { prevented: 1, stopped: 1 });
});

test("cycle 11: confirms before opening multiple URLs and shows count in message", async () => {
  const urls = [
    "https://example.com/a",
    "https://example.com/b",
    "https://example.com/c",
  ];
  const f = await setup(
    "bulk_open_urls",
    urls.map((url) => ({ checked: true, url })),
  );
  f.element.onBulkActionChange();
  f.setConfirmResult(true);
  await f.element.onExecuteBulkAction(f.event);
  // Must have called window.confirm exactly once with the URL count
  assert.equal(f.confirmCalls.length, 1);
  assert.ok(
    f.confirmCalls[0].includes("3"),
    `confirm message should contain the count 3, got: "${f.confirmCalls[0]}"`,
  );
  // After confirming, all tabs must be opened
  assert.equal(f.opened.length, 3);
  assert.deepEqual(f.opened[0], [urls[0], "_blank", "noopener,noreferrer"]);
  assert.deepEqual(f.opened[1], [urls[1], "_blank", "noopener,noreferrer"]);
  assert.deepEqual(f.opened[2], [urls[2], "_blank", "noopener,noreferrer"]);
  assert.deepEqual(f.events, { prevented: 1, stopped: 1 });
  assert.deepEqual(f.requests, []);
  assert.deepEqual(f.copied, []);
});

test("cycle 12: cancelling the confirmation opens no tabs and returns zero", async () => {
  const f = await setup("bulk_open_urls", [
    { checked: true, url: "https://example.com/a" },
    { checked: true, url: "https://example.com/b" },
    { checked: true, url: "https://example.com/c" },
  ]);
  f.element.onBulkActionChange();
  f.setConfirmResult(false);
  await f.element.onExecuteBulkAction(f.event);
  // Confirm was called but user declined
  assert.equal(f.confirmCalls.length, 1);
  assert.ok(f.confirmCalls[0].includes("3"));
  // No tabs should have been opened
  assert.deepEqual(f.opened, []);
  // openSelectedUrls must return the count of tabs actually opened
  const count = f.element.openSelectedUrls();
  assert.equal(count, 0);
  assert.deepEqual(f.events, { prevented: 1, stopped: 1 });
  assert.deepEqual(f.requests, []);
  assert.deepEqual(f.copied, []);
});

test("cycle 12: a single selected URL opens directly without confirmation and returns 1", async () => {
  const url = "https://example.com/single";
  const f = await setup("bulk_open_urls", [
    { checked: true, url },
    { checked: false, url: "https://example.com/unchecked" },
  ]);
  f.element.onBulkActionChange();
  // Must return the count of opened tabs
  const count = f.element.openSelectedUrls();
  assert.equal(count, 1);
  // No confirmation dialog should appear for a single URL
  assert.equal(f.confirmCalls.length, 0);
  // The single URL must still be opened
  assert.equal(f.opened.length, 1);
  assert.deepEqual(f.opened[0], [url, "_blank", "noopener,noreferrer"]);
});

test("supplemental cycle 7: an HTTP error notifies the user without copying the error body", async () => {
  const f = await setup("bulk_copy_urls");
  f.failures.status = 500;
  await f.element.onExecuteBulkAction(f.event);
  assert.deepEqual(f.alerts, ["Could not load URLs. Please try again."]);
  assert.deepEqual(f.copied, []);
  assert.deepEqual(f.opened, []);
  assert.equal(f.requests.length, 1);
  assert.deepEqual(f.events, { prevented: 1, stopped: 1 });
});

test("supplemental cycle 7: a network rejection is handled and a later retry can copy", async () => {
  const f = await setup("bulk_copy_urls");
  f.failures.fetch = new Error("Network unavailable");
  await f.element.onExecuteBulkAction(f.event);
  assert.deepEqual(f.alerts, ["Could not load URLs. Please try again."]);
  assert.deepEqual(f.copied, []);
  f.failures.fetch = null;
  await f.element.onExecuteBulkAction(f.event);
  assert.deepEqual(f.copied, ["https://example.com/copied"]);
  assert.equal(f.alerts.length, 1);
  assert.equal(f.requests.length, 2);
  assert.deepEqual(f.opened, []);
});

test("supplemental cycle 7: a failed response body read does not reach the clipboard", async () => {
  const f = await setup("bulk_copy_urls");
  f.failures.read = new Error("Response interrupted");
  await f.element.onExecuteBulkAction(f.event);
  assert.deepEqual(f.alerts, ["Could not load URLs. Please try again."]);
  assert.deepEqual(f.copied, []);
  assert.deepEqual(f.opened, []);
});
