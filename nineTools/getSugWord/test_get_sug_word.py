"""Offline regression tests. Run with python -B -m unittest discover -s this_directory."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import get_sug_word as app


class FakeFetcher:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = iter(responses) if responses is not None else None

    def fetch(self, query):
        self.calls.append((query.market, query.prefix))
        item = next(self.responses) if self.responses is not None else [query.prefix + " result"]
        if isinstance(item, BaseException):
            raise item
        return app.Result(query.market, "aps", query.prefix, app.now_text(), "api",
                          app.api_url(query, "aps"), item)

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".test_", dir=app.BASE)
        self.root = Path(self.temporary.name).resolve()
        self.assertEqual(self.root.parent, app.BASE.resolve())
        self.addCleanup(self.temporary.cleanup)
        self.settings = app.Settings(markets=("de",), retries=0)
        self.logs = []

    def collect(self, queries, fetcher, name="output", **kwargs):
        return app.run_collection(self.settings, queries, self.root/name, self.root/"cache",
                                  self.logs.append, fetcher=fetcher, **kwargs)

    def test_keywords_bom_duplicates_and_txt_validation(self):
        path = self.root/"input.txt"
        path.write_text("\ufeff  pull de noël  \n\npull de noël\nNoël\n", encoding="utf-8")
        self.assertEqual(app.read_keywords(path), ["pull de noël", "Noël"])
        with self.assertRaises(ValueError):
            app.require_txt(self.root/"input.csv")

    def test_query_expansion_and_shared_provenance(self):
        self.assertEqual(len(app.build_queries("fr", ["pull"], "none")), 1)
        self.assertEqual(len(app.build_queries("fr", ["pull"], "letters")), 28)
        self.assertEqual(len(app.build_queries("fr", ["pull"], "letters-digits")), 38)
        queries = app.build_queries("fr", ["pull", "pull a"], "letters")
        shared = next(q for q in queries if q.prefix == "pull a")
        self.assertEqual(shared.seeds, ["pull", "pull a"])
        self.assertEqual(len({q.prefix for q in queries}), len(queries))
        self.assertIn("pull ", {q.prefix for q in queries})

    def test_parse_preserves_raw_phrases_and_keyword_types(self):
        values = ["pull de noël", "pull de noël", "Pull de Noël", "pull à capuche"]
        payload = {"suggestions": [{"type": "KEYWORD", "value": v} for v in values]
                   + [{"type": "WIDGET", "value": "excluded"}]}
        self.assertEqual(app.parse_suggestions(json.dumps(payload)),
                         ["pull de noël", "Pull de Noël", "pull à capuche"])
        self.assertEqual(app.parse_suggestions('{"suggestions": []}'), [])
        for body in ["<html>validation</html>", '{}', '["word"]',
                     '{"suggestions":[{"value":null}]}',
                     '{"suggestions":[{"value":"line1\\nline2"}]}']:
            with self.subTest(body=body), self.assertRaises(app.SuggestionError):
                app.parse_suggestions(body)

    def test_market_urls_keep_french_accents_and_prefix_space(self):
        url = app.api_url(app.Query("fr", "pull de noël "), "aps")
        parsed = parse_qs(urlsplit(url).query, keep_blank_values=True)
        self.assertIn("completion.amazon.fr", url)
        self.assertEqual(parsed["prefix"], ["pull de noël "])
        self.assertEqual(parsed["mid"], ["A13V1IB3VIYZZH"])

    def test_cache_roundtrip_expiry_corruption_and_distinct_prefixes(self):
        query = app.Query("de", "word ", ["word"])
        result = FakeFetcher().fetch(query)
        path = app.cache_path(self.root, query, "aps")
        app.save_cache(path, result)
        self.assertEqual(app.read_cache(path, query, self.settings), result)
        self.assertNotEqual(path, app.cache_path(self.root, app.Query("de", "word"), "aps"))
        result.collected_at = (datetime.now(app.LOCAL_TIME)-timedelta(hours=25)).isoformat()
        app.save_cache(path, result)
        self.assertIsNone(app.read_cache(path, query, self.settings))
        path.write_text("partial write", encoding="utf-8")
        self.assertIsNone(app.read_cache(path, query, self.settings))

    def test_word_cache_has_no_metadata_and_detects_partial_updates(self):
        query = app.Query("de", "seed", ["seed"])
        result = FakeFetcher().fetch(query)
        path = app.cache_path(self.root,query,"aps")
        app.save_cache(path,result)
        self.assertEqual(path.suffix,".json")
        word_path = path.with_suffix(".txt")
        self.assertEqual(word_path.read_text(encoding="utf-8"),"seed result\n")
        word_path.write_text("changed result\n",encoding="utf-8")
        self.assertIsNone(app.read_cache(path,query,self.settings))
        app.save_cache(path,result)
        word_path.unlink()
        self.assertIsNone(app.read_cache(path,query,self.settings))

    def test_resume_limit_and_output_only_contains_returned_words(self):
        queries = app.build_queries("de", ["seed"], "letters")
        first = FakeFetcher([["returned one", "returned two"]])
        self.assertEqual(self.collect(queries, first, max_queries=1), 0)
        self.assertEqual(first.calls, [("de", "seed")])
        second = FakeFetcher([["returned two", "returned three"]])
        self.assertEqual(self.collect(queries, second, name="second", max_queries=1), 0)
        self.assertEqual(second.calls, [("de", "seed ")])
        words = (self.root/"second/de_suggestions.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(words, ["returned one", "returned two", "returned three"])
        details = json.loads((self.root/"second/de_details.json").read_text(encoding="utf-8"))
        self.assertEqual(details["queries"][0]["suggestions"][1],{"rank":2,"word_line":2})
        self.assertEqual(details["queries"][1]["suggestions"][0],{"rank":1,"word_line":2})
        pending = (self.root/"second/de_unfinished.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(pending,[q.prefix for q in queries[2:]])

    def test_empty_response_is_success_and_cached(self):
        queries = app.build_queries("de", ["seed"], "none")
        self.assertEqual(self.collect(queries, FakeFetcher([[]])), 0)
        unused = FakeFetcher()
        self.assertEqual(self.collect(queries, unused, name="second"), 0)
        self.assertEqual(unused.calls, [])
        self.assertEqual((self.root/"second/de_suggestions.txt").read_text(), "")
        self.assertIn("其中无建议 1 个", (self.root/"second/summary.md").read_text(encoding="utf-8"))

    def test_failure_is_not_cached_and_refresh_does_not_export_stale_words(self):
        queries = app.build_queries("de", ["seed"], "none")
        self.collect(queries, FakeFetcher([["old result"]]))
        failed = FakeFetcher([app.SuggestionError("failed request")])
        self.assertEqual(self.collect(queries, failed, name="refreshed", refresh=True), 1)
        self.assertEqual((self.root/"refreshed/de_suggestions.txt").read_text(), "")
        self.assertEqual((self.root/"refreshed/de_unfinished.txt").read_text(),"seed\n")
        errors = json.loads((self.root/"refreshed/de_failures.json").read_text(encoding="utf-8"))
        self.assertEqual(errors[0]["reason"],"failed request")
        self.assertEqual(errors[0]["status"],"failed")

    def test_rate_limit_pauses_market_and_does_not_cache_failure(self):
        queries = [app.Query("de", "first", ["first"]), app.Query("de", "second", ["second"]),
                   app.Query("fr", "third", ["third"])]
        self.settings.markets = ("de", "fr")
        fetcher = FakeFetcher([app.SuggestionError("HTTP 429", rate_limited=True), ["fr result"]])
        self.assertEqual(self.collect(queries, fetcher), 1)
        self.assertEqual(fetcher.calls, [("de", "first"), ("fr", "third")])
        self.assertFalse(app.cache_path(self.root/"cache", queries[0], "aps").exists())
        self.assertEqual((self.root/"output/de_suggestions.txt").read_text(), "")

    def test_interrupt_saves_completed_results_for_resume(self):
        queries = app.build_queries("de", ["one", "two"], "none")
        self.assertEqual(self.collect(queries, FakeFetcher([["first result"], KeyboardInterrupt()])), 130)
        resumed = FakeFetcher([["second result"]])
        self.assertEqual(self.collect(queries, resumed, name="resumed"), 0)
        self.assertEqual(resumed.calls, [("de", "two")])
        self.assertEqual((self.root/"resumed/de_suggestions.txt").read_text(encoding="utf-8").splitlines(),
                         ["first result", "second result"])

    def test_retry_and_rate_limit_wait_limit(self):
        query = app.Query("de", "seed", ["seed"])
        self.settings.retries = 1
        fetcher = app.Fetcher(self.settings, self.logs.append)
        result = FakeFetcher().fetch(query)
        with patch.object(fetcher.limiter, "wait"), patch.object(app.time, "sleep"), \
                patch.object(app, "request_api", side_effect=[app.SuggestionError("timeout", retryable=True), result]) as request:
            self.assertEqual(fetcher.fetch(query), result)
            self.assertEqual(request.call_count, 2)
        with patch.object(fetcher.limiter, "wait"), patch.object(app.time, "sleep") as sleep, \
                patch.object(app, "request_api", side_effect=app.SuggestionError("429", retryable=True,
                             rate_limited=True, retry_after=120)):
            with self.assertRaises(app.SuggestionError):
                fetcher.fetch(query)
            sleep.assert_not_called()

    def test_nonretryable_failure_is_reported_once(self):
        query = app.Query("de", "seed", ["seed"])
        self.settings.retries = 2
        fetcher = app.Fetcher(self.settings, self.logs.append)
        with patch.object(fetcher.limiter, "wait"), \
                patch.object(app, "request_api", side_effect=app.SuggestionError("unavailable")) as request:
            with self.assertRaises(app.SuggestionError):
                fetcher.fetch(query)
            request.assert_called_once_with(query,self.settings)

    def test_python_config_and_validation(self):
        path = self.root/"config.py"
        path.write_text("SETTINGS = {'markets':['fr'],'interval':1.5,'cache_hours':0}\n", encoding="utf-8")
        settings = app.read_config(path)
        self.assertEqual(settings.markets, ("fr",))
        self.assertEqual(settings.interval, 1.5)
        self.assertEqual(settings.cache_hours,0)
        for value in [{"interval":0.1},{"timeout":float("inf")},{"markets":["xx"]},
                      {"retries":6},{"unknown":1},{"markets":"fr"},{"timeout":"bad"},{"expand":[]}]:
            # Keep non-finite numbers representable in an executable Python configuration.
            expression = repr(value).replace("inf", "float('inf')")
            path.write_text("SETTINGS = "+expression+"\n", encoding="utf-8")
            with self.subTest(value=value), self.assertRaises(ValueError):
                app.read_config(path)


if __name__ == "__main__":
    unittest.main()
