#!/usr/bin/env python3
"""Check media provenance, bilingual publication and click-to-load privacy.

No network access or content-generation imports. This cannot verify the truth
of a caption or upload date against the live platform; it checks the reviewed
catalogue is published faithfully and prevents known unsafe substitutions.
"""
import argparse
import collections
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup


ORIGIN = 'https://adhdjo.org'
PLATFORM_HOSTS = {
    'YouTube': {'www.youtube.com', 'youtube.com', 'youtu.be'},
    'Instagram': {'www.instagram.com', 'instagram.com'},
    'TikTok': {'www.tiktok.com', 'tiktok.com'},
}
SOURCE_HOSTS = set().union(*PLATFORM_HOSTS.values()) | {'podcasts.apple.com', 'ahli.com', 'www.ahli.com'}
GUIDES = {'adults', 'assessment', 'assessment-in-jordan', 'children-and-teens', 'care-options', 'sleep-and-routines'}
FEATURES = {'bbc-extra-nabil-2024', 'alarabiya-jordan-nabil-2024', 'ahlihub-lets-talk-adhd-2024'}
KINDS = {'interview', 'workshop', 'video', 'short'}


def resource_key(url):
    """Catch duplicate recordings linked through different same-platform URLs.

    Crossposts on different platforms are intentionally distinct video links.
    """
    p = urlsplit(url)
    host = (p.hostname or '').lower()
    if host in PLATFORM_HOSTS['YouTube']:
        if host == 'youtu.be':
            ident = p.path.strip('/').split('/')[0]
        elif p.path.startswith(('/shorts/', '/embed/')):
            ident = p.path.strip('/').split('/')[1]
        else:
            ident = parse_qs(p.query).get('v', [''])[0]
        return ('YouTube', ident) if ident else (host, p.path)
    if host in PLATFORM_HOSTS['Instagram']:
        m = re.search(r'/(?:reel|p)/([^/]+)', p.path)
        if m:
            return ('Instagram', m.group(1))
    if host in PLATFORM_HOSTS['TikTok']:
        m = re.search(r'/video/(\d+)', p.path)
        if m:
            return ('TikTok', m.group(1))
    return (host, p.path.rstrip('/'), p.query)


class Validator:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors = []
        self.stats = collections.Counter()
        self.documents = {}
        self.data = None
        self.records = {}

    def check(self, condition, location, message):
        if not condition:
            self.errors.append(f'{location}: {message}')
        return bool(condition)

    def document(self, relative):
        if relative not in self.documents:
            p = self.root / relative
            if not self.check(p.is_file(), relative, 'Missing page'):
                return None
            self.documents[relative] = BeautifulSoup(p.read_text(), 'html.parser')
        return self.documents[relative]

    def url(self, value, hosts, where):
        p = urlsplit(value)
        self.check(p.scheme == 'https' and p.hostname in hosts and not p.username and not p.password, where,
                   'URL must use HTTPS and an approved source host: ' + value)

    def catalogue(self):
        where = 'content/media.json'
        self.data = json.loads((self.root / where).read_text())
        checked = date.fromisoformat(self.data['checked_at'])
        ids, keys = set(), set()
        for item in self.data['items']:
            id_ = item['id']
            loc = where + '#' + id_
            self.check(id_ not in ids and re.fullmatch(r'[a-z0-9][a-z0-9_-]*', id_), loc, 'Duplicate or invalid ID')
            ids.add(id_)
            key = resource_key(item['url'])
            self.check(key not in keys, loc, 'Duplicate URL or same-platform media ID')
            keys.add(key)
            self.check(item['kind'] in KINDS, loc, 'Unknown media type')
            self.url(item['url'], PLATFORM_HOSTS.get(item['platform'], set()), loc)
            for lang in ('en', 'ar'):
                self.check(bool(item.get('title', {}).get(lang)) and bool(item.get('description', {}).get(lang)), loc, 'Missing localized title or description: ' + lang)
            self.check(bool(item['sources']), loc, 'Missing source evidence')
            for source in item['sources']:
                self.url(source['url'], SOURCE_HOSTS, loc)
                self.check(bool(source['label'].strip()), loc, 'Source needs a publisher/label')
            if item.get('date'):
                published = date.fromisoformat(item['date'])
                self.check(published <= checked, loc, 'Publication date is later than the recorded check')
            if item.get('youtube_id'):
                self.check(item['platform'] == 'YouTube' and re.fullmatch(r'[A-Za-z0-9_-]{11}', item['youtube_id']), loc, 'Invalid YouTube player identifier')
                self.check(key == ('YouTube', item['youtube_id']), loc, 'Player ID differs from the cited watch URL')
            for slug in item.get('related', []):
                self.check(slug in GUIDES, loc, 'Unknown related guide: ' + slug)
            self.records[id_] = item
        self.check(FEATURES <= ids, where, 'The BBC, AlArabiya and Ahli appearances must remain available')
        ahli = self.records.get('ahlihub-lets-talk-adhd-2024')
        if ahli:
            self.check(ahli.get('date') is None, where, 'Ahli event date must not be substituted for an unconfirmed upload date')
        channels = self.data['channels']
        self.check(len({c['id'] for c in channels}) == len(channels), where, 'Duplicate channel IDs')
        self.check(len({c['url'].rstrip('/') for c in channels}) == len(channels), where, 'Duplicate channels')
        for channel in channels:
            self.url(channel['url'], PLATFORM_HOSTS.get(channel['platform'], set()), where)
        self.stats['catalogue_items'] = len(self.records)

    def media(self, lang):
        where = f'{lang}/media/index.html'
        doc = self.document(where)
        if doc is None:
            return
        self.check(doc.html.get('lang') == lang and doc.html.get('dir') == ('rtl' if lang == 'ar' else 'ltr'), where, 'Incorrect page language/direction')
        cards = doc.select('[data-media-item]')
        ids = [c.get('data-media-id') for c in cards]
        self.check(len(ids) == len(self.records) and set(ids) == set(self.records), where, 'Rendered cards must match the catalogue exactly once')
        self.check(len({x['id'] for x in doc.select('[id]')}) == len(doc.select('[id]')), where, 'Duplicate HTML IDs')
        for card in cards:
            item = self.records.get(card.get('data-media-id'))
            if not item:
                continue
            loc = where + '#' + item['id']
            self.check(not card.has_attr('hidden'), loc, 'All cards must be readable without JavaScript')
            self.check(card.get('id') == 'media-' + item['id'], loc, 'Wrong anchor ID')
            self.check(card.get('data-platform') == item['platform'] and card.get('data-kind') == item['kind'], loc, 'Filter metadata differs from the record')
            heading, description = card.find('h3'), card.select_one('.media-description')
            self.check(heading and heading.get_text() == item['title'][lang], loc, 'Title differs from reviewed record')
            self.check(description and description.get_text() == item['description'][lang], loc, 'Description differs from reviewed record')
            self.check(heading and heading.get('dir') == 'auto', loc, 'Original Arabic titles need automatic text direction')
            source_links = {a.get('href') for a in card.select('.media-sources a')}
            self.check(source_links == {s['url'] for s in item['sources']}, loc, 'Missing or substituted source evidence')
            watch = card.select_one('.media-card-actions a')
            self.check(watch and watch.get('href') == item['url'], loc, 'Missing usable external watch link')
            dates = [t.get('datetime') for t in card.select('time')]
            self.check(dates == ([item['date']] if item.get('date') else []), loc, 'Date is missing, invented or substituted')
            original = item.get('original_title')
            if original and original.strip() != item['title'][lang].strip():
                caption = card.select_one('.media-caption p')
                self.check(caption and caption.get_text() == original and caption.get('dir') == 'auto', loc, 'Original caption is missing, altered or lacks correct direction')
            button = card.select_one('[data-video-load]')
            if item.get('youtube_id'):
                stage = card.select_one('[data-video-player]')
                self.check(button and button.get('data-youtube-id') == item['youtube_id'], loc, 'Play control targets the wrong video')
                self.check(button and stage and button.get('aria-controls') == stage.get('id') and button.get('aria-label'), loc, 'Play control needs an accessible name and correct container')
            else:
                self.check(button is None, loc, 'Non-YouTube item cannot load a YouTube player')
            for slug in item.get('related', []):
                self.check(card.find('a', href=f'/{lang}/learn/{slug}/'), loc, 'Missing relevant guide link: ' + slug)
        for attr in ['data-media-search', 'data-media-platform', 'data-media-kind', 'data-media-clear', 'data-media-status', 'data-media-empty']:
            self.check(len(doc.select('[' + attr + ']')) == 1, where, 'Missing or duplicated control: ' + attr)
        status = doc.select_one('[data-media-status]')
        self.check(status and status.get('aria-live') == 'polite', where, 'Filter results need an accessible live count')
        for selector, key in [('[data-media-platform]', 'platform'), ('[data-media-kind]', 'kind')]:
            control = doc.select_one(selector)
            if control:
                options = {o.get('value') for o in control.select('option') if o.get('value')}
                self.check(options == {r[key] for r in self.records.values()}, where, 'Filter options do not cover the collected records: ' + key)
        featured = {a.get('href', '').removeprefix('#media-') for a in doc.select('.media-feature')}
        self.check(FEATURES <= featured, where, 'Expected interviews/workshop missing from featured links')
        channels = {a.get('href') for a in doc.select('.media-channel')}
        self.check(channels == {c['url'] for c in self.data['channels']}, where, 'Official channel links missing or substituted')
        self.check(not doc.select('iframe, object, embed, .ad-section, ins.adsbygoogle'), where, 'A player or ad placement is preloaded')
        for node in doc.select('[src], [poster], [srcset]'):
            for attr in ('src', 'poster', 'srcset'):
                if node.has_attr(attr):
                    self.check(not re.search(r'(?:https?:)?//', node[attr]), where, 'Third-party media or script is preloaded: ' + node[attr])
            if node.name == 'script':
                self.check(not re.search(r'adsbygoogle|ads-privacy', node.get('src', '')), where, 'Advertising loader on media page')
        for node in doc.select('link[href]'):
            rel = set(node.get('rel', []))
            if rel & {'preload', 'prefetch', 'preconnect', 'dns-prefetch'}:
                self.check(not node['href'].startswith(('https://', 'http://', '//')), where, 'Third-party connection is warmed before consent/play')
        css = (self.root / 'assets/css/media.css').read_text()
        self.check(not re.search(r'url\(\s*[\"\x27]?(?:https?:)?//|@import', css, re.I), 'assets/css/media.css', 'Remote media must not be loaded through CSS')
        schemas = [json.loads(s.string or s.get_text()) for s in doc.select('script[type="application/ld+json"]')]
        lists = [s for s in schemas if s.get('@type') == 'ItemList']
        self.check(len(lists) == 1, where, 'Expected one collection ItemList')
        self.check('VideoObject' not in json.dumps(schemas), where, 'Do not fabricate video-specific structured metadata')
        if lists:
            entries = lists[0].get('itemListElement', [])
            self.check(lists[0].get('numberOfItems') == len(self.records) and len(entries) == len(self.records), where, 'Structured collection count differs from actual links')
            self.check({(x.get('url'), x.get('name')) for x in entries} == {(x['url'], x['title'][lang]) for x in self.records.values()}, where, 'Structured list contains invented or missing records')
        context = doc.select_one('.media-context')
        self.check(context and ('not a medical endorsement' in context.get_text() if lang == 'en' else 'ليست اعتماداً طبياً' in context.get_text()), where, 'Missing distinction between appearances and clinical endorsement')
        self.stats[lang + '_cards'] = len(cards)

    def integrations(self, lang):
        route = f'/{lang}/media/'
        for file in sorted((self.root / lang).rglob('index.html')):
            where = str(file.relative_to(self.root))
            doc = self.document(where)
            if doc.find('meta', attrs={'http-equiv': re.compile('refresh', re.I)}):
                continue
            canonical = doc.select_one('link[rel="canonical"]')
            if not canonical or canonical['href'] != ORIGIN + '/' + where.removesuffix('index.html'):
                continue
            self.check(len(doc.select('.main-nav a[href="' + route + '"]')) == 1, where, 'Canonical page must have one media navigation link')
            self.check(doc.select_one('.site-footer a[href="' + route + '"]'), where, 'Footer media link missing')
            self.stats['canonical_pages_with_media_navigation'] += 1
        home = self.document(f'{lang}/index.html')
        block = home.select_one('[data-media-home]')
        self.check(block, f'{lang}/index.html', 'Missing homepage media introduction')
        if block:
            links = {a.get('href') for a in block.select('a[href]')}
            self.check({route + '#media-' + id_ for id_ in FEATURES} <= links, f'{lang}/index.html', 'Homepage lacks the three requested appearances')
        for slug in GUIDES:
            where = f'{lang}/learn/{slug}/index.html'
            doc = self.document(where)
            block = doc.select_one('[data-media-related]') if doc else None
            self.check(block and block.select('a[href]'), where, 'Missing related media links')
            if block:
                for anchor in block.select('a[href]'):
                    href = anchor['href']
                    id_ = href.removeprefix(route + '#media-')
                    self.check(id_ in self.records and slug in self.records.get(id_, {}).get('related', []), where, 'Media link is missing or unrelated: ' + href)
        about = self.document(f'{lang}/about/index.html')
        block = about.select_one('[data-media-about]')
        self.check(block and block.find('a', href=route), f'{lang}/about/index.html', 'About page must connect the named owner’s appearances')
        privacy = self.document(f'{lang}/privacy/index.html')
        block = privacy.select_one('[data-media-privacy]')
        where = f'{lang}/privacy/index.html'
        self.check(block, where, 'Missing optional-player privacy disclosure')
        if block:
            copy = block.get_text(' ', strip=True)
            required = ('YouTube', 'Instagram', 'TikTok', 'youtube-nocookie.com', 'IP')
            self.check(all(term in copy for term in required), where, 'Disclosure must identify platforms, player host and IP sharing')
            self.check(('Choosing “Play here”' in copy and 'does not erase' in copy) if lang == 'en' else ('عند اختيار' in copy and 'دون أن يمحو' in copy), where, 'Disclosure must describe click-to-load and limits of closing the player')
            self.check(block.find('a', href='https://policies.google.com/privacy'), where, 'Missing player-provider privacy policy')
        old = 'They are links, not embedded trackers.' if lang == 'en' else 'هي روابط وليست أدوات تتبع مضمّنة.'
        self.check(old not in privacy.get_text(), where, 'Old blanket no-embeds claim contradicts the new optional player')

    def run(self):
        self.catalogue()
        for lang in ('en', 'ar'):
            self.media(lang)
            self.integrations(lang)
        return self.errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    validator = Validator(args.root)
    try:
        errors = validator.run()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('FAIL: invalid media data or missing build: ' + str(exc))
        return 1
    if errors:
        print('\n'.join('FAIL: ' + error for error in errors))
        print(f'{len(errors)} media validation errors.')
        return 1
    print('PASS: ' + json.dumps(dict(validator.stats), ensure_ascii=False))
    print('Reviewed catalogue provenance, bilingual records/dates, click-to-load privacy, channels, navigation, guide links and disclosures.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
