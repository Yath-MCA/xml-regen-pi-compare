from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import regen_compare_v1 as regen


def group(surname_pi=", ", end_pi="; ", count=3):
    contribs = []
    for i in range(count):
        contribs.append(
            f'<contrib><name><surname>S{i}<?pistart xml:space="{surname_pi}"?>'
            f'</surname><given-names>G{i}<?pistart xml:space=" "?>'
            f'</given-names></name><?pistart xml:space="{end_pi}"?></contrib>'
        )
    return "<contrib-group>" + "".join(contribs) + "</contrib-group>"


class RegenCompareV2Tests(unittest.TestCase):
    def classification_cfg(self):
        return {
            "sep": {
                "surname": [{"value": ",\xa0", "pos": "inner", "when": ""}],
                "given-names": [{"value": "\xa0", "pos": "inner", "when": ""}],
                "affixes": [],
                "between-xrefs": ",",
                "between-contribs": {"default": "; ", "when": {"last-before": ", "}},
            }
        }

    def compared_row(self, folder: Path, original: str, regenerated: str, docid="doc-1"):
        result = regen.compare_doc(regen.ec.parse_group(original), regen.ec.parse_group(regenerated))
        result.update(
            {
                "docid": docid,
                "file_id": "FILE-1",
                "error": None,
                "folder": folder,
                "orig_text": original,
                "regen_text": regenerated,
            }
        )
        return result

    def test_compare_doc_keeps_exact_slot_key_and_role_percentages(self):
        original = group()
        regenerated = group(surname_pi=" | ")

        result = regen.compare_doc(regen.ec.parse_group(original), regen.ec.parse_group(regenerated))

        self.assertEqual(result["mismatches"][0]["key"], "surname")
        self.assertEqual(len(result["per_contrib"]), 3)
        self.assertEqual(result["per_contrib"][0]["role"], "first")
        self.assertEqual(result["per_contrib"][1]["role"], "last-before")
        self.assertEqual(result["per_contrib"][2]["role"], "last")
        self.assertAlmostEqual(result["per_contrib"][0]["pct"], 200 / 3)

    def test_space_and_nbsp_stay_strict_but_are_categorized(self):
        original = group(surname_pi=", ", count=1)
        regenerated = group(surname_pi=",\xa0", count=1)

        result = regen.compare_doc(
            regen.ec.parse_group(original), regen.ec.parse_group(regenerated), self.classification_cfg()
        )

        self.assertLess(result["pct"], 100)
        self.assertIn("space-nbsp", result["categories"])

    def test_unconfigured_and_other_value_difference_can_overlap(self):
        original = group(surname_pi=" | ", count=1)
        regenerated = group(surname_pi=",\xa0", count=1)

        result = regen.compare_doc(
            regen.ec.parse_group(original), regen.ec.parse_group(regenerated), self.classification_cfg()
        )

        self.assertIn("original-value-not-configured", result["categories"])
        self.assertIn("other-value-difference", result["categories"])

    def test_missing_wrong_position_and_extra_are_categorized(self):
        original = ('<contrib-group><contrib><name><surname>S</surname>'
                    '<given-names>G<?pistart xml:space=","?></given-names></name></contrib></contrib-group>')
        regenerated = ('<contrib-group><contrib><name><surname>S<?pistart xml:space=","?></surname>'
                       '<given-names>G</given-names></name></contrib></contrib-group>')
        cfg = self.classification_cfg()
        cfg["sep"]["surname"] = [{"value": ",", "pos": "inner", "when": ""}]

        result = regen.compare_doc(regen.ec.parse_group(original), regen.ec.parse_group(regenerated), cfg)
        surname = next(m for m in result["mismatches"] if m["slot"] == "surname")
        given = next(m for m in result["mismatches"] if m["slot"] == "given-names")

        self.assertIn("missing-at-configured-position", surname["categories"])
        self.assertIn("original-pi-different-position", surname["categories"])
        self.assertIn("extra-in-original", given["categories"])

    def test_summary_v7_has_kpis_category_chart_and_filter_metadata(self):
        with TemporaryDirectory() as tmp:
            harness = Path(tmp)
            first = self.compared_row(harness / "doc-1", group(), group(surname_pi=" | "), "doc-1")
            second = self.compared_row(harness / "doc-2", group(), group(surname_pi=" | "), "doc-2")
            for row in (first, second):
                row["folder"].mkdir()
                row["categories"] = {"space-nbsp", "other-value-difference"}
                for mismatch in row["mismatches"]:
                    mismatch["categories"] = {"space-nbsp", "other-value-difference"}

            out = regen.write_summary(
                "LWW", "MD", [first, second], [], harness, Path("config.xml"), config_version="1"
            )
            html = out.read_text(encoding="utf-8")

            self.assertTrue(out.name.endswith("_regen_compare_v7.html"))
            self.assertIn('<div class="kpi-value">2</div>', html)
            self.assertIn("Overall match", html)
            self.assertIn("Not matched", html)
            self.assertIn('data-category="space-nbsp"', html)
            self.assertIn("Space vs NBSP", html)
            self.assertIn("2 files", html)
            self.assertIn("100.0% of unmatched", html)
            self.assertIn('data-categories="other-value-difference space-nbsp"', html)
            self.assertIn("activateUnmatched", html)
            self.assertIn("activeCategory", html)
            self.assertIn("setAttribute('aria-pressed'", html)
            self.assertIn('id="clearCategoryFilter"', html)

    def test_failed_file_is_charted_as_processing_error(self):
        with TemporaryDirectory() as tmp:
            harness = Path(tmp)
            failed = {"docid": "bad-doc", "file_id": "BAD-1", "error": "parse error"}

            out = regen.write_summary("LWW", "MD", [failed], [], harness, Path("config.xml"))
            html = out.read_text(encoding="utf-8")

            self.assertIn("Processing error", html)
            self.assertIn('data-categories="processing-error"', html)
            self.assertIn('<span class="cause-tag">Processing error</span>', html)

    def test_empty_unmatched_chart_has_zero_state(self):
        with TemporaryDirectory() as tmp:
            harness = Path(tmp)
            row = self.compared_row(harness / "doc-1", group(), group())
            row["folder"].mkdir()

            out = regen.write_summary("LWW", "MD", [row], [], harness, Path("config.xml"))
            html = out.read_text(encoding="utf-8")

            self.assertIn("No mismatches to categorize.", html)

    def test_summary_v7_has_versions_tabs_and_collapsible_tables(self):
        with TemporaryDirectory() as tmp:
            harness = Path(tmp)
            row = self.compared_row(harness / "doc-1", group(), group(surname_pi=" | "))
            row["folder"].mkdir()

            out = regen.write_summary(
                "LWW", "MD", [row], [], harness, Path("config.xml"), config_version="1"
            )
            html = out.read_text(encoding="utf-8")

            self.assertTrue(out.name.endswith("_regen_compare_v7.html"))
            self.assertIn("<b>Config version</b> v1", html)
            self.assertIn("<b>Report version</b> v7", html)
            self.assertNotIn("Tool version", html)
            self.assertIn("File-level results", html)
            self.assertIn("Matched 100%", html)
            self.assertIn("Not matched", html)
            self.assertIn("Contributor-level results", html)
            self.assertIn("First", html)
            self.assertIn("Last-before", html)
            self.assertIn("Last", html)
            self.assertIn("<th>Original</th><th>Regen</th><th>Percentage</th><th>Remarks</th>", html)
            self.assertIn("Preview HTML", html)
            self.assertIn("Raw XML", html)
            self.assertEqual(html.count('class="table-toggle" data-table-toggle'), 5)
            self.assertEqual(html.count('aria-expanded="true"'), 5)
            self.assertEqual(html.count('class="collapsible-table"'), 5)
            self.assertIn("document.getElementById(target)", html)

    def test_summary_missing_config_version_and_not_allowed_table_control(self):
        with TemporaryDirectory() as tmp:
            harness = Path(tmp)
            row = self.compared_row(harness / "doc-1", group(), group())
            row["folder"].mkdir()

            out = regen.write_summary(
                "LWW", "MD", [row], [("doc-1", 1, "prefix", "element")],
                harness, Path("config.xml"), config_version=""
            )
            html = out.read_text(encoding="utf-8")

            self.assertIn("<b>Config version</b> Not specified", html)
            self.assertEqual(html.count('class="table-toggle" data-table-toggle'), 6)
            targets = [part.split('"', 1)[0] for part in html.split('data-table-target="')[1:]]
            self.assertEqual(len(targets), len(set(targets)))

    def test_detailed_page_shows_two_columns_and_highlights_mismatch(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            row = self.compared_row(folder, group(count=1), group(surname_pi=" | ", count=1))

            row["config_version"] = "1"
            regen.write_compare_html(row)
            html = (folder / "contrib_group_compare.html").read_text(encoding="utf-8")

            self.assertIn("<b>Config version</b> v1", html)
            self.assertIn("<b>Report version</b> v7", html)
            self.assertNotIn("Tool version", html)
            self.assertIn("<th>Original</th><th>Regenerated</th>", html)
            self.assertIn("Preview HTML", html)
            self.assertIn("Raw XML", html)
            self.assertIn('class="pi bad"', html)
            self.assertIn("Mismatch details", html)
            self.assertIn('<span class="mobile-col-label">Original</span>', html)
            self.assertIn('<span class="mobile-col-label">Regenerated</span>', html)
            self.assertEqual(html.count('class="table-toggle" data-table-toggle'), 2)
            self.assertIn('data-table-target="detail-comparison-table"', html)
            self.assertIn('data-table-target="detail-mismatch-table"', html)
            self.assertIn("document.getElementById(target)", html)

    def test_repeated_values_only_highlight_the_mismatched_slot(self):
        with TemporaryDirectory() as tmp:
            original = group(count=3)
            regenerated = original.replace('xml:space=", "', 'xml:space=" | "', 1)
            row = self.compared_row(Path(tmp), original, regenerated)

            regen.write_compare_html(row)
            html = (Path(tmp) / "contrib_group_compare.html").read_text(encoding="utf-8")

            self.assertEqual(html.count('class="pi bad"'), 4)

    def test_missing_pi_has_visible_marker(self):
        with TemporaryDirectory() as tmp:
            original = group(count=1)
            regenerated = original.replace('<?pistart xml:space=", "?>', "", 1)
            row = self.compared_row(Path(tmp), original, regenerated)

            regen.write_compare_html(row)
            html = (Path(tmp) / "contrib_group_compare.html").read_text(encoding="utf-8")

            self.assertIn("[missing PI]", html)

    def test_role_eligibility_matches_first_before_last_rules(self):
        self.assertIsNone(regen.role_index(1, "first"))
        self.assertIsNone(regen.role_index(1, "last-before"))
        self.assertEqual(regen.role_index(1, "last"), 0)
        self.assertEqual(regen.role_index(2, "last-before"), 0)
        self.assertEqual(regen.role_index(2, "last"), 1)
        self.assertEqual(regen.role_index(4, "first"), 0)
        self.assertEqual(regen.role_index(4, "last-before"), 2)
        self.assertEqual(regen.role_index(4, "last"), 3)

    def test_failed_document_is_in_not_matched_with_na_percentage(self):
        with TemporaryDirectory() as tmp:
            harness = Path(tmp)
            failed = {"docid": "bad-doc", "file_id": "BAD-1", "error": "missing original"}

            out = regen.write_summary("LWW", "MD", [failed], [], harness, Path("config.xml"))
            html = out.read_text(encoding="utf-8")

            self.assertIn("Not matched", html)
            self.assertIn("BAD-1", html)
            self.assertIn("N/A", html)
            self.assertIn("missing original", html)

    def test_role_tab_warning_counts_only_that_role(self):
        with TemporaryDirectory() as tmp:
            harness = Path(tmp)
            original = group(count=3)
            regenerated = original.replace('xml:space=", "', 'xml:space=" | "', 1)
            row = self.compared_row(harness / "doc-1", original, regenerated)
            row["folder"].mkdir()

            out = regen.write_summary("LWW", "MD", [row], [], harness, Path("config.xml"))
            html = out.read_text(encoding="utf-8")
            first_button = html.split('data-rt-tab="roles-first"', 1)[1].split("</button>", 1)[0]
            last_button = html.split('data-rt-tab="roles-last"', 1)[1].split("</button>", 1)[0]

            self.assertIn("rt-warn", first_button)
            self.assertNotIn("rt-warn", last_button)

    def test_detailed_table_keeps_between_xref_slot_index(self):
        with TemporaryDirectory() as tmp:
            original = (
                '<contrib-group><contrib><xref rid="a"/><?pistart xml:space=","?>'
                '<xref rid="b"/><?pistart xml:space="; "?></contrib></contrib-group>'
            )
            regenerated = original.replace('xml:space=","', 'xml:space=" | "', 1)
            row = self.compared_row(Path(tmp), original, regenerated)

            regen.write_compare_html(row)
            html = (Path(tmp) / "contrib_group_compare.html").read_text(encoding="utf-8")

            self.assertIn("<td>between-xrefs #1</td>", html)


class ConditionalInsertionTests(unittest.TestCase):
    def load_cfg(self, folder: Path, extra_alias=""):
        config = folder / "config.xml"
        config.write_text(
            f'''<pi-config client="LWW" shortcode="MD"><contrib>
            <elements>
              <prefix allowed="no" alis="affix"/>
              <suffix allowed="no" alis="affix"/>
              <degrees allowed="yes" alis="affix"/>
              <author-comment allowed="yes" alis="affix"/>
              {extra_alias}
            </elements><ques/>
            <separators>
              <given-names value="&#x00A0;" pos="inner"/>
              <surname value="" pos="" when="next-xref"/>
              <surname value=",&#x00A0;" pos="inner" when="following-affix"/>
              <affixes value="," pos="inner" when="subsequent-affix"/>
              <between-xrefs value="," pos="after"/>
              <between-contribs value=", " pos="inner"/>
              <between-contribs when="last-before" value=", "/>
            </separators></contrib></pi-config>''',
            encoding="utf-8",
        )
        return regen.load_config(config)

    def test_given_names_always_gets_configured_pi(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp))
            raw = '<contrib><name><surname>Smith</surname><given-names>Ann</given-names></name></contrib>'

            result = regen.regen_one_contrib(raw, "last", cfg)

            self.assertIn('<given-names>Ann<?pistart xml:space="&#x00A0;"?></given-names>', result)

    def test_load_config_retains_root_version(self):
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.xml"
            config.write_text(
                '<pi-config version="7"><contrib><elements/><ques/><separators/></contrib></pi-config>',
                encoding="utf-8",
            )

            cfg = regen.load_config(config)

            self.assertEqual(cfg["version"], "7")

    def test_load_config_defaults_missing_version_to_empty(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp))

            self.assertEqual(cfg["version"], "")

    def test_load_config_selects_by_followed_journals(self):
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.xml"
            config.write_text(
                '''<pi-config version="1.1">
                <contrib id="master_md" followed-journals="MD,INF">
                  <elements/><ques/>
                  <separators><between-xrefs value="," pos="after"/></separators>
                </contrib>
                <contrib id="master_atv" followed-journals="ATV">
                  <elements/><ques/>
                  <separators><between-xrefs value="" pos="after"/></separators>
                </contrib>
                </pi-config>''',
                encoding="utf-8",
            )

            md = regen.load_config(config, shortcode="MD")
            inf = regen.load_config(config, shortcode="inf")
            atv = regen.load_config(config, shortcode="ATV")

            self.assertEqual(md["contrib_id"], "master_md")
            self.assertEqual(md["sep"]["between-xrefs"], ",")
            self.assertEqual(inf["contrib_id"], "master_md")
            self.assertEqual(atv["contrib_id"], "master_atv")
            self.assertEqual(atv["sep"]["between-xrefs"], "")

    def test_load_config_accepts_singular_followed_journal(self):
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.xml"
            config.write_text(
                '''<pi-config>
                <contrib id="solo" followed-journal="ATV">
                  <elements/><ques/>
                  <separators><between-xrefs value="" pos="after"/></separators>
                </contrib>
                </pi-config>''',
                encoding="utf-8",
            )

            cfg = regen.load_config(config, shortcode="ATV")

            self.assertEqual(cfg["contrib_id"], "solo")
            self.assertEqual(cfg["followed_journals"], ["ATV"])

    def test_load_config_no_match_raises(self):
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.xml"
            config.write_text(
                '''<pi-config>
                <contrib id="master_md" followed-journals="MD">
                  <elements/><ques/><separators/>
                </contrib>
                <contrib id="master_atv" followed-journals="ATV">
                  <elements/><ques/><separators/>
                </contrib>
                </pi-config>''',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as ctx:
                regen.load_config(config, shortcode="XYZ")

            self.assertIn("no <contrib> followed-journals match", str(ctx.exception))
            self.assertIn("XYZ", str(ctx.exception))

    def test_load_config_duplicate_match_raises(self):
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.xml"
            config.write_text(
                '''<pi-config>
                <contrib id="a" followed-journals="MD,ATV">
                  <elements/><ques/><separators/>
                </contrib>
                <contrib id="b" followed-journals="ATV">
                  <elements/><ques/><separators/>
                </contrib>
                </pi-config>''',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as ctx:
                regen.load_config(config, shortcode="ATV")

            self.assertIn("matched multiple", str(ctx.exception))

    def test_empty_between_xrefs_skips_insertion(self):
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.xml"
            config.write_text(
                '''<pi-config>
                <contrib id="atv" followed-journals="ATV">
                  <elements/><ques/>
                  <separators>
                    <given-names value="&#x00A0;" pos="inner"/>
                    <between-xrefs value="" pos="after"/>
                    <between-contribs value=", " pos="inner"/>
                  </separators>
                </contrib>
                </pi-config>''',
                encoding="utf-8",
            )
            cfg = regen.load_config(config, shortcode="ATV")
            raw = (
                '<contrib><name><surname>Shi</surname>'
                '<given-names>Hongjie</given-names></name>'
                '<xref rid="a"/><xref rid="b"/><xref rid="c"/></contrib>'
            )

            result = regen.regen_one_contrib(raw, "last", cfg)

            self.assertNotIn('<?pistart xml:space=","?>', result)
            self.assertIn('<xref rid="a"/><xref rid="b"/><xref rid="c"/>', result)

    def test_right_after_name_when_no_affix(self):
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.xml"
            config.write_text(
                '''<pi-config>
                <contrib id="atv" followed-journals="ATV">
                  <elements>
                    <suffix allowed="yes" alis="affix"/>
                    <degrees allowed="no" alis="affix"/>
                  </elements><ques/>
                  <separators>
                    <given-names value="&#x00A0;" pos="inner"/>
                    <between-xrefs value="" pos="after"/>
                    <between-contribs value=", " pos="inner" when="no-affix" loc="right-after-name"/>
                    <between-contribs value=", " pos="inner"/>
                  </separators>
                </contrib>
                </pi-config>''',
                encoding="utf-8",
            )
            cfg = regen.load_config(config, shortcode="ATV")
            no_affix = (
                '<contrib><name><surname>Shi</surname>'
                '<given-names>Hongjie</given-names></name>'
                '<xref rid="a"/><xref rid="b"/></contrib>'
            )
            with_affix = (
                '<contrib><name><surname>Shi</surname>'
                '<given-names>Hongjie</given-names></name>'
                '<suffix>Jr</suffix><xref rid="a"/></contrib>'
            )

            out_no = regen.regen_one_contrib(no_affix, "first", cfg)
            out_yes = regen.regen_one_contrib(with_affix, "first", cfg)

            self.assertIn(
                '</name><?pistart xml:space=", "?><xref rid="a"/>',
                out_no,
            )
            self.assertNotIn('</name><?pistart', out_yes)
            self.assertIn('<suffix>Jr</suffix>', out_yes)

    def test_xref_after_name_suppresses_surname_pi(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp))
            raw = '<contrib><name><surname>Smith</surname><given-names>Ann</given-names></name><xref rid="a"/></contrib>'

            result = regen.regen_one_contrib(raw, "last", cfg)

            self.assertNotIn("Smith<?pistart", result)

    def test_affix_after_name_adds_surname_pi(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp))
            raw = '<contrib><name><surname>Smith</surname><given-names>Ann</given-names></name><degrees>MD</degrees></contrib>'

            result = regen.regen_one_contrib(raw, "last", cfg)

            self.assertIn('<surname>Smith<?pistart xml:space=",&#x00A0;"?></surname>', result)

    def test_non_affix_after_name_does_not_add_surname_pi(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp))
            raw = '<contrib><name><surname>Smith</surname><given-names>Ann</given-names></name><email>a@b.test</email></contrib>'

            result = regen.regen_one_contrib(raw, "last", cfg)

            self.assertNotIn("Smith<?pistart", result)

    def test_second_and_later_affixes_get_commas(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp))
            raw = ('<contrib><name><surname>Smith</surname><given-names>Ann</given-names></name>'
                   '<degrees>MD</degrees><author-comment>Lead</author-comment><suffix>Jr</suffix></contrib>')

            result = regen.regen_one_contrib(raw, "last", cfg)

            self.assertNotIn('MD<?pistart xml:space=","?>', result)
            self.assertIn('<author-comment>Lead<?pistart xml:space=","?></author-comment>', result)
            self.assertIn('<suffix>Jr<?pistart xml:space=","?></suffix>', result)

    def test_self_closing_subsequent_affix_is_expanded(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp))
            raw = ('<contrib><name><surname>Smith</surname><given-names>Ann</given-names></name>'
                   '<degrees>MD</degrees><suffix/></contrib>')

            result = regen.regen_one_contrib(raw, "last", cfg)

            self.assertIn('<suffix><?pistart xml:space=","?></suffix>', result)

    def test_affix_membership_comes_from_alias(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp), '<role allowed="yes" alis="affix"/>')
            raw = '<contrib><name><surname>Smith</surname><given-names>Ann</given-names></name><role>Editor</role></contrib>'

            result = regen.regen_one_contrib(raw, "last", cfg)

            self.assertIn('Smith<?pistart xml:space=",&#x00A0;"?>', result)

    def test_existing_xref_and_contrib_separator_rules_remain(self):
        with TemporaryDirectory() as tmp:
            cfg = self.load_cfg(Path(tmp))
            raw = ('<contrib><name><surname>Smith</surname><given-names>Ann</given-names></name>'
                   '<xref rid="a"/><xref rid="b"/></contrib>')

            result = regen.regen_one_contrib(raw, "last-before", cfg)

            self.assertIn('<xref rid="a"/><?pistart xml:space=","?><xref rid="b"/>', result)
            self.assertTrue(result.endswith('<?pistart xml:space=", "?></contrib>'))


if __name__ == "__main__":
    unittest.main()
