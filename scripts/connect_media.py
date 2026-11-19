"""Connect the media hub to navigation, guides, ownership and privacy pages.

Run after scripts/media.py. Safe to rerun; all generated blocks are marked.
"""
import json
from remediate import ROOT, e, link, load, para, save, sitemap, soup


def integrate():
    data = json.loads((ROOT/'content/media.json').read_text())
    items = {item['id']: item for item in data['items']}
    guide_items = {
        'adults': ['bbc-extra-nabil-2024', 'warsheh-nabil-adhd-2024'],
        'assessment': ['warsheh-nabil-adhd-2024'],
        'assessment-in-jordan': ['ahlihub-lets-talk-adhd-2024'],
        'children-and-teens': ['tt-7648332689182838036'],
        'care-options': ['yt-sx-2mr5aa6a'],
        'sleep-and-routines': ['ig-dvrehpedjur', 'tt-7637039192026959124'],
    }
    for lang in ('en', 'ar'):
        ar = lang == 'ar'
        media_url = '/'+lang+'/media/'
        media_label = 'فيديوهات ومقابلات' if ar else 'Videos & interviews'
        for file in sorted((ROOT/lang).rglob('index.html')):
            rel = str(file.relative_to(ROOT)); doc = load(rel)
            if doc.find('meta', attrs={'http-equiv':'refresh'}): continue
            for parent in [doc.select_one('.main-nav'), doc.select_one('.footer-links')]:
                if parent:
                    for old in parent.find_all('a',href=media_url): old.decompose()
                    markup = soup(link(media_url, media_label))
                    if parent.has_attr('class') and 'main-nav' in parent['class']:
                        about = parent.find('a', href='/'+lang+'/about/')
                        if about: about.insert_before(markup)
                        else: parent.append(markup)
                    else: parent.append(markup)
            if rel == lang+'/media/index.html':
                doc.select_one('.main-nav a[href="'+media_url+'"]').attrs['aria-current']='page'
            save(doc,rel)
        # Put the owner's original conversations near the top of each homepage.
        rel = lang+'/index.html'; doc = load(rel)
        for old in doc.select('[data-media-home]'):old.decompose()
        heading = 'شاهد نبيل في المقابلات وورش العمل' if ar else 'Watch Nabil’s interviews and workshops'
        intro = 'تجارب وحوارات من بي بي سي والعربية وورشة البنك الأهلي، مع مقاطع من ADHDJO.' if ar else 'Conversations from BBC Arabic, Al Arabiya and the Ahli workshop, alongside ADHDJO videos.'
        body = '<section class="section band" data-media-home><div class="wrap"><div class="section-head"><div><span class="kicker">ADHDJO · '+('أصوات وتجارب' if ar else 'Voices & experience')+'</span><h2>'+heading+'</h2>'+para(intro)+'</div>'+link(media_url,'تصفّح كل روابط الفيديو' if ar else 'Browse all video links')+'</div><div class="grid">'
        for id_ in ['bbc-extra-nabil-2024','alarabiya-jordan-nabil-2024','ahlihub-lets-talk-adhd-2024']:
            item=items[id_]
            body += '<article class="card"><h3>'+e(item['title'][lang])+'</h3>'+para(item['description'][lang])+'<p>'+link(media_url+'#media-'+id_, 'شاهد الحوار' if ar else 'Watch the conversation')+'</p></article>'
        body += '</div></div></section>'
        anchor=doc.select_one('[data-jordan-guide]') or doc.main.find('section')
        anchor.insert_after(soup(body)); save(doc,rel)
        # Personal stories have an explicit context, alongside the evidence-based guides.
        for slug,ids in guide_items.items():
            rel=f'{lang}/learn/{slug}/index.html';doc=load(rel)
            for old in doc.select('[data-media-related]'):old.decompose()
            body='<aside class="notice" data-media-related><h2>'+('شاهد تجربة شخصية' if ar else 'Watch a personal perspective')+'</h2>'
            body+=para('تضيف هذه المقاطع صوتاً شخصياً للموضوع؛ المعلومات والمصادر في هذا الدليل تقدم الخلفية الأوسع.' if ar else 'These clips add a personal voice to the topic; this guide and its sources provide broader background.')
            body+='<ul>'+''.join('<li>'+link(media_url+'#media-'+id_,items[id_]['title'][lang])+'</li>' for id_ in ids)+'</ul></aside>'
            article=doc.select_one('.article-body');related=article.select_one('.related')
            if related:related.insert_before(soup(body))
            else:article.append(soup(body))
            save(doc,rel)
        # Keep ownership and the media archive connected.
        rel=f'{lang}/about/index.html';doc=load(rel)
        for old in doc.select('[data-media-about]'):old.decompose()
        target=doc.select_one('.article-body') or doc.select_one('.wrap.prose') or doc.main
        target.append(soup('<section data-media-about><h2>'+('حوارات نبيل ومشاركاته' if ar else 'Nabil’s conversations and appearances')+'</h2>'+para('شارك نبيل في حوارات لبي بي سي عربي والعربية الأردن وبودكاست ورشة، وفي ورشة ADHD لدى البنك الأهلي الأردني. تجمع مكتبة الفيديو هذه التسجيلات ومقاطع من قنواته.' if ar else 'Nabil has appeared with BBC Arabic, AlArabiya Jordan and Warsheh Podcast, and in an ADHD workshop hosted by Jordan Ahli Bank. The media library brings these recordings and clips from his channels together.')+'<p>'+link(media_url,media_label)+'</p></section>'))
        save(doc,rel)
        # Disclose the real behavior of click-to-load players.
        rel=f'{lang}/privacy/index.html';doc=load(rel)
        old_copy='هي روابط وليست أدوات تتبع مضمّنة.' if ar else 'They are links, not embedded trackers.'
        new_copy='الروابط الخارجية وحدها لا تحمّل مشغلات مضمّنة؛ ترد أدناه تفاصيل مشغلات الفيديو الاختيارية.' if ar else 'External links alone do not load embedded players; optional video players are described below.'
        for node in doc.find_all(string=True):
            if old_copy in str(node):node.replace_with(str(node).replace(old_copy,new_copy))
        for old in doc.select('[data-media-privacy]'):old.decompose()
        body='<section data-media-privacy><h2>'+('الفيديوهات والمنصات الخارجية' if ar else 'Videos and external platforms')+'</h2>'+para('تعرض مكتبة الفيديو روابط إلى YouTube وInstagram وTikTok. لا تحمّل صوراً أو مشغلات من تلك المنصات عند فتح الصفحة. عند اختيار «شغّل هنا» يُحمّل مشغّل YouTube من نطاق youtube-nocookie.com؛ وقد تتلقى Google عنوان IP ومعلومات المتصفح والصفحة وبيانات التفاعل مع المشغّل وفق سياستها. هذا ليس وعداً بعدم جمع البيانات. يمكنك إغلاق المشغّل لإيقاف تحميله على الصفحة، دون أن يمحو ذلك بيانات سبق إرسالها. تفتح روابط المشاهدة الخارجية المنصة المعنية وتخضع لسياساتها.' if ar else 'The media library links to YouTube, Instagram and TikTok. It loads no images or players from those platforms when the page opens. Choosing “Play here” loads a YouTube player from youtube-nocookie.com; Google may receive your IP address, browser and page information, and interactions with the player under its policy. This does not mean no data is collected. Closing the player removes it from the page but does not erase data already sent. External watch links open the relevant platform under its own policies.')+'<p>'+link('https://policies.google.com/privacy','سياسة خصوصية Google' if ar else 'Google privacy policy')+' · '+link('https://www.tiktok.com/legal/page/row/privacy-policy/en','خصوصية TikTok' if ar else 'TikTok privacy policy')+'</p></section>'
        heading=doc.find('h2',string='الإعلانات وخيارات الخصوصية' if ar else 'Advertising and privacy choices')
        if heading:heading.insert_before(soup(body))
        else:doc.main.append(soup(body))
        save(doc,rel)
    # Keep the language landing page useful without adding an embedded service.
    doc=load('index.html')
    for old in doc.select('[data-media-landing]'):old.decompose()
    doc.main.append(soup('<div class="wrap" data-media-landing><p>'+link('/en/media/','Videos & interviews')+' · '+link('/ar/media/','فيديوهات ومقابلات')+'</p></div>'))
    save(doc,'index.html')
    sitemap()
    print('Connected media across navigation, homepages, six bilingual guides, About and Privacy.')


if __name__ == '__main__':
    integrate()
