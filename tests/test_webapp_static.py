import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "webapp" / "static"


def test_static_assets_keep_required_ui_contract():
    index = (STATIC / "index.html").read_text(encoding="utf-8")
    styles = (STATIC / "style.css").read_text(encoding="utf-8")
    script = (STATIC / "app.js").read_text(encoding="utf-8")

    for element_id in (
        "page-captcha",
        "page-rules",
        "page-simple",
        "page-success",
        "page-error",
        "bot-avatar",
        "rules-content",
        "btn-captcha",
        "btn-agree",
        "btn-join",
    ):
        assert f'id="{element_id}"' in index

    assert "meta name=\"color-scheme\"" in index
    assert "var(--tg-theme-bg-color" in styles
    assert "--accent: #65B6DD;" in styles
    assert "prefers-color-scheme: dark" in styles
    assert "prefers-reduced-motion: reduce" in styles
    assert "showPage(\"page-success\")" in script


def test_app_javascript_has_valid_syntax():
    subprocess.run(
        ["node", "--check", str(STATIC / "app.js")],
        check=True,
        cwd=ROOT,
    )


def test_rules_gate_requires_bottom_scroll(tmp_path):
    test_script = tmp_path / "rules-gate.cjs"
    test_script.write_text(
        f"""
const assert = require("assert");

class ClassList {{
  constructor(owner) {{
    this.owner = owner;
    this.values = new Set();
  }}

  add(value) {{
    this.values.add(value);
  }}

  remove(value) {{
    this.values.delete(value);
  }}

  contains(value) {{
    return this.values.has(value);
  }}
}}

function makeElement(id, className = "") {{
  const element = {{
    id,
    style: {{}},
    disabled: false,
    textContent: "",
    scrollTop: 0,
    scrollHeight: 0,
    clientHeight: 0,
    listeners: {{}},
    classList: null,
    addEventListener(type, listener) {{
      this.listeners[type] = this.listeners[type] || [];
      this.listeners[type].push(listener);
    }},
    dispatch(type) {{
      for (const listener of this.listeners[type] || []) {{
        listener();
      }}
    }},
  }};

  element.classList = new ClassList(element);

  for (const cls of className.split(/\\s+/).filter(Boolean)) {{
    element.classList.add(cls);
  }}

  return element;
}}

const elements = {{
  "page-captcha": makeElement("page-captcha", "page active"),
  "page-rules": makeElement("page-rules", "page"),
  "page-simple": makeElement("page-simple", "page"),
  "page-success": makeElement("page-success", "page"),
  "page-error": makeElement("page-error", "page"),
  "rules-content": makeElement("rules-content"),
  "btn-captcha": makeElement("btn-captcha"),
  "btn-agree": makeElement("btn-agree"),
  "btn-join": makeElement("btn-join"),
  "scroll-hint": makeElement("scroll-hint"),
  "success-text": makeElement("success-text"),
}};

elements["rules-content"].scrollHeight = 500;
elements["rules-content"].clientHeight = 120;
elements["btn-agree"].disabled = true;

global.window = {{
  __HYPERAUTH_STATE__: {{
    token: "token-123",
    captchaEnabled: false,
    hasRules: true,
    rules: "Rule 1\\nRule 2\\nRule 3",
  }},
}};
global.document = {{
  body: makeElement("body"),
  documentElement: {{ style: {{ setProperty() {{}} }} }},
  getElementById(id) {{
    return elements[id] || null;
  }},
  querySelectorAll(selector) {{
    return selector === ".page"
      ? [
          elements["page-captcha"],
          elements["page-rules"],
          elements["page-simple"],
          elements["page-success"],
          elements["page-error"],
        ]
      : [];
  }},
}};

const app = require({str(STATIC / "app.js")!r});

assert.strictEqual(elements["btn-agree"].disabled, true);
assert.strictEqual(elements["scroll-hint"].style.display, undefined);
assert.strictEqual(elements["rules-content"].listeners.scroll.length, 1);

app.loadRules();
assert.strictEqual(elements["rules-content"].listeners.scroll.length, 1);

elements["rules-content"].scrollTop = 380;
elements["rules-content"].dispatch("scroll");
assert.strictEqual(elements["btn-agree"].disabled, false);
assert.strictEqual(elements["scroll-hint"].style.display, "none");
assert(elements["page-rules"].classList.contains("active"));
""",
        encoding="utf-8",
    )

    subprocess.run(["node", str(test_script)], check=True, cwd=ROOT)


def test_success_flow_is_visible_without_telegram(tmp_path):
    test_script = tmp_path / "success-flow.cjs"
    test_script.write_text(
        f"""
const assert = require("assert");

class ClassList {{
  constructor() {{
    this.values = new Set();
  }}

  add(value) {{
    this.values.add(value);
  }}

  remove(value) {{
    this.values.delete(value);
  }}

  contains(value) {{
    return this.values.has(value);
  }}
}}

function makeElement(id, className = "") {{
  const element = {{
    id,
    style: {{}},
    disabled: false,
    textContent: "",
    listeners: {{}},
    classList: new ClassList(),
    addEventListener(type, listener) {{
      this.listeners[type] = this.listeners[type] || [];
      this.listeners[type].push(listener);
    }},
  }};

  for (const cls of className.split(/\\s+/).filter(Boolean)) {{
    element.classList.add(cls);
  }}

  return element;
}}

const elements = {{
  "page-captcha": makeElement("page-captcha", "page active"),
  "page-rules": makeElement("page-rules", "page"),
  "page-simple": makeElement("page-simple", "page"),
  "page-success": makeElement("page-success", "page"),
  "page-error": makeElement("page-error", "page"),
  "rules-content": makeElement("rules-content"),
  "btn-captcha": makeElement("btn-captcha"),
  "btn-agree": makeElement("btn-agree"),
  "btn-join": makeElement("btn-join"),
  "scroll-hint": makeElement("scroll-hint"),
  "success-text": makeElement("success-text"),
}};

global.window = {{
  __HYPERAUTH_STATE__: {{
    token: "token-123",
    captchaEnabled: false,
    hasRules: false,
  }},
}};
global.document = {{
  body: makeElement("body"),
  documentElement: {{ style: {{ setProperty() {{}} }} }},
  getElementById(id) {{
    return elements[id] || null;
  }},
  querySelectorAll(selector) {{
    return selector === ".page"
      ? [
          elements["page-captcha"],
          elements["page-rules"],
          elements["page-simple"],
          elements["page-success"],
          elements["page-error"],
        ]
      : [];
  }},
}};
global.fetch = async () => ({{
  ok: true,
  headers: {{ get: () => "application/json" }},
  json: async () => ({{ ok: true }}),
}});
global.alert = () => {{}};

(async () => {{
  const app = require({str(STATIC / "app.js")!r});
  await app.sendResult("agree");

  assert(elements["page-success"].classList.contains("active"));
  assert(!elements["page-simple"].classList.contains("active"));
  assert.strictEqual(
    elements["success-text"].textContent,
    "Verification completed successfully."
  );
  assert(!document.body.classList.contains("is-submitting"));
}})().catch((error) => {{
  console.error(error);
  process.exit(1);
}});
""",
        encoding="utf-8",
    )

    subprocess.run(["node", str(test_script)], check=True, cwd=ROOT)


def test_error_surface_shows_backend_422_message(tmp_path):
    test_script = tmp_path / "error-422.cjs"
    test_script.write_text(
        f"""
const assert = require("assert");

const alerts = [];

class ClassList {{
  constructor() {{
    this.values = new Set();
  }}
  add(value) {{
    this.values.add(value);
  }}
  remove(value) {{
    this.values.delete(value);
  }}
  contains(value) {{
    return this.values.has(value);
  }}
}}

function makeElement(id, className = "") {{
  const element = {{
    id,
    style: {{}},
    disabled: false,
    textContent: "",
    listeners: {{}},
    classList: new ClassList(),
    addEventListener(type, listener) {{
      this.listeners[type] = this.listeners[type] || [];
      this.listeners[type].push(listener);
    }},
  }};
  for (const cls of className.split(/\\s+/).filter(Boolean)) {{
    element.classList.add(cls);
  }}
  return element;
}}

const elements = {{
  "page-captcha": makeElement("page-captcha", "page active"),
  "page-rules": makeElement("page-rules", "page"),
  "page-simple": makeElement("page-simple", "page"),
  "page-success": makeElement("page-success", "page"),
  "page-error": makeElement("page-error", "page"),
  "rules-content": makeElement("rules-content"),
  "btn-captcha": makeElement("btn-captcha"),
  "btn-agree": makeElement("btn-agree"),
  "btn-join": makeElement("btn-join"),
  "scroll-hint": makeElement("scroll-hint"),
  "success-text": makeElement("success-text"),
}};

global.window = {{
  Telegram: {{
    WebApp: {{
      initData: "auth_date=1720000000&user=%7B%22id%22%3A42%7D&hash=abc",
      ready() {{}},
      expand() {{}},
      showAlert(message) {{
        alerts.push(message);
      }},
      close() {{}},
      themeParams: {{}},
    }},
  }},
  __HYPERAUTH_STATE__: {{
    token: "token-123",
    captchaEnabled: false,
    hasRules: false,
  }},
}};
global.document = {{
  body: makeElement("body"),
  documentElement: {{ style: {{ setProperty() {{}} }} }},
  getElementById(id) {{
    return elements[id] || null;
  }},
  querySelectorAll(selector) {{
    return selector === ".page"
      ? [
          elements["page-captcha"],
          elements["page-rules"],
          elements["page-simple"],
          elements["page-success"],
          elements["page-error"],
        ]
      : [];
  }},
}};
global.fetch = async () => ({{
  ok: false,
  status: 422,
  headers: {{ get: () => "application/json" }},
  json: async () => ({{ detail: [{{ msg: "Field required" }}] }}),
  text: async () => "",
}});
global.alert = message => alerts.push(message);

(async () => {{
  const app = require({str(STATIC / "app.js")!r});
  await app.sendResult("agree");

  assert.strictEqual(alerts[0], "Verification request is missing Telegram data. Please reopen the Mini App.");
}})().catch((error) => {{
  console.error(error);
  process.exit(1);
}});
""",
        encoding="utf-8",
    )

    subprocess.run(["node", str(test_script)], check=True, cwd=ROOT)


def test_avatar_setup_uses_custom_image_when_available(tmp_path):
    test_script = tmp_path / "avatar-setup.cjs"
    test_script.write_text(
        f"""
const assert = require("assert");

class ClassList {{
  constructor() {{
    this.values = new Set();
  }}
  add(value) {{
    this.values.add(value);
  }}
  remove(value) {{
    this.values.delete(value);
  }}
  contains(value) {{
    return this.values.has(value);
  }}
}}

function makeElement(id, className = "") {{
  const element = {{
    id,
    style: {{}},
    disabled: false,
    textContent: "",
    dataset: {{ fallbackLabel: "HA" }},
    listeners: {{}},
    classList: new ClassList(),
    addEventListener(type, listener) {{
      this.listeners[type] = this.listeners[type] || [];
      this.listeners[type].push(listener);
    }},
  }};
  for (const cls of className.split(/\\s+/).filter(Boolean)) {{
    element.classList.add(cls);
  }}
  return element;
}}

const avatar = makeElement("bot-avatar");
const elements = {{
  "bot-avatar": avatar,
  "page-captcha": makeElement("page-captcha", "page active"),
  "page-rules": makeElement("page-rules", "page"),
  "page-simple": makeElement("page-simple", "page"),
  "page-success": makeElement("page-success", "page"),
  "page-error": makeElement("page-error", "page"),
  "rules-content": makeElement("rules-content"),
  "btn-captcha": makeElement("btn-captcha"),
  "btn-agree": makeElement("btn-agree"),
  "btn-join": makeElement("btn-join"),
  "scroll-hint": makeElement("scroll-hint"),
  "success-text": makeElement("success-text"),
}};

global.window = {{
  __HYPERAUTH_STATE__: {{
    token: "token-123",
    captchaEnabled: false,
    hasRules: false,
    avatarUrl: "/static/avatar.jpg?v=1",
  }},
}};
global.Image = class {{
  set src(value) {{
    this._src = value;
    if (typeof this.onload === "function") {{
      this.onload();
    }}
  }}
}};
global.document = {{
  body: makeElement("body"),
  documentElement: {{ style: {{ setProperty() {{}} }} }},
  getElementById(id) {{
    return elements[id] || null;
  }},
  querySelectorAll(selector) {{
    return selector === ".page"
      ? [
          elements["page-captcha"],
          elements["page-rules"],
          elements["page-simple"],
          elements["page-success"],
          elements["page-error"],
        ]
      : [];
  }},
}};
global.fetch = async () => ({{
  ok: true,
  headers: {{ get: () => "application/json" }},
  json: async () => ({{ ok: true }}),
}});
global.alert = () => {{}};

(async () => {{
  const app = require({str(STATIC / "app.js")!r});
  app.setupAvatar();

  assert.strictEqual(avatar.style.backgroundImage, 'url("/static/avatar.jpg?v=1")');
  assert.strictEqual(avatar.textContent, "");
  assert.strictEqual(avatar.classList.contains("has-image"), true);
}})().catch((error) => {{
  console.error(error);
  process.exit(1);
}});
""",
        encoding="utf-8",
    )

    subprocess.run(["node", str(test_script)], check=True, cwd=ROOT)


def test_verify_request_includes_telegram_init_data(tmp_path):
    test_script = tmp_path / "verify-payload.cjs"
    test_script.write_text(
        f"""
const assert = require("assert");

const fetchCalls = [];

class ClassList {{
  constructor() {{
    this.values = new Set();
  }}
  add(value) {{
    this.values.add(value);
  }}
  remove(value) {{
    this.values.delete(value);
  }}
  contains(value) {{
    return this.values.has(value);
  }}
}}

function makeElement(id, className = "") {{
  const element = {{
    id,
    style: {{}},
    disabled: false,
    textContent: "",
    listeners: {{}},
    classList: new ClassList(),
    addEventListener(type, listener) {{
      this.listeners[type] = this.listeners[type] || [];
      this.listeners[type].push(listener);
    }},
  }};
  for (const cls of className.split(/\\s+/).filter(Boolean)) {{
    element.classList.add(cls);
  }}
  return element;
}}

const elements = {{
  "page-captcha": makeElement("page-captcha", "page active"),
  "page-rules": makeElement("page-rules", "page"),
  "page-simple": makeElement("page-simple", "page"),
  "page-success": makeElement("page-success", "page"),
  "page-error": makeElement("page-error", "page"),
  "rules-content": makeElement("rules-content"),
  "btn-captcha": makeElement("btn-captcha"),
  "btn-agree": makeElement("btn-agree"),
  "btn-join": makeElement("btn-join"),
  "scroll-hint": makeElement("scroll-hint"),
  "success-text": makeElement("success-text"),
}};

global.window = {{
  Telegram: {{
    WebApp: {{
      initData: "auth_date=1720000000&user=%7B%22id%22%3A42%7D&hash=abc",
      ready() {{}},
      expand() {{}},
      showAlert() {{}},
      close() {{}},
      themeParams: {{}},
    }},
  }},
  __HYPERAUTH_STATE__: {{
    token: "token-123",
    captchaEnabled: false,
    hasRules: false,
  }},
}};
global.document = {{
  body: makeElement("body"),
  documentElement: {{ style: {{ setProperty() {{}} }} }},
  getElementById(id) {{
    return elements[id] || null;
  }},
  querySelectorAll(selector) {{
    return selector === ".page"
      ? [
          elements["page-captcha"],
          elements["page-rules"],
          elements["page-simple"],
          elements["page-success"],
          elements["page-error"],
        ]
      : [];
  }},
}};
global.fetch = async (url, options) => {{
  fetchCalls.push([url, options]);
  return {{
    ok: true,
    headers: {{ get: () => "application/json" }},
    json: async () => ({{ ok: true }}),
  }};
}};
global.alert = () => {{}};

(async () => {{
  const app = require({str(STATIC / "app.js")!r});
  await app.sendResult("agree");

  assert.strictEqual(fetchCalls.length, 1);
  const payload = JSON.parse(fetchCalls[0][1].body);
  assert.strictEqual(payload.initData, "auth_date=1720000000&user=%7B%22id%22%3A42%7D&hash=abc");
  assert.strictEqual(payload.action, "agree");
}})().catch((error) => {{
  console.error(error);
  process.exit(1);
}});
""",
        encoding="utf-8",
    )

    subprocess.run(["node", str(test_script)], check=True, cwd=ROOT)
