import { beforeAll, afterEach, describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  RegenPi,
  RegenPiError,
  RegenPiSelector,
  stripPistart,
  makePistart,
  formatPiAttrValue,
  roleOf,
  pickBetweenContribsRule,
} from "../regen-pi.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SAMPLE_XML_PATH = join(__dirname, "..", "LWW_MD.separator-classname.xml");

function sampleXmlText() {
  return readFileSync(SAMPLE_XML_PATH, "utf8");
}

function sampleDoc() {
  return new DOMParser().parseFromString(sampleXmlText(), "text/xml");
}

function clearLoadingConfig() {
  try {
    delete globalThis.LOADING_CONFIG;
  } catch (_) {
    globalThis.LOADING_CONFIG = undefined;
  }
}

beforeAll(() => {
  expect(typeof DOMParser).toBe("function");
});

afterEach(() => {
  clearLoadingConfig();
});

describe("Option B sample parse (S1 / S1b)", () => {
  it("fromXml loads Option B sample; select(given-names) length >= 1", () => {
    const engine = RegenPi.fromXml(sampleXmlText());
    const gn = engine.select("given-names");
    expect(gn.length).toBeGreaterThanOrEqual(1);
    expect(gn[0].value).toBe("\u00a0");
    expect(gn[0].pos).toBe("inner");
    expect(engine.config.client).toBe("LWW");
    expect(engine.config.shortcode).toBe("MD");
  });

  it("fromXmlDoc reads live Document without second string parse path differences", () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    expect(engine.select("given-names")[0].value).toBe("\u00a0");
    expect(engine.select("between-xrefs").length).toBe(1);
    expect(engine.select("between-contribs").length).toBe(4);
  });
});

describe("CLIENT_CONFIG / fromClientConfig (S1c + safety)", () => {
  it("fromClientConfig with IS_LOADED + XML_DOC builds engine", () => {
    const engine = RegenPi.fromClientConfig({
      FILE_NAME: "MD.xml",
      IS_LOADED: true,
      XML_DOC: sampleDoc(),
    });
    expect(engine.select("between-contribs").length).toBe(4);
    expect(engine.select("between-xrefs")[0].value).toBe(",");
  });

  it("mocks LOADING_CONFIG.CLIENT_CONFIG map + fileName selector", () => {
    globalThis.LOADING_CONFIG = {
      CLIENT_CONFIG: {
        md: {
          FILE_NAME: "MD.xml",
          IS_LOADED: true,
          TYPE: "SPLIT",
          URL: "assets/config/journals/lww/split/MD.xml",
          XML_DOC: sampleDoc(),
        },
        other: {
          FILE_NAME: "XX.xml",
          IS_LOADED: true,
          XML_DOC: sampleDoc(),
        },
      },
    };
    const engine = RegenPi.fromClientConfig(null, { fileName: "MD.xml" });
    expect(engine.select("given-names")[0].value).toBe("\u00a0");
  });

  it("throws when LOADING_CONFIG global is missing", () => {
    clearLoadingConfig();
    expect(() => RegenPi.fromClientConfig()).toThrow(RegenPiError);
    expect(() => RegenPi.fromClientConfig()).toThrow(/LOADING_CONFIG/);
  });

  it("throws when IS_LOADED is false", () => {
    expect(() =>
      RegenPi.fromClientConfig({
        FILE_NAME: "MD.xml",
        IS_LOADED: false,
        XML_DOC: sampleDoc(),
      })
    ).toThrow(RegenPiError);
    expect(() =>
      RegenPi.fromClientConfig({
        FILE_NAME: "MD.xml",
        IS_LOADED: false,
        XML_DOC: sampleDoc(),
      })
    ).toThrow(/IS_LOADED/);
  });

  it("throws when XML_DOC is null", () => {
    expect(() =>
      RegenPi.fromClientConfig({
        FILE_NAME: "MD.xml",
        IS_LOADED: true,
        XML_DOC: null,
      })
    ).toThrow(RegenPiError);
    expect(() =>
      RegenPi.fromClientConfig({
        FILE_NAME: "MD.xml",
        IS_LOADED: true,
        XML_DOC: null,
      })
    ).toThrow(/XML_DOC/);
  });

  it("throws for multi-entry map without fileName/url/key", () => {
    expect(() =>
      RegenPi.fromClientConfig({
        a: { FILE_NAME: "A.xml", IS_LOADED: true, XML_DOC: sampleDoc() },
        b: { FILE_NAME: "B.xml", IS_LOADED: true, XML_DOC: sampleDoc() },
      })
    ).toThrow(RegenPiError);
  });
});

describe("blank classname rejects", () => {
  it("fromXml blank classname on separator throws RegenPiError", () => {
    expect(() =>
      RegenPi.fromXml(
        '<pi-config><contrib><separators><separator value=","/></separators></contrib></pi-config>'
      )
    ).toThrow(RegenPiError);
  });

  it("RegenPiSelector empty / whitespace-only throws", () => {
    expect(() => new RegenPiSelector("")).toThrow(RegenPiError);
    expect(() => new RegenPiSelector("   ")).toThrow(RegenPiError);
  });

  it("config.select('') throws", () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    expect(() => engine.select("")).toThrow(RegenPiError);
  });
});

describe("given-names regen (S2)", () => {
  it('pos="inner" inserts PI before </given-names>; empty given-names wraps PI', () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    const out = engine.regen(
      "<contrib-group>" +
        "<contrib><name><surname>A</surname><given-names>Ann</given-names></name></contrib>" +
        "<contrib><name><surname>B</surname><given-names/></name></contrib>" +
        "</contrib-group>"
    );
    const pi = makePistart("\u00a0");
    expect(out).toContain("<given-names>Ann" + pi + "</given-names>");
    expect(out).toContain("<given-names>" + pi + "</given-names>");
  });
});

describe("between-xrefs regen (S3 / S4)", () => {
  it("inserts PI after each xref except the last when >= 2", () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    const block =
      "<contrib>" +
      '<xref ref-type="aff" rid="a1"/>' +
      '<xref ref-type="aff" rid="a2"/>' +
      '<xref ref-type="aff" rid="a3"/>' +
      "</contrib>";
    const out = engine.regen(block);
    const pi = makePistart(",");
    expect(out).toContain(
      '<xref ref-type="aff" rid="a1"/>' + pi + '<xref ref-type="aff" rid="a2"/>'
    );
    expect(out).toContain(
      '<xref ref-type="aff" rid="a2"/>' + pi + '<xref ref-type="aff" rid="a3"/>'
    );
    // no comma PI after the last xref
    expect(out).not.toContain('<xref ref-type="aff" rid="a3"/>' + pi);
  });

  it("does not insert xref PI when 0-1 xref", () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    const one = '<contrib><xref ref-type="aff" rid="a1"/></contrib>';
    const zero = "<contrib><name><surname>X</surname></name></contrib>";
    const outOne = engine.regen(one);
    const outZero = engine.regen(zero);
    const xrefPi = makePistart(",");
    expect(outOne).not.toContain(xrefPi);
    expect(outZero).not.toContain(xrefPi);
  });
});

describe("between-contribs regen (S5 / S6 / S7)", () => {
  function threeContribs() {
    return (
      "<contrib-group>" +
      "<contrib><name><surname>One</surname></name></contrib>" +
      "<contrib><name><surname>Two</surname></name></contrib>" +
      "<contrib><name><surname>Three</surname></name></contrib>" +
      "</contrib-group>"
    );
  }

  function twoContribs() {
    return (
      "<contrib-group>" +
      "<contrib><name><surname>One</surname></name></contrib>" +
      "<contrib><name><surname>Two</surname></name></contrib>" +
      "</contrib-group>"
    );
  }

  it('contribs="3+" default comma on non-last matching roles (S5)', () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    const out = engine.regen(threeContribs());
    const comma = makePistart(",");
    const andPi = makePistart("and");
    const empty = makePistart("");
    // first (other/first): unconditional "," with contribs 3+
    expect(out).toContain("</name>" + comma + "</contrib>");
    // last-before: "and"
    expect(out).toContain(andPi + "</contrib>");
    // last: empty when="last" rule
    expect(out).toContain(empty + "</contrib>");
  });

  it('when="last-before" + contribs 3+ / 2 (S6)', () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    const out3 = engine.regen(threeContribs());
    const out2 = engine.regen(twoContribs());
    const andPi = makePistart("and");
    // 3 contribs: second-to-last gets and via contribs="3+"
    expect(out3.match(new RegExp(andPi.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g"))).toHaveLength(1);
    // 2 contribs: last-before gets and via contribs="2"
    expect(out2).toContain(andPi);
  });

  it('when="last" emits only when explicit last rule matches (S7)', () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    const out = engine.regen(threeContribs());
    // sample has when="last" value=""
    expect(out).toMatch(/\?><\/contrib>\s*<\/contrib-group>/);
    expect(out).toContain(makePistart(""));
  });

  it("last contrib silent when no when=last rule", () => {
    const xml =
      '<pi-config><contrib><separators>' +
      '<separator classname="between-contribs" value="," pos="after" contribs="3+"/>' +
      '<separator classname="between-contribs" value="and" pos="after" contribs="3+" when="last-before"/>' +
      "</separators></contrib></pi-config>";
    const engine = RegenPi.fromXml(xml);
    const out = engine.regen(threeContribs());
    // last block should have no pistart before </contrib>
    const lastBlock = out.match(/<contrib>[\s\S]*?<\/contrib>/g).pop();
    expect(lastBlock).not.toMatch(/<\?pistart/);
  });
});

describe("stripPistart then regen (S8)", () => {
  it("stripPistart removes only pistart PIs; regen restores separators", () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    const dirty =
      "<contrib>" +
      "<name><given-names>Ann<?pistart xml:space=\"&#x00A0;\"?></given-names></name>" +
      '<xref ref-type="aff" rid="a1"/><?pistart xml:space=","?>' +
      '<xref ref-type="aff" rid="a2"/>' +
      "</contrib>";
    const stripped = stripPistart(dirty);
    expect(stripped).not.toMatch(/<\?pistart/);
    const out = engine.regen(stripped);
    expect(out).toContain(makePistart("\u00a0"));
    expect(out).toContain(makePistart(","));
  });
});

describe("NBSP value (S9)", () => {
  it("unescapes &#x00A0; and makePistart emits &#x00A0;", () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    expect(engine.select("given-names")[0].value).toBe("\u00a0");
    expect(formatPiAttrValue("\u00a0")).toBe("&#x00A0;");
    expect(makePistart("\u00a0")).toBe('<?pistart xml:space="&#x00A0;"?>');
    expect(RegenPi.makePistart("\u00a0")).toBe('<?pistart xml:space="&#x00A0;"?>');
  });
});

describe("legacy tag-as-kind parse (S10)", () => {
  it("legacy <given-names .../> under separators maps classname", () => {
    const xml =
      '<pi-config client="X" shortcode="Y">' +
      "<contrib><separators>" +
      '<given-names value="&#x00A0;" pos="inner"/>' +
      '<between-xrefs value="," pos="after"/>' +
      "</separators></contrib></pi-config>";
    const engine = RegenPi.fromXml(xml);
    const gn = engine.select("given-names");
    expect(gn.length).toBe(1);
    expect(gn[0].classname).toBe("given-names");
    expect(gn[0].value).toBe("\u00a0");
    expect(engine.select("between-xrefs")[0].value).toBe(",");
  });
});

describe("helpers: roleOf / pickBetweenContribsRule", () => {
  it("roleOf mirrors first / last-before / last / other", () => {
    expect(roleOf(0, 3)).toBe("first");
    expect(roleOf(1, 3)).toBe("last-before");
    expect(roleOf(2, 3)).toBe("last");
    expect(roleOf(1, 4)).toBe("other");
  });

  it("pickBetweenContribsRule respects when + contribs", () => {
    const engine = RegenPi.fromXmlDoc(sampleDoc());
    const rules = engine.select("between-contribs");
    expect(pickBetweenContribsRule(rules, 0, 3).value).toBe(",");
    expect(pickBetweenContribsRule(rules, 1, 3).value).toBe("and");
    expect(pickBetweenContribsRule(rules, 2, 3).value).toBe("");
    // n=2: index 0 is last-before -> contribs="2" and-rule; index 1 is last
    expect(roleOf(0, 2)).toBe("last-before");
    expect(pickBetweenContribsRule(rules, 0, 2).value).toBe("and");
    expect(pickBetweenContribsRule(rules, 1, 2).value).toBe("");
    // n=1: sole contrib is last; only when="last" matches (empty value)
    expect(roleOf(0, 1)).toBe("last");
    expect(pickBetweenContribsRule(rules, 0, 1).value).toBe("");
  });
});

describe("invalid XML / missing DOMParser edges", () => {
  it("invalid XML / no pi-config throws", () => {
    expect(() => RegenPi.fromXml("<not-pi/>")).toThrow(RegenPiError);
  });
});