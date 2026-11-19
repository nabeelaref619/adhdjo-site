"""Build the English and Arabic media hub from content/media.json.

Run after the main content generators. This module does not change global
navigation, privacy copy, shared assets or other pages. It never fetches media.
"""
import json
import re
from datetime import date

from remediate import ROOT, ORIGIN, e, link, load, page, save


VERSION = '20261119-media2'
KINDS = {
    'interview': {'en': 'Interview', 'ar': 'مقابلة'},
    'workshop': {'en': 'Workshop', 'ar': 'ورشة عمل'},
    'video': {'en': 'Video', 'ar': 'فيديو'},
    'short': {'en': 'Short video', 'ar': 'فيديو قصير'},
}
GROUPS = {
    'interview': {'en': 'Interviews & conversations', 'ar': 'مقابلات وحوارات'},
    'workshop': {'en': 'Workshops & events', 'ar': 'ورش عمل وفعاليات'},
    'video': {'en': 'Videos', 'ar': 'فيديوهات'},
    'short': {'en': 'Short videos', 'ar': 'فيديوهات قصيرة'},
}
GUIDES = {
    'adults': {'en': 'ADHD in adult life', 'ar': 'ADHD في حياة البالغين'},
    'children-and-teens': {'en': 'Children and teenagers', 'ar': 'الأطفال والمراهقون'},
    'assessment': {'en': 'Understanding assessment', 'ar': 'فهم التقييم'},
    'assessment-in-jordan': {'en': 'Getting assessed in Jordan', 'ar': 'بدء التقييم في الأردن'},
    'care-options': {'en': 'Care and treatment options', 'ar': 'خيارات الرعاية والعلاج'},
    'sleep-and-routines': {'en': 'Sleep and everyday routines', 'ar': 'النوم والروتين اليومي'},
}
PLATFORMS = ('YouTube', 'Instagram', 'TikTok')


def text(item, key, lang):
    value = item.get(key, '')
    return value.get(lang, value.get('en', '')) if isinstance(value, dict) else value


def date_label(value, lang):
    if not value:
        return ''
    parsed = date.fromisoformat(value)
    months = (
        ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        if lang == 'en' else
        ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
    )
    return f'{parsed.day} {months[parsed.month - 1]} {parsed.year}'


def ordered(items):
    # Preserve editorial order within a kind; the source file controls which
    # interviews and workshops are featured first.
    return [item for kind in KINDS for item in items if item['kind'] == kind]


def arrow():
    return '<span aria-hidden="true">↗</span>'


def watch_link(item, lang, css='button secondary'):
    label = ('شاهد على ' if lang == 'ar' else 'Watch on ') + item['platform']
    return f'<a class="{e(css)}" href="{e(item["url"], quote=True)}">{e(label)} {arrow()}</a>'


def channels_section(channels, lang):
    ar = lang == 'ar'
    title = 'تابع القنوات' if ar else 'Browse the channels'
    intro = ('للمزيد من المنشورات والمقاطع، افتح القنوات الرسمية. المجموعة هنا لا تشمل كل ما نُشر.' if ar else
             'For more posts and clips, browse the official channels. This collection does not include everything published.')
    out = '<section class="media-channels" aria-labelledby="media-channels-title"><div><h2 id="media-channels-title">' + title + '</h2><p>' + intro + '</p></div><div class="media-channel-links">'
    for channel in channels:
        label = text(channel, 'label', lang)
        out += f'<a class="media-channel" href="{e(channel["url"], quote=True)}"><span class="media-channel-platform" dir="ltr">{e(channel["platform"])}</span><span dir="auto">{e(label)}</span>{arrow()}</a>'
    return out + '</div></section>'


def featured(items, lang):
    # Keep cards distinct from the searchable inventory: these are shortcuts to
    # the full entries, not duplicate playable videos or duplicate search hits.
    interviews = [item for item in items if item['kind'] == 'interview']
    workshops = [item for item in items if item['kind'] == 'workshop']
    choices = interviews[:2] + workshops[:1]
    choices += [item for item in interviews + workshops if item not in choices][:3 - len(choices)]
    if not choices:
        return ''
    ar = lang == 'ar'
    out = '<section class="media-featured" aria-labelledby="media-featured-title"><div class="section-head"><div><span class="kicker">' + ('ابدأ من هنا' if ar else 'Start here') + '</span><h2 id="media-featured-title">' + ('أصوات وتجارب وحوارات' if ar else 'Stories, conversations & shared experience') + '</h2></div></div><div class="media-feature-grid">'
    for item in choices:
        out += f'<a class="media-feature" href="#media-{e(item["id"], quote=True)}"><span class="media-feature-top"><span>{e(KINDS[item["kind"]][lang])}</span><span aria-hidden="true">↘</span></span><h3 dir="auto">{e(text(item,"title",lang))}</h3>'
        out += '<p>' + e(text(item, 'description', lang)) + '</p><span class="media-feature-action">' + ('انتقل إلى المقطع' if ar else 'Explore this appearance') + '</span></a>'
    return out + '</div></section>'


def filters(items, lang):
    ar = lang == 'ar'
    out = '<div class="media-filter-panel"><div class="media-filters">'
    label = 'ابحث عن عنوان أو موضوع' if ar else 'Search a title or topic'
    out += f'<div class="field"><label for="media-search">{label}</label><input id="media-search" type="search" data-media-search placeholder="{label}" /></div>'
    out += '<div class="field"><label for="media-platform">' + ('المنصة' if ar else 'Platform') + '</label><select id="media-platform" data-media-platform><option value="">' + ('كل المنصات' if ar else 'All platforms') + '</option>'
    for platform in PLATFORMS:
        if any(item['platform'] == platform for item in items):
            out += f'<option value="{platform}">{platform}</option>'
    out += '</select></div><div class="field"><label for="media-kind">' + ('نوع المقطع' if ar else 'Type') + '</label><select id="media-kind" data-media-kind><option value="">' + ('كل الأنواع' if ar else 'All types') + '</option>'
    for kind, labels in KINDS.items():
        if any(item['kind'] == kind for item in items):
            out += f'<option value="{kind}">{labels[lang]}</option>'
    out += '</select></div></div><div class="media-filter-footer"><p class="filter-status" data-media-status role="status" aria-live="polite">'
    out += (f'{len(items)} روابط فيديو في المجموعة' if ar else f'{len(items)} video links in this collection')
    out += '</p><button type="button" class="media-clear" data-media-clear>' + ('مسح الفلاتر' if ar else 'Clear filters') + '</button></div></div>'
    out += '<div class="empty media-empty" data-media-empty hidden><h3>' + ('لا توجد نتائج مطابقة' if ar else 'No matching videos') + '</h3><p>' + ('جرّب عبارة أقصر أو اختر كل المنصات والأنواع.' if ar else 'Try a shorter search or choose all platforms and types.') + '</p></div>'
    return out


def card(item, lang):
    ar = lang == 'ar'
    id_ = e(item['id'], quote=True)
    title = text(item, 'title', lang)
    description = text(item, 'description', lang)
    searchable = ' '.join(filter(None, [text(item, 'title', 'en'), text(item, 'title', 'ar'), text(item, 'description', 'en'), text(item, 'description', 'ar'), item.get('original_title', ''), item['platform'], *[source['label'] for source in item['sources']]]))
    out = f'<article id="media-{id_}" class="media-card" data-media-item data-media-id="{id_}" data-platform="{e(item["platform"])}" data-kind="{e(item["kind"])}" data-search="{e(searchable, quote=True)}" aria-labelledby="title-{id_}">'
    out += f'<div class="media-stage" id="player-{id_}" data-video-player><span class="media-stage-platform" dir="ltr">{e(item["platform"])}</span>'
    out += '<span class="media-stage-mark" aria-hidden="true">' + ('◌' if item['kind'] == 'workshop' else '▷') + '</span>'
    out += '<span class="media-stage-kind">' + e(KINDS[item['kind']][lang]) + '</span>'
    if item.get('youtube_id'):
        play = 'شغّل هنا' if ar else 'Play here'
        out += f'<button type="button" class="media-play" data-video-load data-youtube-id="{e(item["youtube_id"])}" data-video-title="{e(title, quote=True)}" aria-controls="player-{id_}" aria-label="{e(play+": "+title, quote=True)}"><span aria-hidden="true">▶</span>{play}</button>'
    else:
        label = ('شاهد على ' if ar else 'Watch on ') + item['platform']
        out += f'<a class="media-stage-link" href="{e(item["url"], quote=True)}">{e(label)} {arrow()}</a>'
    out += '</div><div class="media-card-body"><div class="media-card-meta"><span class="tag rose">' + e(KINDS[item['kind']][lang]) + '</span>'
    if item.get('date'):
        out += f'<time datetime="{e(item["date"])}">{date_label(item["date"], lang)}</time>'
    if item.get('language'):
        language = {'ar': 'العربية' if ar else 'Arabic', 'Arabic': 'العربية' if ar else 'Arabic', 'en': 'الإنجليزية' if ar else 'English', 'English': 'الإنجليزية' if ar else 'English'}.get(item['language'], item['language'])
        out += '<span>' + e(language) + '</span>'
    out += f'</div><h3 id="title-{id_}" dir="auto">{e(title)}</h3><p class="media-description">{e(description)}</p>'
    original = item.get('original_title')
    if original and original.strip() != title.strip():
        out += '<details class="media-caption"><summary>' + ('العنوان أو الوصف الأصلي' if ar else 'Original title or caption') + '</summary><p dir="auto">' + e(original) + '</p></details>'
    if item.get('youtube_id'):
        out += '<p class="media-play-note">' + ('لا يتصل المشغّل بـ YouTube إلا عند اختيار «شغّل هنا».' if ar else 'The player connects to YouTube only when you choose “Play here”.') + '</p>'
    out += '<div class="media-card-actions">' + watch_link(item, lang) + '</div>'
    if item.get('related'):
        related = [slug for slug in item['related'] if slug in GUIDES]
        if related:
            out += '<div class="media-related"><span>' + ('اقرأ أيضاً' if ar else 'Read alongside') + '</span><ul>'
            out += ''.join('<li>' + link('/' + lang + '/learn/' + slug + '/', GUIDES[slug][lang]) + '</li>' for slug in related)
            out += '</ul></div>'
    out += '<div class="media-sources"><span>' + ('المصدر' if len(item['sources']) == 1 and ar else 'المصادر' if ar else 'Source' if len(item['sources']) == 1 else 'Sources') + ': </span>'
    out += ' · '.join(f'<a href="{e(source["url"], quote=True)}" dir="auto">{e(source["label"])}</a>' for source in item['sources'])
    return out + '</div></div></article>'


def render(lang, data):
    ar = lang == 'ar'
    items = ordered(data['items'])
    title = 'فيديوهات ومقابلات' if ar else 'Videos & interviews'
    intro = ('مقابلات وورش عمل ومقاطع من ADHDJO عن فرط الحركة وتشتت الانتباه والحياة اليومية. شاهد الحوار، ثم اختر ما تريد قراءته أو تجربته.' if ar else
             'Interviews, workshops and ADHDJO videos about ADHD and everyday life. Watch a conversation, then choose what to read or try next.')
    body = '<div class="wrap media-hub">' + featured(items, lang)
    body += '<section class="media-library" id="media-library" data-media-library aria-labelledby="media-library-title"><div class="section-head"><div><span class="kicker">' + ('تصفّح المجموعة' if ar else 'Explore the collection') + '</span><h2 id="media-library-title">' + ('مجموعة فيديوهات وظهورات إعلامية' if ar else 'Collected videos and appearances') + '</h2><p class="muted">' + ('ابحث بالعربية أو الإنجليزية، أو اختر المنصة ونوع المقطع. قد يتكرر التسجيل نفسه على أكثر من منصة.' if ar else 'Search in Arabic or English, or choose a platform and format. Some links show the same recording on different platforms.') + '</p></div></div>'
    body += filters(items, lang)
    for kind, labels in GROUPS.items():
        group = [item for item in items if item['kind'] == kind]
        if not group:
            continue
        body += f'<section class="media-group" data-media-group data-group-kind="{kind}" aria-labelledby="media-group-{kind}"><h3 class="media-group-title" id="media-group-{kind}" data-media-group-title>{labels[lang]}</h3><div class="media-grid">'
        body += ''.join(card(item, lang) for item in group) + '</div></section>'
    body += '<noscript><p class="no-js">' + ('جميع المقاطع وروابط مشاهدتها متاحة هنا. يحتاج البحث والتشغيل داخل الصفحة إلى JavaScript.' if ar else 'All videos and watch links are available here. Search and playback within this page need JavaScript.') + '</p></noscript></section>'
    body += channels_section(data['channels'], lang)
    body += '<aside class="media-context"><h2>' + ('تجارب وحوارات، مع مساحة للتفكير' if ar else 'Experiences and conversations, with context') + '</h2><p>'
    body += ('تشارك هذه المقاطع تجارب وحوارات توعوية؛ لا تُعد تقييماً لحالتك أو توصية بعلاج. استضافة شخص في مقابلة أو ورشة ليست اعتماداً طبياً له. للمعلومات السريرية، راجع الأدلة ومصادرها وتحدث مع مختص مناسب.' if ar else 'These videos share experiences and public conversations; they do not assess your symptoms or recommend a treatment. An interview or workshop appearance is not a medical endorsement. For clinical information, use the linked guides and their sources and speak with an appropriate professional.')
    body += '</p><p>' + link('/' + lang + '/learn/', 'اقرأ الأدلة' if ar else 'Read the guides') + ' · ' + link('/' + lang + '/privacy/', 'الخصوصية والمشاهدة الخارجية' if ar else 'Privacy and external services') + '</p><p class="small muted">'
    body += ('آخر مراجعة لروابط المجموعة: ' if ar else 'Collection links last checked: ') + f'<time datetime="{e(data["checked_at"])}">{date_label(data["checked_at"], lang)}</time>. '
    body += ('قد تتغير إتاحة المقاطع على منصاتها.' if ar else 'Availability on each platform can change.')
    body += '</p></aside></div>'
    path = lang + '/media'
    page(lang, path, title, intro, body, ads=False)
    doc = load(path + '/index.html')
    # Keep the common site shell and add only page-specific assets and metadata.
    for existing in doc.select('link[href*="/assets/css/media.css"], script[src*="/assets/js/media.js"]'):
        existing.decompose()
    css = doc.new_tag('link', rel='stylesheet', href=f'/assets/css/media.css?v={VERSION}')
    doc.head.append(css)
    script = doc.new_tag('script', src=f'/assets/js/media.js?v={VERSION}', defer='')
    doc.head.append(script)
    itemlist = {
        '@context': 'https://schema.org', '@type': 'ItemList',
        'name': title, 'url': ORIGIN + '/' + path + '/',
        'numberOfItems': len(items), 'itemListOrder': 'https://schema.org/ItemListUnordered',
        'itemListElement': [{'@type': 'ListItem', 'position': n, 'name': text(item, 'title', lang), 'url': item['url']} for n, item in enumerate(items, 1)],
    }
    schema = doc.new_tag('script', type='application/ld+json')
    schema.string = json.dumps(itemlist, ensure_ascii=False).replace('</', '<\\/')
    doc.head.append(schema)
    save(doc, path + '/index.html')


def validate(data):
    date.fromisoformat(data['checked_at'])
    ids = set()
    for item in data['items']:
        id_ = item['id']
        if id_ in ids or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', id_):
            raise ValueError('Each media item needs a unique, URL-safe ID')
        ids.add(id_)
        if item['kind'] not in KINDS or item['platform'] not in PLATFORMS:
            raise ValueError('Unsupported media format or platform: ' + id_)
        if not item['sources'] or not item['url'].startswith('https://'):
            raise ValueError('Every item needs a source and HTTPS watch URL: ' + id_)
        if not all(text(item, 'title', lang) and text(item, 'description', lang) for lang in ('en', 'ar')):
            raise ValueError('Both languages need a title and description: ' + id_)
        if item.get('youtube_id') and not re.fullmatch(r'[A-Za-z0-9_-]{11}', item['youtube_id']):
            raise ValueError('Invalid YouTube ID: ' + id_)
        if item.get('date'):
            date.fromisoformat(item['date'])


def main():
    data = json.loads((ROOT / 'content/media.json').read_text())
    validate(data)
    for lang in ('en', 'ar'):
        render(lang, data)
    print(f'Rendered bilingual media hub with {len(data["items"])} collected items.')


if __name__ == '__main__':
    main()
