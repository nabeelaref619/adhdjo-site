#!/usr/bin/env python3
"""Validate the built bilingual static site without network access.

Run with Python + beautifulsoup4 from any directory:
  ../.venv/bin/python scripts/validate_site.py --as-of 2026-11-19

Checks are based on routes, DOM structure and the versioned directory evidence,
not article length or an assumption that a source check is clinical review.
External URLs are inventoried but never fetched by this script.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("beautifulsoup4 is required; run this script with the project's Python environment.")

ORIGIN = "https://adhdjo.org"
HOSTS = {"adhdjo.org", "www.adhdjo.org"}
ARTICLE_ROUTE = re.compile(r"^/(en|ar)/learn/[^/]+/$")
PRIVACY_ROUTES = {"/en/privacy/", "/ar/privacy/"}
PLACEHOLDER = re.compile(r"\b(?:lorem ipsum|TODO|TBD|YOUR[_ -](?:NAME|EMAIL|PHONE)|example@example\.(?:com|org))\b", re.I)
FALSE_BADGE = re.compile(r"^(?:[✓✔✅]\s*)?(?:verified(?:\s+(?:doctor|clinician|specialist|clinic))?|approved specialist|طبيب موثّ?ق|مختص معتمد)$", re.I)


def route_for(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return "/" + (rel[:-10] if rel.endswith("index.html") else rel)


def parse_jsonld(text: str):
    value = json.loads(text)
    if not isinstance(value, (dict, list)):
        raise ValueError("JSON-LD must be an object or array")
    return value


class Validator:
    def __init__(self, root: Path, as_of: dt.date):
        self.root = root.resolve()
        self.as_of = as_of
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.stats = collections.Counter()
        self.article_words = {}
        self.documents = {}
        self.routes = {}
        self.redirects = {}
        self.indexable = set()
        self.external_urls = set()
        for file in sorted(self.root.rglob("*.html")):
            if any(p.startswith(".") or p in {"node_modules", "scripts"} for p in file.relative_to(self.root).parts):
                continue
            route = route_for(file, self.root)
            self.documents[file.resolve()] = BeautifulSoup(file.read_text(encoding="utf-8"), "html.parser")
            self.routes[file.resolve()] = route

    def issue(self, code, file, message, warning=False):
        try:
            label = str(Path(file).relative_to(self.root))
        except (ValueError, TypeError):
            label = str(file)
        (self.warnings if warning else self.errors).append({"code": code, "file": label, "message": message})

    def resolve(self, route: str, reference: str):
        absolute = urljoin(ORIGIN + route, reference.strip())
        parsed = urlsplit(absolute)
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.hostname not in HOSTS:
            self.external_urls.add(absolute)
            return None
        path = (self.root / unquote(parsed.path).lstrip("/")).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("URL escapes the site directory")
        if parsed.path.endswith("/") or path.is_dir():
            path = path / "index.html"
        return path, unquote(parsed.fragment), absolute

    def check_reference(self, file, reference, attr, tag):
        if not reference:
            self.issue("empty-reference", file, f"<{tag}> has an empty {attr}")
            return
        try:
            result = self.resolve(self.routes[file], reference)
        except ValueError as exc:
            self.issue("invalid-url", file, f"{reference!r}: {exc}")
            return
        if result is None:
            return
        target, fragment, _ = result
        self.stats["internal_references"] += 1
        if not target.is_file():
            self.issue("missing-target", file, f"{attr}={reference!r} has no local file")
            return
        # Browser text fragments need no id. A preceding ordinary fragment does.
        anchor = fragment.split(":~:text=", 1)[0]
        if anchor and target in self.documents:
            document = self.documents[target]
            if not document.find(id=anchor) and not document.find("a", attrs={"name": anchor}):
                self.issue("missing-anchor", file, f"{reference!r}: target has no #{anchor}")

    def check_documents(self):
        for file, doc in self.documents.items():
            route = self.routes[file]
            self.stats["html_pages"] += 1
            refresh = doc.find("meta", attrs={"http-equiv": re.compile(r"^refresh$", re.I)})
            canonical_tags = doc.select('link[rel~="canonical"]')
            if len(canonical_tags) != 1:
                self.issue("canonical-count", file, f"Expected one canonical link, found {len(canonical_tags)}")
                canonical = None
            else:
                href = canonical_tags[0].get("href", "")
                canonical = urljoin(ORIGIN + route, href)
                if not href.startswith("https://"):
                    self.issue("relative-search-metadata", file, "Prefer an absolute HTTPS canonical URL", warning=True)
            if refresh:
                self.stats["redirect_pages"] += 1
                match = re.search(r"(?:^|;)\s*url\s*=\s*(['\"]?)(.+?)\1\s*$", refresh.get("content", ""), re.I)
                if not match:
                    self.issue("redirect-target", file, "Refresh redirect has no parseable URL")
                else:
                    target_url = urljoin(ORIGIN + route, match.group(2))
                    self.redirects[route] = target_url
                    self.check_reference(file, match.group(2), "refresh", "meta")
                    if canonical != target_url:
                        self.issue("redirect-canonical", file, "Redirect canonical differs from refresh destination")
                robots = ",".join(m.get("content", "") for m in doc.select('meta[name="robots"]')).lower()
                if "noindex" not in robots:
                    self.issue("redirect-indexable", file, "Legacy redirect should be noindex")
            else:
                if canonical != ORIGIN + route:
                    self.issue("canonical-target", file, f"Canonical must identify this page: {ORIGIN + route}")
                robots = ",".join(m.get("content", "") for m in doc.select('meta[name="robots"]')).lower()
                if "noindex" not in robots:
                    self.indexable.add(ORIGIN + route)
                self.check_languages(file, doc, route)
                if not doc.find("main"):
                    self.issue("missing-main", file, "Content page has no main landmark")
                if len(doc.find_all("h1")) != 1:
                    self.issue("heading-count", file, "Content page must have one primary heading")
            ids = [tag["id"] for tag in doc.select("[id]")]
            for ident, count in collections.Counter(ids).items():
                if count > 1:
                    self.issue("duplicate-id", file, f"#{ident} occurs {count} times")
            for tag in doc.select("[href], [src]"):
                for attr in ("href", "src"):
                    if tag.has_attr(attr):
                        self.check_reference(file, tag[attr], attr, tag.name)
            for tag in doc.select('script[type="application/ld+json"]'):
                try:
                    schema = parse_jsonld(tag.string or tag.get_text())
                    self.check_review_claims(file, schema)
                    self.stats["jsonld_blocks"] += 1
                except (json.JSONDecodeError, ValueError) as exc:
                    self.issue("invalid-jsonld", file, str(exc))
            visible = BeautifulSoup(str(doc.body or doc), "html.parser")
            for tag in visible.select("script, style, template"):
                tag.decompose()
            match = PLACEHOLDER.search(visible.get_text(" ", strip=True))
            if match:
                self.issue("placeholder-copy", file, f"Unfinished text: {match.group(0)!r}")
            for tag in doc.select('.badge, .verified, .tag, [data-verification], [data-verified]'):
                if FALSE_BADGE.fullmatch(tag.get_text(" ", strip=True)) or tag.get("data-verified") == "true":
                    self.issue("unsupported-verification-badge", file, "A public source check must not be presented as clinical verification")
            self.check_ads(file, doc, route, bool(refresh))
            if ARTICLE_ROUTE.fullmatch(route) and not refresh:
                body = BeautifulSoup(str(doc.select_one(".article-body") or doc.main), "html.parser")
                for tag in body.select("script, style, nav, aside, .sources, .byline, .learning-controls, .ad-section"):
                    tag.decompose()
                self.article_words[route] = len(re.findall(r"\b[^\W_]+(?:[’'-][^\W_]+)*\b", body.get_text(" ", strip=True), re.UNICODE))

    def check_review_claims(self, file, value):
        """This release has source checks but no independent clinical review."""
        if isinstance(value, dict):
            if value.get("reviewedBy") or value.get("medicalReviewer"):
                self.issue("unsupported-reviewer-claim", file,
                           "Structured data claims a reviewer, but this release has no recorded clinical review")
            for child in value.values():
                self.check_review_claims(file, child)
        elif isinstance(value, list):
            for child in value:
                self.check_review_claims(file, child)

    def check_languages(self, file, doc, route):
        parts = route.strip("/").split("/")
        lang = parts[0] if parts[0] in {"en", "ar"} else None
        if lang:
            html = doc.find("html")
            if not html or html.get("lang") != lang:
                self.issue("document-language", file, f"Expected html lang={lang}")
            if lang == "ar" and (not html or html.get("dir") != "rtl"):
                self.issue("arabic-direction", file, "Arabic page must have dir=rtl")
        expected = {language: ORIGIN + "/" + language + "/" + "/".join(parts[1:]) + ("/" if parts[1:] else "") for language in ("en", "ar")} if lang else {"en": ORIGIN + "/en/", "ar": ORIGIN + "/ar/"}
        if not lang and route != "/":
            return
        for language, url in expected.items():
            tags = doc.select(f'link[rel~="alternate"][hreflang="{language}"]')
            if len(tags) != 1 or urljoin(ORIGIN + route, tags[0].get("href", "")) != url:
                self.issue("language-alternate", file, f"Expected one {language} alternate pointing to {url}")
        if lang:
            opposite = "ar" if lang == "en" else "en"
            switch = doc.select_one(".language-switch")
            if not switch or urljoin(ORIGIN + route, switch.get("href", "")) != expected[opposite]:
                self.issue("language-switch", file, "Language switch does not reach the corresponding translated page")

    def check_ads(self, file, doc, route, redirect):
        slots = doc.select("ins.adsbygoogle, [data-ad-slot]")
        slots = list({id(tag): tag for tag in slots}.values())
        loaders = [tag for tag in doc.select("script[src]") if "pagead/js/adsbygoogle.js" in tag["src"]]
        inline = "\n".join(tag.string or tag.get_text() for tag in doc.find_all("script", src=False))
        ad_script = bool(loaders or re.search(r"adsbygoogle\s*[=.)]|adsbygoogle[^\n]*\.push", inline))
        article = bool(ARTICLE_ROUTE.fullmatch(route)) and not redirect
        privacy = route in PRIVACY_ROUTES and not redirect
        if not article and slots:
            self.issue("ad-placement-scope", file, "Only substantive guide articles may contain ad placements")
        if not article and not privacy and ad_script:
            self.issue("ad-script-scope", file, "This page must not load or initialize Google advertising")
        if article and len(slots) != 1:
            self.issue("manual-ad-count", file, f"Expected one preserved manual article unit, found {len(slots)}")
        if article and len(loaders) != 1:
            self.issue("ad-loader-count", file, f"Expected one Google loader, found {len(loaders)}")
        if privacy and len(loaders) != 1:
            self.issue("privacy-loader-count", file, "Privacy page must retain one Google loader for consent revocation")
        if loaders:
            self.stats["pages_loading_google_ads"] += 1
            if not re.search(r"requestNonPersonalizedAds\s*=\s*1\b", inline):
                self.issue("ad-privacy-flag", file, "Missing requestNonPersonalizedAds=1 before ad requests")
            for loader in loaders:
                if loader.get("data-privacy-treatments") != "disablePersonalization":
                    self.issue("ad-privacy-treatment", file, "Google loader must disable personalization")
            if not doc.select_one("[data-ad-privacy]") or not any("ads-privacy.js" in t["src"] for t in doc.select("script[src]")):
                self.issue("privacy-control", file, "Google-enabled page needs the privacy-settings control and its script")
            first_loader = list(doc.find_all("script")).index(loaders[0])
            preceding = "\n".join(t.string or t.get_text() for t in list(doc.find_all("script"))[:first_loader])
            if not re.search(r"requestNonPersonalizedAds\s*=\s*1\b", preceding):
                self.issue("ad-privacy-order", file, "Privacy flag must precede the Google loader")
        if re.search(r"enable_page_level_ads\s*:\s*true", inline):
            self.issue("auto-ad-config", file, "Page config enables automatic page-level ads")
        for slot in slots:
            self.stats["manual_ad_units"] += 1
            if not re.fullmatch(r"\d+", slot.get("data-ad-slot", "")):
                self.issue("ad-slot-id", file, "Manual unit lacks a numeric ad-slot ID")
            if not re.fullmatch(r"ca-pub-\d+", slot.get("data-ad-client", "")):
                self.issue("ad-client-id", file, "Manual unit lacks a publisher ID")
            if not slot.find_parent(attrs={"aria-label": re.compile(r"Advertisement|إعلان", re.I)}):
                self.issue("ad-labelling", file, "Manual unit lacks an advertising-labelled container")

    def check_sitemap(self):
        path = self.root / "sitemap.xml"
        try:
            tree = ET.parse(path)
        except (OSError, ET.ParseError) as exc:
            self.issue("sitemap-parse", path, str(exc))
            return
        locations = [n.text or "" for n in tree.findall(".//{*}loc")]
        self.stats["sitemap_urls"] = len(locations)
        for url, count in collections.Counter(locations).items():
            if count > 1:
                self.issue("sitemap-duplicate", path, f"{url} occurs {count} times")
            if url not in self.indexable:
                self.issue("sitemap-noncanonical", path, f"Not a current indexable page: {url}")
        for missing in sorted(self.indexable - set(locations)):
            self.issue("sitemap-missing", path, f"Current page missing: {missing}")
        for route, target in self.redirects.items():
            if urlsplit(target).path in self.redirects:
                self.issue("redirect-chain", route, f"Redirect points at another redirect: {target}")

    def check_directory(self):
        path = self.root / "content/directory.json"
        if not path.exists():
            self.issue("directory-evidence-missing", path, "Versioned public directory data is required for provenance checks")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.issue("directory-evidence-json", path, str(exc))
            return
        self.validate_directory_data(path, data)

    def validate_directory_data(self, path, data):
        # The public-data adapter is intentionally isolated from generic HTML checks.
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            self.issue("directory-evidence-schema", path, "Expected public directory schema_version 1")
            return
        records = data.get("records", [])
        if not isinstance(records, list) or not records:
            self.issue("directory-evidence-schema", path, "Expected a nonempty entries or records array")
            return
        by_id = {}
        for record in records:
            if not isinstance(record, dict):
                self.issue("directory-evidence-schema", path, "Each record must be an object")
                continue
            ident = record.get("id")
            if not ident or ident in by_id:
                self.issue("directory-data-id", path, f"Missing or duplicate entry ID: {ident!r}")
            else:
                by_id[ident] = record
        seen = {}
        for lang in ("en", "ar"):
            file = (self.root / lang / "support/index.html").resolve()
            doc = self.documents.get(file)
            if not doc:
                self.issue("directory-page-missing", file, "Translated directory page is missing")
                continue
            cards = doc.select("[data-resource]")
            seen[lang] = {card.get("data-resource-id") for card in cards}
            self.stats[f"directory_cards_{lang}"] = len(cards)
            if len(seen[lang]) != len(cards):
                self.issue("directory-card-id", file, "Directory card IDs must be unique")
            for card in cards:
                ident = card.get("data-resource-id")
                if not ident or card.get("id") != "resource-" + ident:
                    self.issue("directory-card-id", file, "Each card needs a data-resource-id and matching resource-ID anchor")
                record = by_id.get(ident)
                if record is None:
                    self.issue("unsupported-directory-entry", file, f"#{ident} has no public evidence record")
                    continue
                self.check_card_evidence(file, card, record, data, path, lang)
            missing = set(by_id) - seen[lang]
            for ident in sorted(missing):
                self.issue("missing-directory-entry", file, f"Evidence entry #{ident} is missing from this translation")
        if seen.get("en") != seen.get("ar"):
            self.issue("directory-language-parity", path, "English and Arabic directory IDs differ")

    def check_card_evidence(self, file, card, record, data, path, lang):
        ident = record["id"]
        expected_name = record.get("name", {}).get(lang)
        heading = card.find(re.compile(r"^h[2-6]$"))
        if not expected_name or not heading or " ".join(heading.stripped_strings) != " ".join(expected_name.split()):
            self.issue("directory-name-mismatch", file, f"#{ident} heading differs from its published {lang} evidence record")
        if card.get("data-country") != record.get("country_code") or card.get("data-type") != record.get("category"):
            self.issue("directory-filter-mismatch", file, f"#{ident} country/category filters differ from the evidence record")
        visible_text = " ".join(card.stripped_strings)
        for field in ("description", "access"):
            expected = record.get(field, {}).get(lang)
            if not expected or " ".join(expected.split()) not in visible_text:
                self.issue("directory-scope-mismatch", file, f"#{ident} is missing its recorded {lang} {field}, including service limits")
        checked = record.get("checked_on", data.get("checked_on") if isinstance(data, dict) else None)
        try:
            day = dt.date.fromisoformat(checked or "")
            if day > self.as_of:
                raise ValueError("date is in the future")
            if (self.as_of - day).days > 90:
                self.issue("directory-stale-source", file, f"#{ident} source check is more than 90 days old")
        except (TypeError, ValueError) as exc:
            self.issue("directory-check-date", path, f"#{ident}: invalid checked_on {checked!r}: {exc}")
        if not card.find("time", attrs={"datetime": checked}):
            self.issue("directory-visible-date", file, f"#{ident} must show its source-check date {checked}")
        sources = record.get("sources", [])
        evidence = {s.get("url") if isinstance(s, dict) else s for s in sources}
        source_map = data.get("sources", {}) if isinstance(data, dict) else {}
        for sid in record.get("source_ids", []):
            source = source_map.get(sid, {})
            evidence.add(source.get("url") if isinstance(source, dict) else source)
        evidence = {url for url in evidence if isinstance(url, str) and url.startswith("https://")}
        links = {a.get("href") for a in card.select('.sources a[href^="https://"]')}
        if not evidence:
            self.issue("directory-no-evidence", path, f"#{ident} has no primary-source URL")
        elif not (links & evidence):
            self.issue("directory-evidence-link", file, f"#{ident} source list does not link its recorded evidence")
        for contact in record.get("contacts", []):
            if not isinstance(contact, dict) or not contact.get("source") or contact.get("source") not in evidence:
                self.issue("directory-contact-evidence", path, f"#{ident} contact lacks a recorded source URL")
        contacts = [c for c in record.get("contacts", []) if isinstance(c, dict)]
        phones = {re.sub(r"\D", "", c.get("dial", c.get("value", ""))) for c in contacts if c.get("kind") == "phone"}
        emails = {c.get("value", "").casefold() for c in contacts if c.get("kind") == "email"}
        for link in card.select("a[href]"):
            href = link["href"]
            if href.startswith("tel:") and re.sub(r"\D", "", unquote(href[4:])) not in phones:
                self.issue("unsupported-directory-contact", file, f"#{ident} phone link is not in its evidence record")
            if href.startswith("mailto:") and unquote(href[7:].split("?", 1)[0]).casefold() not in emails:
                self.issue("unsupported-directory-contact", file, f"#{ident} email link is not in its evidence record")
            if href.startswith("https://") and href not in evidence | {record.get("url")}:
                self.issue("unsupported-directory-link", file, f"#{ident} link is not in its evidence record: {href}")
        for bad_flag in ("licence_checked", "availability_confirmed", "endorsement"):
            if record.get(bad_flag) is True:
                self.issue("directory-overclaim", path, f"#{ident} claims {bad_flag}, beyond this public-source review")
        if record.get("clinical_quality_rating") is not None:
            self.issue("directory-quality-rating", path, f"#{ident} has an unsupported clinical quality rating")

    def run(self):
        self.check_documents()
        self.check_sitemap()
        self.check_directory()
        self.stats["external_urls_not_fetched"] = len(self.external_urls)
        return {"as_of": self.as_of.isoformat(), "status": "pass" if not self.errors else "fail", "stats": dict(self.stats), "article_main_word_counts": self.article_words, "errors": self.errors, "warnings": self.warnings,
                "limits": ["Word counts are descriptive, not a quality score or AdSense threshold.", "No external URL requests or Google account settings were checked.", "Directory evidence checks confirm traceability, not licensure, clinical quality or availability."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.datetime.now(ZoneInfo("Asia/Amman")).date())
    parser.add_argument("--json", action="store_true", help="Print the full structured report")
    args = parser.parse_args()
    report = Validator(args.root, args.as_of).run()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Site validation: {report['status'].upper()} — {len(report['errors'])} errors, {len(report['warnings'])} warnings")
        print(json.dumps(report["stats"], ensure_ascii=False, sort_keys=True))
        for issue in report["errors"] + report["warnings"]:
            print(f"{issue['code']}: {issue['file']}: {issue['message']}")
        print("Article main-body words (descriptive only):")
        for route, words in sorted(report["article_main_word_counts"].items()):
            print(f"  {route}: {words}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
