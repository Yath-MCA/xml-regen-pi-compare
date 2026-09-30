# CONFIG — pi-config schema (Option B)

Canonical separator form (journal split configs + `regen-pi.js`):

```xml
<separator classname="..." value="..." pos="..." contribs="..." when="..."/>
```

`classname` is **required** and must be non-blank.

## Where the config lives in the web app

Configs are loaded by the host into a live DOM Document — do not re-fetch:

```text
LOADING_CONFIG.CLIENT_CONFIG[*]
  FILE_NAME, URL, TYPE ("SPLIT"), IS_LOADED, XML_DOC, ...
```

`RegenPi.fromClientConfig` / `fromXmlDoc` read that Document. The on-disk /
asset XML still matches the schema below (see also
`LWW_MD.separator-classname.xml` in this folder).

## Root

```xml
<pi-config client="LWW" shortcode="MD" dtd="JATS" version="1" status="draft">
  <contrib>
    ...
  </contrib>
</pi-config>
```

| Attribute | Stored on `RegenPiConfig` |
|---|---|
| `client` | `client` |
| `shortcode` | `shortcode` |
| `dtd` | `dtd` |
| `version` | `version` |
| `status` | `status` |

Only the first `<contrib>` child section is read.

## `<elements>` / `<ques>`

Permission flags only — **not** separator sources.

```xml
<elements>
  <degrees allowed="yes"/>
  <prefix allowed="no"/>
</elements>
<ques>
  <aff allowed="yes"/>
</ques>
```

`allowed` is true when `yes` / `true` / `1` (case-insensitive).
Python also honors `alis="affix"`; JS currently stores only `allowed`.

## `<separators>` — Option B

```xml
<separators>
  <separator classname="given-names"      value="&#x00A0;" pos="inner"/>
  <separator classname="between-xrefs"    value=","        pos="after"/>
  <separator classname="between-contribs" value=","        pos="after" contribs="3+"/>
  <separator classname="between-contribs" value="and"      pos="after" contribs="3+" when="last-before"/>
  <separator classname="between-contribs" value="and"      pos="after" contribs="2"  when="last-before"/>
  <separator classname="between-contribs" value=""         pos="after" when="last"/>
</separators>
```

| Attribute | Meaning | Notes |
|---|---|---|
| `classname` | Slot id | **Required** on `<separator>` |
| `value` | PI text after entity decode | `""` if omitted |
| `pos` | Placement hint | Default `"after"`; `given-names` uses `"inner"` |
| `contribs` | `"2"`, `"3+"`, … | Optional; blank = any |
| `when` | `last`, `last-before`, … | Optional; blank = unconditional |

## Legacy tag-as-kind

Accepted for older files; local tag name becomes `classname`. Prefer Option B.

## Focus classnames used by `regen()`

| classname | Expected `pos` | Regen behavior |
|---|---|---|
| `given-names` | `inner` | PI inside given-names |
| `between-xrefs` | `after` | Between xrefs; never after last xref |
| `between-contribs` | `after` | Before `</contrib>`; `when` + `contribs` |

Other classnames can be `select()`-ed but are ignored by `regen()` until extended.

## Working example

[`LWW_MD.separator-classname.xml`](./LWW_MD.separator-classname.xml)
