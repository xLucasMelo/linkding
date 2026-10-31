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
    window: { open: (...args) => opened.push(args) },
    navigator: { clipboard: { writeText: async (text) => copied.push(text) } },
    FormData: class {
      constructor(owner, submitter) {
        this.owner = owner;
        this.submitter = submitter;
      }
    },
    fetch: async (...args) => {
      requests.push(args);
      return { ok: true, text: async () => "https://example.com/copied" };
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
