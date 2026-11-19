"""Generate the bilingual annotated source catalogue after remediate.py.

Only the two sources/index.html files are written. The source catalogue is
versioned JSON and needs no network calls during generation.
"""
import json
import sys
from html import escape
from pathlib import Path

sys.dont_write_bytecode = True
from remediate import ROOT, page, load, save, link, para


def build_sources():
    data = json.loads((ROOT / 'content/source-catalogue.json').read_text())
    groups = data['groups']
    records = data['sources']
    group_ids = {group['id'] for group in groups}
    source_ids = [record['id'] for record in records]
    assert len(source_ids) == len(set(source_ids)), 'Duplicate source ID'
    assert all(record['group'] in group_ids for record in records)
    assert all(record['url'].startswith('https://') for record in records)
    assert all(record['checked_on'] == data['checked_on'] for record in records)
    allowed_status = {'direct_page_retrieved',
                      'official_indexed_content_confirmed_direct_fetch_403'}
    assert all(record['check_status'] in allowed_status for record in records)

    for lang in ('en', 'ar'):
        ui = data[lang]
        toc = '<nav class="article-toc" aria-label="' + escape(ui['group_label'], quote=True) + '">'
        toc += '<strong>' + escape(ui['group_label']) + '</strong>'
        toc += ''.join(link('#' + group['id'], group[lang]['title']) for group in groups)
        toc += '</nav>'
        body = '<div class="article-body">'
        body += '<div class="notice">' + para(ui['review_note'])
        body += para(ui['translation_note'])
        body += '<p>' + link('/' + lang + '/editorial/', ui['editorial_link']) + '</p></div>'
        for group in groups:
            body += '<section id="' + escape(group['id'], quote=True) + '">'
            body += '<h2>' + escape(group[lang]['title']) + '</h2>'
            body += para(group[lang]['intro'])
            for source in (record for record in records if record['group'] == group['id']):
                label = source[lang]
                body += '<section class="overview" id="' + escape(source['id'], quote=True) + '">'
                body += '<h3>' + link(source['url'], label['title']) + '</h3>'
                body += '<p class="small muted"><bdi>' + escape(source['publisher']) + '</bdi>'
                body += ' · ' + escape(ui['region_labels'][source['region']]) + '</p>'
                body += para(label['note'])
                if source['check_status'] != 'direct_page_retrieved':
                    body += '<p class="small">' + escape(ui['nice_check_note']) + '</p>'
                body += '</section>'
            body += '</section>'
        body += '<aside class="notice">' + para(ui['directory_note'])
        body += '<p>' + link('/' + lang + '/support/methodology/', ui['directory_link']) + '</p></aside>'
        body += '</div>'
        markup = '<section class="section"><div class="wrap article-layout">' + toc + body + '</div></section>'
        route = lang + '/sources'
        page(lang, route, ui['title'], ui['intro'], markup)
        # Keep this generated page correct whether run alone or after the main builder.
        document = load(route + '/index.html')
        bottom = document.select_one('.footer-bottom')
        if bottom:
            spans = bottom.find_all('span', recursive=False)
            if spans:
                spans[-1].string = ('Updated 19 November 2026' if lang == 'en'
                                    else '\u062d\u064f\u062f\u0651\u062b \u0641\u064a 19 \u0646\u0648\u0641\u0645\u0628\u0631 2026')
        save(document, route + '/index.html')
    print('Generated two annotated Sources pages with ' + str(len(records)) + ' references.')


if __name__ == '__main__':
    build_sources()
