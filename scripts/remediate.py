"""Build the 2026-11-19 content revision. Run from the repository root.

Requires beautifulsoup4. Content is local, versioned JSON; no network or AI calls.
"""
import copy
import json
import re
from datetime import date
from html import escape as e
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://adhdjo.org'
DAY = '2026-11-19'
TEMPLATES = {}


def soup(text):
    return BeautifulSoup(text, 'html.parser')


def load(path):
    return soup((ROOT / path).read_text())


def absolute_links(doc, path):
    base = ORIGIN + '/' + path
    for tag in doc.select('[href], [src]'):
        attr = 'href' if tag.has_attr('href') else 'src'
        value = tag[attr]
        if tag.name=='link' and any(r in tag.get('rel',[]) for r in ('canonical','alternate')):
            tag[attr]=urljoin(base,value)
            continue
        if not value or value.startswith(('#', 'mailto:', 'tel:', 'data:')):
            continue
        resolved = urljoin(base, value)
        if resolved.startswith(ORIGIN + '/'):
            tag[attr] = resolved[len(ORIGIN):]


for lang in ('en', 'ar'):
    TEMPLATES[lang] = load(f'{lang}/about/index.html')
    absolute_links(TEMPLATES[lang], f'{lang}/about/index.html')
AD_TEMPLATE = load('en/learn/adults/index.html')
AD_SCRIPTS = [str(x) for x in AD_TEMPLATE.head.select('script')
              if 'adsbygoogle' in str(x) or 'ads-privacy.js' in str(x)]
AD_BOX = str(AD_TEMPLATE.select_one('.ad-section'))


def para(text):
    return '<p>' + e(text) + '</p>'


def link(url, text):
    return f'<a href="{e(url, quote=True)}">{e(text)}</a>'


def byline(lang):
    if lang == 'en':
        return (f'<p class="byline">Published by ADHDJO · Owner: Nabil Aref · Updated 19 November 2026.<br>'
                f'AI-assisted research, drafting and translation. Independent clinical review has not been completed. '
                f'{link("/en/editorial/", "How this content is prepared")}</p>')
    return (f'<p class="byline">نشر ADHDJO · المالك: نبيل عارف (Nabil Aref) · حُدّث في 19 نوفمبر 2026.<br>'
            f'أُعدّ البحث والصياغة والترجمة بمساعدة الذكاء الاصطناعي. لم تُجرَ مراجعة سريرية مستقلة. '
            f'{link("/ar/editorial/", "كيف نُعدّ المحتوى")}</p>')


def set_meta(doc, title, intro, path, lang, article=False):
    url = ORIGIN + '/' + path.strip('/') + '/'
    doc.title.string = title + ' — ADHDJO'
    for name, val in [('description', intro)]:
        doc.find('meta', attrs={'name': name})['content'] = val
    doc.find('link', rel='canonical')['href'] = url
    for t in doc.select('link[hreflang]'):
        t['href'] = ORIGIN + '/' + t['hreflang'] + '/' + '/'.join(path.strip('/').split('/')[1:]) + '/'
    for prop, val in [('og:title', title), ('og:description', intro), ('og:url', url), ('og:type', 'article' if article else 'website')]:
        doc.find('meta', attrs={'property': prop})['content'] = val
    for t in doc.select('script[type="application/ld+json"]'):
        t.decompose()
    data = {'@context':'https://schema.org', '@type':'Article' if article else 'WebPage',
            'name':title, 'url':url, 'inLanguage':lang, 'dateModified':DAY,
            'publisher':{'@type':'Organization','name':'ADHDJO','url':ORIGIN + '/' + lang + '/about/'}}
    if article:
        data.update(headline=title, author={'@type':'Organization','name':'ADHDJO','url':ORIGIN+'/'+lang+'/editorial/'})
    t=doc.new_tag('script', type='application/ld+json');t.string=json.dumps(data,ensure_ascii=False);doc.head.append(t)
    alt='ar' if lang=='en' else 'en'
    sw=doc.select_one('.language-switch');sw['href']='/' + alt + '/' + '/'.join(path.strip('/').split('/')[1:]) + '/'
    for a in doc.select('.main-nav a[aria-current]'): del a['aria-current']


def page(lang, path, title, intro, body, article=False, ads=False):
    doc=copy.deepcopy(TEMPLATES[lang])
    set_meta(doc,title,intro,path,lang,article)
    main=doc.find('main');main.clear()
    home='Home' if lang=='en' else 'الرئيسية'
    kicker='ADHDJO · Practical information with sources' if lang=='en' else 'ADHDJO · معلومات عملية بمصادر واضحة'
    content=f'<section class="page-head"><div class="wrap"><nav class="breadcrumb" aria-label="{home}">{link("/"+lang+"/",home)}<span>{e(title)}</span></nav><span class="kicker">{kicker}</span><h1>{e(title)}</h1><p class="lede">{e(intro)}</p></div></section>{body}'
    main.append(soup(content))
    if ads:
        for markup in AD_SCRIPTS: doc.head.append(soup(markup))
        box=soup(AD_BOX)
        if lang=='ar':
            box.aside['aria-label']='إعلان';box.select_one('.ad-label').string='إعلان'
        main.append(box)
    save(doc,path + '/index.html')


def save(doc,path):
    dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True)
    for tag in doc.select('script[src]'):
        if tag['src'].split('?')[0].endswith('/assets/js/app.js'):
            tag['src']='/assets/js/app.js?v=20261119'
    for tag in doc.select('link[rel="stylesheet"]'):
        if tag['href'].split('?')[0].endswith('/assets/css/site.css'):
            tag['href']='/assets/css/site.css?v=20261119'
    dest.write_text(str(doc).strip()+'\n')


def blocks(sections, lang, sources=None):
    result=''
    sources=sources or {}
    for sec in sections:
        result+=f'<section id="{e(sec["id"])}"><h2>{e(sec["title"])}</h2>'
        result+=''.join(para(x) for x in sec.get('paragraphs',[]))
        if sec.get('bullets'): result+='<ul>'+''.join('<li>'+e(x)+'</li>' for x in sec['bullets'])+'</ul>'
        refs=[sources[x] for x in sec.get('source_ids',[]) if x in sources]
        if refs:
            result+='<p class="sources">'+('Background sources: ' if lang=='en' else 'مصادر الخلفية: ')
            result+=' · '.join(link(r['url'],r.get('title',r.get('publisher',r['id']))) for r in refs)+'</p>'
        result+='</section>'
    return result


def related(lang,current=None):
    return '<nav class="related notice" aria-label="'+('Next steps' if lang=='en' else 'الخطوات التالية')+'"><h2>'+('Choose your next step' if lang=='en' else 'اختر خطوتك التالية')+'</h2><ul>'+''.join('<li>'+link('/'+lang+'/'+path,text)+'</li>' for path,text in [
        ('learn/assessment-in-jordan/','Getting assessed in Jordan' if lang=='en' else 'بدء التقييم في الأردن'),
        ('tools/appointment-prep/','Build a private appointment checklist' if lang=='en' else 'جهّز قائمة أسئلة للموعد'),
        ('support/','Find source-checked services' if lang=='en' else 'ابحث عن خدمات راجعنا معلوماتها')] if path!=current)+'</ul></nav>'


def update_guides():
    additions=json.loads((ROOT/'content/guide-additions.json').read_text())
    for slug,langs in additions.items():
        for lang,sections in langs.items():
            path=f'{lang}/learn/{slug}/index.html';doc=load(path);absolute_links(doc,path)
            body=doc.select_one('.article-body')
            for old in body.select('[data-original-practice], .related, .byline'):old.decompose()
            for sec in sections:
                for old in doc.select(f'.article-toc a[href$="#{sec["id"]}"]'):old.decompose()
            body.insert(0,soup(byline(lang)))
            part=soup('<div data-original-practice="">'+blocks(sections,lang)+'</div>')
            if slug=='sleep-and-routines':
                part.select_one('#sleep-notes').append(soup('<p class="sources">'+link('https://www.nhs.uk/conditions/insomnia/','NHS: Insomnia')+'</p>'))
            last=body.select_one('.notice')
            if last:last.insert_before(part)
            else:body.append(part)
            body.append(soup(related(lang)))
            if slug=='care-options':
                source=body.select_one('#therapy .sources')
                if source and not source.find('a',href='https://www.nimh.nih.gov/health/publications/adhd-what-you-need-to-know'):
                    source.append(soup(' · '+link('https://www.nimh.nih.gov/health/publications/adhd-what-you-need-to-know','NIMH: ADHD in adults')))
            toc=doc.select_one('.article-toc')
            for sec in sections:toc.append(soup(link('#'+sec['id'],sec['title'])))
            for schema in doc.select('script[type="application/ld+json"]'):
                data=json.loads(schema.string);data['dateModified']=DAY;data['author']={'@type':'Organization','name':'ADHDJO','url':ORIGIN+'/'+lang+'/editorial/'};schema.string=json.dumps(data,ensure_ascii=False)
            save(doc,path)
    data=json.loads((ROOT/'content/new-guides.json').read_text())
    for guide in data['guides']:
        refs={s['id']:s for s in guide['sources']}
        for lang in ('en','ar'):
            g=guide[lang];toc='<aside class="article-toc" aria-label="'+('In this guide' if lang=='en' else 'في هذا الدليل')+'">'
            toc+=''.join(link('#'+s['id'],s['title']) for s in g['sections'])+'</aside>'
            body='<section class="section"><div class="wrap article-layout">'+toc+'<article class="article-body">'+byline(lang)+blocks(g['sections'],lang,refs)+related(lang,'learn/'+guide['slug']+'/')+'</article></div></section>'
            page(lang,lang+'/learn/'+guide['slug'],g['title'],g['intro'],body,article=True,ads=True)


def editorial_pages():
    enabout=''.join([
        '<h2>Who is responsible for ADHDJO?</h2>',
        para('ADHDJO is owned by Nabil Aref. It began as a Jordan community resource and provides Arabic and English educational guides, practical planning tools and a source-checked service directory. Nabil handles website feedback, corrections and content enquiries.'),
        '<p>'+link('mailto:naref@adhdjo.org','naref@adhdjo.org')+' · '+link('https://www.instagram.com/adhdjo/','Instagram @adhdjo')+'</p>',
        '<h2>What you can use this site for</h2>',
        para('Prepare questions for an appointment, compare what services say they offer, and try a small organizational aid. Guides combine cited background information with original checklists and clearly labelled fictional examples. They do not diagnose you, select a treatment or replace individualized care.'),
        '<h2>How the content was made</h2>',
        para('This revision used AI assistance for research, writing, translation and website development. Sources are linked beside the claims they support. Independent clinical review has not been completed. Review status is stated so readers can judge the limits of the material.'),
        '<p>'+link('/en/editorial/','Read the editorial and corrections policy')+'</p>',
        '<h2>Why the directory is selective</h2>',
        para('A useful listing needs an identifiable service, evidence for what it offers and a contact route. The former community name list has been replaced by entries that meet the published evidence criteria. An omitted name does not mean a professional is unqualified; it means we have not established enough information for a useful listing in this revision.'),
        '<p>'+link('/en/support/methodology/','How directory information is checked')+'</p>',
        '<h2>Advertising</h2>',
        para('Selected educational articles include labelled Google advertising, subject to approval and availability. An advertisement is not a recommendation of a provider, product or treatment. Tools and directory pages do not load advertising scripts. See the privacy page for Google services and consent controls.')])
    arabout=''.join([
        '<h2>من المسؤول عن ADHDJO؟</h2>',
        para('يملك الموقع نبيل عارف (Nabil Aref). بدأ كمورد مجتمعي للأردن، ويقدّم أدلة تثقيفية بالعربية والإنجليزية وأدوات تنظيمية ودليلاً للخدمات راجعنا مصادره. يتلقى نبيل ملاحظات الموقع والتصحيحات والاستفسارات المتعلقة بالمحتوى.'),
        '<p>'+link('mailto:naref@adhdjo.org','naref@adhdjo.org')+' · '+link('https://www.instagram.com/adhdjo/','Instagram @adhdjo')+'</p>',
        '<h2>كيف تستفيد من الموقع؟</h2>',
        para('يمكنك تحضير أسئلة لموعد، ومقارنة ما تعلنه الخدمات، وتجربة وسيلة تنظيمية صغيرة. تجمع الأدلة بين معلومات مسندة إلى مصادر وقوائم عملية أصلية وأمثلة افتراضية واضحة. لا تشخّص حالتك ولا تختار علاجاً لك ولا تحل محل الرعاية الفردية.'),
        '<h2>كيف أُعدّ المحتوى؟</h2>',
        para('استُخدمت مساعدة الذكاء الاصطناعي في البحث والصياغة والترجمة وتطوير الموقع في هذه المراجعة. تُربط المصادر بالمعلومات التي تدعمها. لم تُجرَ مراجعة سريرية مستقلة. نوضح حالة المراجعة حتى يعرف القارئ حدود المادة المنشورة.'),
        '<p>'+link('/ar/editorial/','اقرأ سياسة التحرير والتصحيح')+'</p>',
        '<h2>لماذا نختار معلومات الدليل بعناية؟</h2>',
        para('يحتاج الإدراج المفيد إلى خدمة محددة ودليل على ما تقدمه وطريقة للتواصل. استُبدلت قائمة الأسماء المجتمعية السابقة بإدراجات تحقق معايير الأدلة المنشورة. عدم إدراج اسم لا يعني أن صاحبه غير مؤهل؛ بل يعني أننا لم نثبت معلومات كافية لإدراج مفيد في هذه المراجعة.'),
        '<p>'+link('/ar/support/methodology/','كيف نتحقق من معلومات الخدمات')+'</p>',
        '<h2>الإعلانات</h2>',
        para('تتضمن مقالات تثقيفية مختارة إعلانات Google موضّحة، بحسب الموافقة والتوفر. الإعلان ليس توصية بمختص أو منتج أو علاج. لا تحمّل الأدوات ودليل الخدمات شيفرات إعلانية. توضح صفحة الخصوصية خدمات Google وخيارات الموافقة.')])
    editorial={
        'en':[
            ('Ownership and contact','Nabil Aref owns ADHDJO and is responsible for receiving corrections. Contact naref@adhdjo.org or @adhdjo on Instagram. This website is an educational community resource, not a healthcare provider.'),
            ('Research and authorship','AI assistance was used to locate sources, draft explanations and translate the Arabic and English text. The publisher is ADHDJO. Ownership, publication and source checking should not be mistaken for a medical qualification or independent clinical review.'),
            ('What counts as evidence','Clinical background is linked to public-health agencies, professional guidance or primary research. Overseas guidance is identified by its source; it does not establish Jordanian law, local medicine availability, eligibility or fees. Provider pages establish what a service says it offers, not its clinical quality.'),
            ('Examples, worksheets and translations','Fictional examples and original planning worksheets are clearly described. They are not patient testimonials, diagnostic tests or validated treatment programs. Arabic text is an editorial translation prepared with AI assistance, not an official translation endorsed by the cited organizations.'),
            ('Corrections','Send the page URL, the statement that needs correcting and a public primary source where possible. Do not send medical records or confidential details about another person. Reports are reviewed through the owner’s contact channels; there is no guaranteed response time. Material corrections should identify what changed and when.'),
            ('Dates and verification limits','An updated date records a content revision. A directory check date records the public evidence examined on that date. Neither confirms current appointment availability. A page is described as clinically reviewed only after a qualified reviewer has actually reviewed it and agreed to be identified.'),
            ('19 November 2026 revision','Added a Jordan assessment guide and a detailed appointment preparation guide; expanded the adult, family, care and routine guides; rechecked directory evidence and restrictions; replaced the unsupported community name list; added named ownership and a public email; removed advertising placements from overview pages and consolidated old duplicate pages.')],
        'ar':[
            ('الملكية والتواصل','يملك نبيل عارف (Nabil Aref) الموقع ويتلقى طلبات التصحيح عبر naref@adhdjo.org أو @adhdjo على Instagram. الموقع مورد مجتمعي تثقيفي وليس مقدم رعاية صحية.'),
            ('البحث وإعداد المحتوى','استُخدمت مساعدة الذكاء الاصطناعي للعثور على المصادر وصياغة الشرح وترجمة النصوص. الناشر هو ADHDJO. لا تعني الملكية أو النشر أو مراجعة المصادر وجود مؤهل طبي أو إجراء مراجعة سريرية مستقلة.'),
            ('ما الذي نعدّه دليلاً؟','تُربط الخلفية السريرية بمؤسسات الصحة العامة والإرشادات المهنية أو البحث الأصلي. تُنسب الإرشادات الأجنبية إلى مصادرها، ولا تثبت القانون الأردني أو توفر الأدوية أو شروط الاستفادة أو الرسوم. تثبت صفحة مقدم الخدمة ما يعلنه عن خدمته، لا جودته السريرية.'),
            ('الأمثلة والأوراق العملية والترجمة','تُوضَّح الأمثلة الافتراضية والأوراق التنظيمية الأصلية بصفتها كذلك. ليست شهادات مرضى أو اختبارات تشخيصية أو برامج علاجية معتمدة. العربية ترجمة تحريرية بمساعدة الذكاء الاصطناعي وليست ترجمة رسمية معتمدة من الجهات المشار إليها.'),
            ('التصحيحات','أرسل رابط الصفحة والمعلومة المطلوب تصحيحها ومصدراً أولياً علنياً إن أمكن. لا ترسل سجلات طبية أو معلومات سرية عن شخص آخر. تُراجع البلاغات عبر قنوات تواصل المالك دون وعد بمدة استجابة محددة. ينبغي بيان مضمون التصحيحات الجوهرية وتاريخها.'),
            ('التواريخ وحدود التحقق','يشير تاريخ التحديث إلى تعديل المحتوى، ويشير تاريخ فحص إدراج إلى الأدلة العامة التي راجعناها في ذلك اليوم. لا يؤكد أي منهما توفر المواعيد حالياً. لا يوصف المحتوى بأنه مُراجع سريرياً إلا بعد مراجعته فعلياً من مختص مؤهل وافق على ذكر اسمه.'),
            ('مراجعة 19 نوفمبر 2026','أُضيف دليل للتقييم في الأردن ودليل مفصّل للتحضير للموعد، ووُسّعت أدلة البالغين والأسرة والرعاية والروتين. روجعت مصادر الدليل وقيود الخدمات، واستُبدلت قائمة الأسماء غير المدعومة، وأُضيف اسم المالك وبريد عام، وأُزيلت مواضع الإعلان من صفحات العرض العام ووُحّدت الصفحات القديمة المتكررة.')]
    }
    for lang in ('en','ar'):
        body=enabout if lang=='en' else arabout
        page(lang,lang+'/about','About ADHDJO' if lang=='en' else 'عن ADHDJO',
             'A Jordan community resource owned by Nabil Aref.' if lang=='en' else 'مورد مجتمعي للأردن يملكه نبيل عارف.',
             '<section class="section"><div class="wrap prose">'+body+'</div></section>')
        body=''.join('<h2>'+e(t)+'</h2>'+para(p) for t,p in editorial[lang])
        page(lang,lang+'/editorial','Editorial policy and corrections' if lang=='en' else 'سياسة التحرير والتصحيح',
             'Who publishes this content, how it is prepared, and how to report an error.' if lang=='en' else 'من ينشر المحتوى، وكيف يُعدّ، وكيف تبلغ عن خطأ.',
             '<section class="section"><div class="wrap prose">'+body+'</div></section>')
        intro='Contact Nabil Aref, owner of ADHDJO, about website content or corrections.' if lang=='en' else 'تواصل مع نبيل عارف، مالك ADHDJO، بشأن محتوى الموقع أو التصحيحات.'
        body='<h2>'+('Email or Instagram' if lang=='en' else 'البريد الإلكتروني أو Instagram')+'</h2><p>'+link('mailto:naref@adhdjo.org','naref@adhdjo.org')+' · '+link('https://www.instagram.com/adhdjo/','@adhdjo')+'</p>'
        body+=para('For a correction, include the page URL, the exact statement and a public source if available. For a directory update, include the provider’s official page and the public contact or service detail that changed.' if lang=='en' else 'لطلب تصحيح، أرسل رابط الصفحة والنص المحدد ومصدراً علنياً إن توفر. ولتحديث الدليل، أرسل الصفحة الرسمية للخدمة والمعلومة العامة التي تغيرت.')
        body+=para('Please do not send medical records, identity documents, private symptom histories or information about another person. This inbox and Instagram account do not provide assessment, prescriptions, appointments or emergency care. Contact the service directly for healthcare questions. Response times are not guaranteed.' if lang=='en' else 'لا ترسل سجلات طبية أو وثائق هوية أو تاريخ أعراض خاصاً أو معلومات عن شخص آخر. لا يوفر البريد أو حساب Instagram تقييماً أو وصفات أو مواعيد أو رعاية طارئة. تواصل مع مقدم الخدمة مباشرة للأسئلة الصحية. لا توجد مدة استجابة مضمونة.')
        body+='<p>'+link('/'+lang+'/editorial/','Editorial and corrections policy' if lang=='en' else 'سياسة التحرير والتصحيح')+'</p>'
        page(lang,lang+'/contact','Contact' if lang=='en' else 'تواصل معنا',intro,'<section class="section"><div class="wrap prose">'+body+'</div></section>')


def legacy_redirect(path,target):
    text='This page has moved. Continue to the current ADHDJO resource.'
    (ROOT/path).write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page moved — ADHDJO</title><meta name="robots" content="noindex,follow"><link rel="canonical" href="{ORIGIN+target}"><meta http-equiv="refresh" content="0;url={target}"></head><body><main><h1>Page moved / انتقلت الصفحة</h1><p>{text}</p><p>{link(target,"Continue / متابعة")}</p></main></body></html>\n')


def shared_updates():
    root=load('index.html')
    for old in root.select('[data-root-intro]'):old.decompose()
    intro='<section data-root-intro class="section-small"><div class="grid two"><div lang="en"><h2>Practical help for your next step</h2><p>Learn how to arrange an ADHD assessment in Jordan, prepare useful appointment questions, and compare published service information. Read the sources and limits beside each guide or directory entry.</p><ul><li>'+link('/en/learn/assessment-in-jordan/','Assessment in Jordan')+'</li><li>'+link('/en/support/','Find support')+'</li><li>'+link('/en/editorial/','Editorial policy')+'</li></ul></div><div lang="ar" dir="rtl"><h2>مساعدة عملية لخطوتك التالية</h2><p>تعرّف على خطوات طلب تقييم في الأردن، وجهّز أسئلة مفيدة للموعد، وقارن المعلومات المنشورة عن الخدمات. تجد المصادر وحدود المعلومات بجانب الأدلة والإدراجات.</p><ul><li>'+link('/ar/learn/assessment-in-jordan/','التقييم في الأردن')+'</li><li>'+link('/ar/support/','ابحث عن دعم')+'</li><li>'+link('/ar/editorial/','سياسة التحرير')+'</li></ul></div></div><p class="small">ADHDJO · Owner / المالك: Nabil Aref · '+link('mailto:naref@adhdjo.org','naref@adhdjo.org')+'</p></section>'
    root.main.append(soup(intro));save(root,'index.html')
    for lang in ('en','ar'):
        for path in sorted((ROOT/lang).rglob('*.html')):
            rel=str(path.relative_to(ROOT));doc=load(rel);absolute_links(doc,rel)
            if doc.find('meta',attrs={'http-equiv':'refresh'}):continue
            # Remove advertisements from navigation/overview pages; keep their existing privacy controls working.
            if rel in [f'{lang}/index.html',f'{lang}/faq/index.html',f'{lang}/learn/index.html']:
                for a in doc.select('.ad-section'):a.decompose()
                for a in doc.select('script'):
                    if 'adsbygoogle' in str(a) or 'ads-privacy.js' in str(a):a.decompose()
                for a in doc.select('[data-ad-privacy]'):a.decompose()
            # Add a single accountability link to every footer and a visible privacy control where Google loads.
            foot=doc.select_one('.footer-links:last-child')
            if foot and not foot.find('a',href='/'+lang+'/editorial/'):
                foot.append(soup(link('/'+lang+'/editorial/','Editorial policy' if lang=='en' else 'سياسة التحرير')))
            bottom=doc.select_one('.footer-bottom')
            if bottom:
                bottom.clear();bottom.append(soup('<span>ADHDJO · '+('Owner: Nabil Aref' if lang=='en' else 'المالك: نبيل عارف (Nabil Aref)')+'</span><span>'+link('mailto:naref@adhdjo.org','naref@adhdjo.org')+'</span>'))
            if doc.find('script',src=re.compile('pagead2')) and not doc.select_one('[data-ad-privacy]'):
                doc.select_one('.site-footer .wrap').append(soup('<button type="button" class="ad-privacy-link" data-ad-privacy hidden>'+('Privacy and cookie settings' if lang=='en' else 'إعدادات الخصوصية وملفات الارتباط')+'</button>'))
            for node in doc.find_all(string=True):
                if node.parent.name not in ('script','style') and ('↗' in node or '↖' in node):node.replace_with(str(node).replace(' ↗','').replace(' ↖',''))
            if '/learn/' in rel or '/faq/' in rel or rel==f'{lang}/index.html':
                for node in doc.find_all(string=True):
                    if node.parent.name in ('script','style'):continue
                    changed=str(node).replace('Sources checked on 13 October 2026','References checked on 19 November 2026').replace('تم التحقق من المصادر في 13 أكتوبر 2026','روجعت المراجع في 19 نوفمبر 2026')
                    if changed!=str(node):node.replace_with(changed)
            if rel==f'{lang}/faq/index.html':
                source=doc.select_one('#women .sources')
                if source and not source.find('a',href='https://www.nimh.nih.gov/health/publications/adhd-what-you-need-to-know'):
                    source.append(soup(' · '+link('https://www.nimh.nih.gov/health/publications/adhd-what-you-need-to-know','NIMH: ADHD in adults')))
            for a in doc.select('.card-number'):a.decompose()
            save(doc,rel)
        # A prominent Jordan-specific entry on home and the learning index, without duplicating prose.
        for rel in [f'{lang}/index.html',f'{lang}/learn/index.html']:
            doc=load(rel)
            for old in doc.select('[data-jordan-guide]'):old.decompose()
            title='Start an assessment in Jordan' if lang=='en' else 'ابدأ التقييم في الأردن'
            text='Check who will assess you, compare the full cost, prepare for missing records, and leave with a clear next step.' if lang=='en' else 'تحقق من المختص، وقارن التكلفة الكاملة، واستعد عند غياب السجلات، وحدد خطوة تالية واضحة.'
            card=soup('<section class="section-small" data-jordan-guide><div class="wrap notice"><h2>'+e(title)+'</h2>'+para(text)+'<p>'+link('/'+lang+'/learn/assessment-in-jordan/','Read the Jordan assessment guide' if lang=='en' else 'اقرأ دليل التقييم في الأردن')+'</p></div></section>')
            first=doc.main.find('section');first.insert_after(card)
            # The number of published guides changed.
            for node in doc.find_all(string=True):
                if 'Five detailed guides' in str(node):node.replace_with(str(node).replace('Five detailed guides','Six detailed guides'))
                if 'خمسة أدلة' in str(node):node.replace_with(str(node).replace('خمسة أدلة','ستة أدلة'))
            save(doc,rel)
        # Link the existing private checklist to its detailed preparation instructions.
        rel=f'{lang}/tools/appointment-prep/index.html';doc=load(rel)
        if not doc.select_one('[data-prep-guide]'):
            panel=doc.select_one('.tool-panel') or doc.main
            panel.insert(0,soup('<p data-prep-guide>'+link('/'+lang+'/learn/assessment/','Read the preparation guide and example worksheet' if lang=='en' else 'اقرأ دليل التحضير ومثال الورقة العملية')+'</p>'))
            save(doc,rel)
    for p,t in [('about.html','/en/about/'),('contact.html','/en/contact/'),('guide.html','/en/learn/'),('privacy.html','/en/privacy/')]:legacy_redirect(p,t)
    for lang in ('en','ar'):legacy_redirect(f'{lang}/support/community-jordan/index.html','/'+lang+'/support/')


def sitemap():
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns)
    tree=ET.Element('{'+ns+'}urlset')
    urls=['/']
    for lang in ('en','ar'):
        for p in sorted((ROOT/lang).rglob('index.html')):
            if load(str(p.relative_to(ROOT))).find('meta',attrs={'http-equiv':'refresh'}):continue
            urls.append('/'+str(p.parent.relative_to(ROOT))+'/')
    for u in urls:
        item=ET.SubElement(tree,'{'+ns+'}url');ET.SubElement(item,'{'+ns+'}loc').text=ORIGIN+u
    ET.ElementTree(tree).write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)


if __name__=='__main__':
    update_guides();editorial_pages();shared_updates();sitemap()
    print('Generated bilingual guides, editorial pages, navigation updates and sitemap.')
