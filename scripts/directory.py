"""Render the bilingual support directory from versioned public source metadata.

Run after remediate.py, then run its shared_updates()/sitemap() steps. No network
access or sibling research files are required. Changes to entries belong in
content/directory.json; this renderer never imports the excluded-name ledger.
"""
import json
import re

from remediate import ROOT, byline, e, link, page, para


DATA = json.loads((ROOT / 'content/directory.json').read_text())
RECORDS = DATA['records']
DAY = DATA['checked_on']


def bi(en, ar):
    return {'en': en, 'ar': ar}


COUNTRIES = {
    'JO': bi('Jordan', 'الأردن'),
    'AE': bi('United Arab Emirates', 'الإمارات العربية المتحدة'),
    'SA': bi('Saudi Arabia', 'السعودية'),
    'EG': bi('Egypt', 'مصر'),
    'LB': bi('Lebanon', 'لبنان'),
    'GB': bi('United Kingdom', 'المملكة المتحدة'),
    'US': bi('United States', 'الولايات المتحدة'),
    'CA': bi('Canada', 'كندا'),
    'AU': bi('Australia / New Zealand directory', 'دليل أستراليا / نيوزيلندا'),
}
TYPES = {
    'clinical_service': bi('Medical assessment / clinical service', 'تقييم طبي / خدمة سريرية'),
    'psychological_assessment': bi('Psychological assessment', 'تقييم في علم النفس'),
    'psychological_therapy': bi('Psychological therapy', 'علاج نفسي'),
    'developmental_support': bi('Child development / learning support', 'تطور الطفل / دعم التعلم'),
    'support_navigation': bi('Support organization', 'مؤسسة دعم'),
    'referral_directory': bi('Professional / service directory', 'دليل مهنيين / خدمات'),
    'specialist_referral': bi('Specialist referral only', 'إحالة تخصصية فقط'),
}
POPULATIONS = {
    'children': bi('Children', 'الأطفال'),
    'adolescents': bi('Adolescents', 'المراهقون'),
    'adults': bi('Adults', 'البالغون'),
    'young_adults': bi('Young adults', 'الشباب البالغون'),
    'families': bi('Families', 'الأسر'),
    'unconfirmed': bi('Age range to confirm', 'الفئة العمرية تحتاج إلى تأكيد'),
}
GROUPS = {
    'jordan_assessment': {
        'title': bi('Jordan: assessment and psychiatric services', 'الأردن: التقييم وخدمات الطب النفسي'),
        'intro': bi('Four published routes to ask about ADHD assessment or care. Confirm the professional, ages served and the full assessment process before booking.', 'أربع جهات تعلن معلومات عن تقييم ADHD أو رعايته. تأكد من المختص والأعمار المقبولة وخطوات التقييم الكاملة قبل الحجز.'),
    },
    'jordan_support': {
        'title': bi('Jordan: psychological and developmental support', 'الأردن: الدعم النفسي والنمائي'),
        'intro': bi('These services may help with therapy, learning or development. Their published information does not by itself establish a full ADHD diagnostic or prescribing service.', 'قد تساعد هذه الخدمات في العلاج النفسي أو التعلم أو النمو. معلوماتها المنشورة لا تثبت وحدها تقديم تشخيص كامل لـ ADHD أو خدمة لوصف الدواء.'),
    },
    'international_clinical': {
        'title': bi('Regional and international clinical services', 'خدمات سريرية في المنطقة ودول أخرى'),
        'intro': bi('Check residence, referral and age requirements first. A service listed abroad may not accept international patients or provide care remotely where you live.', 'تحقق أولاً من شروط الإقامة والإحالة والعمر. قد لا تقبل الخدمة خارج بلدك مرضى دوليين أو تقدم رعاية عن بعد في مكان إقامتك.'),
    },
    'organizations': {
        'title': bi('Support organizations and further directories', 'مؤسسات الدعم وأدلة أخرى'),
        'intro': bi('Use these to find programs or additional local providers. A directory listing or association membership is not a check of an individual professional’s licence.', 'استخدم هذه الروابط للبحث عن برامج أو مقدمي خدمة محليين إضافيين. الإدراج في دليل أو العضوية في جمعية ليس تحققاً من ترخيص الممارس.'),
    },
    'restricted_referral': {
        'title': bi('Specialist services: restricted referrals only', 'خدمات تخصصية: إحالات بشروط محددة فقط'),
        'intro': bi('These two NHS services are not ordinary self-booking routes. Read the restrictions before contacting them; your local clinician must determine whether referral is appropriate.', 'هاتان الخدمتان في NHS ليستا مساراً للحجز الذاتي المعتاد. اقرأ القيود قبل التواصل؛ يجب أن يحدد المختص المحلي مدى مناسبة الإحالة.'),
    },
}


def external(url, label, css=''):
    cls = f' class="{e(css, quote=True)}"' if css else ''
    return f'<a href="{e(url, quote=True)}"{cls}>{e(label)}</a>'


def options(values, lang, all_label):
    return '<option value="">' + e(all_label) + '</option>' + ''.join(
        f'<option value="{e(key, quote=True)}">{e(label[lang])}</option>'
        for key, label in values.items()
    )


def filters(lang):
    ar = lang == 'ar'
    fields = [
        ('country', 'data-filter-country', 'الدولة' if ar else 'Country', COUNTRIES, 'كل الدول' if ar else 'All countries'),
        ('resource-type', 'data-filter-type', 'نوع الخدمة' if ar else 'Resource type', TYPES, 'كل الأنواع' if ar else 'All types'),
        ('population', 'data-filter-population', 'الفئة المستفيدة' if ar else 'Who it serves', POPULATIONS, 'كل الفئات' if ar else 'All age groups'),
    ]
    label = 'ابحث بالاسم أو المكان أو الخدمة' if ar else 'Search names, locations or services'
    markup = f'<div class="filters"><div class="field"><label for="resource-search">{label}</label><input id="resource-search" data-resource-search type="search" placeholder="{label}" /></div>'
    for id_, attr, title, values, all_label in fields:
        markup += f'<div class="field"><label for="{id_}">{title}</label><select id="{id_}" {attr}>{options(values, lang, all_label)}</select></div>'
    markup += '</div><button type="button" class="button secondary" data-clear-filters>' + ('مسح الفلاتر' if ar else 'Clear filters') + '</button>'
    markup += '<p class="filter-status" data-directory-status role="status" aria-live="polite"></p><div class="empty" data-directory-empty hidden></div>'
    return markup


def card(record, lang):
    ar = lang == 'ar'
    rid = e(record['id'], quote=True)
    attr = (f'id="resource-{rid}" class="card provider" data-resource data-resource-id="{rid}" '
            f'data-country="{e(record["country_code"])}" data-type="{e(record["category"])}" '
            f'data-populations="{e(" ".join(record["population"]))}" '
            f'data-eligible-populations="{e(" ".join(record["eligible_population"]))}"')
    markup = f'<article {attr}><span class="tag">{e(TYPES[record["category"]][lang])}</span>'
    markup += '<p class="location">' + e(record['location'][lang]) + '</p>'
    markup += '<h3><bdi>' + e(record['name'][lang]) + '</bdi></h3>'
    markup += para(record['description'][lang])
    markup += '<p class="population">' + ' · '.join(e(POPULATIONS[p][lang]) for p in record['population']) + '</p>'
    markup += '<div class="eligibility"><strong>' + ('شروط الوصول وما يجب تأكيده' if ar else 'Access and what to confirm') + '</strong>' + para(record['access'][lang]) + '</div>'
    for contact in record['contacts']:
        val = e(contact['value'])
        if contact['kind'] == 'phone':
            dial = contact.get('dial') or re.sub(r'[^+0-9]', '', contact['value'])
            action = f'<a href="tel:{e(dial, quote=True)}"><bdi dir="ltr">{val}</bdi></a>'
        elif contact['kind'] == 'email':
            action = f'<a href="mailto:{e(contact["value"], quote=True)}"><bdi dir="ltr">{val}</bdi></a>'
        else:
            raise ValueError('Unknown contact kind: ' + contact['kind'])
        markup += '<p class="phone">' + e(contact['purpose'][lang]) + ': ' + action + '</p>'
    markup += '<p class="small muted">' + e(DATA['public_label'][lang]) + ' · <time datetime="' + e(record['checked_on']) + '">' + e(record['checked_on']) + '</time></p>'
    action_label = ('اقرأ شروط الإحالة' if ar else 'Read referral requirements') if record['restricted'] else ('صفحة الخدمة والتواصل' if ar else 'Service and contact page')
    markup += '<div class="actions">' + external(record['url'], action_label, 'button secondary') + '</div>'
    source_title = 'مصادر هذا الإدراج' if ar else 'Sources for this listing'
    markup += f'<details class="sources"><summary>{source_title} ({len(record["sources"])})</summary><ul>'
    for source in record['sources']:
        label = source['label'][lang] + ' — ' + source['publisher']
        markup += '<li>' + external(source['url'], label) + '</li>'
    return markup + '</ul></details></article>'


def directory(lang):
    ar = lang == 'ar'
    title = 'ابحث عن دعم ADHD' if ar else 'Find ADHD support'
    intro = ('ابدأ بالجهة المناسبة للتقييم أو العلاج النفسي أو دعم التعلم. لكل إدراج مصدر معلن وشروط وصول؛ الإدراج ليس توصية سريرية.' if ar else
             'Find a starting point for assessment, psychological therapy or learning support. Each listing has public sources and access notes; inclusion is not a clinical endorsement.')
    count = len(RECORDS)
    jordan_count = sum(r['country_code'] == 'JO' for r in RECORDS)
    body = '<section class="section"><div class="wrap">'
    if ar:
        body += '<div class="notice"><strong>ماذا تعني «تمت مراجعة المعلومات المنشورة»؟</strong><p>راجعنا صفحات مقدمي الخدمة والمؤسسات والجهات الصحية في 19 نوفمبر 2026. لم نتحقق مستقلاً من التراخيص أو جودة الرعاية أو الرسوم أو توفر المواعيد. تأكد من ذلك مباشرة قبل الحجز.</p>'
        body += link('/ar/support/methodology/', 'معايير الإدراج وحدود المراجعة') + '</div>'
        body += f'<p class="small muted">{count} مورداً مع مصادر · {jordan_count} خيارات في الأردن · منها خدمتان بإحالة تخصصية مقيدة</p>'
        body += '<p>' + link('/ar/learn/assessment-in-jordan/', 'تعرّف على خطوات بدء التقييم في الأردن') + ' · ' + link('/ar/tools/appointment-prep/', 'حضّر أسئلتك للموعد') + '</p>'
    else:
        body += '<div class="notice"><strong>What does “Published information checked” mean?</strong><p>We checked provider, organization and public health-service pages on 19 November 2026. We have not independently checked licences, clinical quality, fees or appointment availability. Confirm these directly before booking.</p>'
        body += link('/en/support/methodology/', 'How we select and check listings') + '</div>'
        body += f'<p class="small muted">{count} source-linked resources · {jordan_count} Jordan options · includes two restricted specialist referral services</p>'
        body += '<p>' + link('/en/learn/assessment-in-jordan/', 'Understand the assessment route in Jordan') + ' · ' + link('/en/tools/appointment-prep/', 'Prepare your appointment questions') + '</p>'
    body += filters(lang)
    jump_label = 'انتقل إلى قسم' if ar else 'Jump to a section'
    body += '<nav class="section-small" data-directory-jumps aria-label="' + jump_label + '"><p><strong>' + jump_label + ':</strong> ' + ' · '.join(link('#' + key, values['title'][lang]) for key, values in GROUPS.items()) + '</p></nav>'
    for group, labels in GROUPS.items():
        body += f'<section class="section-small" data-resource-group id="{group}" aria-labelledby="heading-{group}"><h2 id="heading-{group}">{e(labels["title"][lang])}</h2>'
        body += para(labels['intro'][lang]) + '<div class="grid provider-grid">'
        body += ''.join(card(r, lang) for r in RECORDS if r['group'] == group)
        body += '</div></section>'
    if ar:
        body += '<section class="section-small grid two"><div><h2>قبل دفع رسوم التقييم</h2><p>اسأل عن اسم المختص ومهنته وترخيصه الساري، والأعمار التي يعمل معها، وما يشمله التقييم والتقرير والمتابعة. اسأل عن الكلفة الكاملة وإمكانية التواصل بلغة تناسبك. الاختبار أو مقياس الأعراض وحده لا يكفي لتشخيص ADHD.</p>' + link('/ar/learn/assessment/', 'كيف يبدو التقييم الشامل؟') + '</div><div><h2>لم تجد جهة مناسبة؟</h2><p>هذه قائمة محدودة وليست حصراً للخدمات. ابدأ بمقدم الرعاية المعتاد أو بالخدمة الصحية المحلية واسأل عن الإحالة لمختص مناسب. غياب اسم من الدليل لا يعني أن الممارس غير مؤهل.</p>' + link('/ar/support/methodology/', 'كيف نختار الإدراجات؟') + '</div></section>'
        body += '<p class="notice">وجدت معلومة قديمة؟ أرسل رابط الإدراج والتصحيح ومصدره إلى ' + link('mailto:naref@adhdjo.org', 'naref@adhdjo.org') + '. لا ترسل سجلات طبية أو بيانات شخصية عن المريض.</p>'
        body += '<noscript><p class="no-js">يمكن قراءة جميع الإدراجات دون JavaScript؛ تحتاج فلاتر البحث إليه.</p></noscript>'
    else:
        body += '<section class="section-small grid two"><div><h2>Before paying for an assessment</h2><p>Ask who will assess you, their profession and current licence, the ages they work with, and what the assessment, report and follow-up include. Confirm the full cost and language access. A test or symptom scale alone is not an ADHD diagnosis.</p>' + link('/en/learn/assessment/', 'What does a comprehensive assessment involve?') + '</div><div><h2>No suitable option listed?</h2><p>This is a limited starting point, not a complete list of services. Ask your usual healthcare professional or local health service about referral to an appropriate specialist. An absent name does not mean a practitioner is unqualified.</p>' + link('/en/support/methodology/', 'How are listings selected?') + '</div></section>'
        body += '<p class="notice">Found outdated information? Send the listing link, correction and supporting source to ' + link('mailto:naref@adhdjo.org', 'naref@adhdjo.org') + '. Do not send medical records or identifying patient information.</p>'
        body += '<noscript><p class="no-js">All listings can be read without JavaScript; interactive filters require it.</p></noscript>'
    body += '</div></section>'
    page(lang, lang + '/support', title, intro, body)


def methodology(lang):
    ar = lang == 'ar'
    title = 'كيف نختار إدراجات دليل الدعم؟' if ar else 'How we check the support directory'
    intro = ('معايير الإدراج، وما راجعناه في 19 نوفمبر 2026، وما يجب تأكيده مباشرة مع مقدم الخدمة.' if ar else
             'Our inclusion criteria, what we checked on 19 November 2026, and what you still need to confirm directly.')
    body = '<section class="section"><div class="wrap prose">' + byline(lang)
    if ar:
        body += '<p class="notice"><strong>مراجعة معلومات، وليست اعتماداً للممارسين.</strong> تعني عبارة «تمت مراجعة المعلومات المنشورة» أننا قارنّا وصف الإدراج بصفحات مصدره. لا تعني أن ADHDJO تحققت من الترخيص أو الجودة أو أوصت بالخدمة.</p>'
        body += '<h2>ما الذي يُدرج في الدليل؟</h2><p>نختار جهات تنشر معلومات واضحة عن خدمة ذات صلة ووسيلة تواصل قابلة للاستخدام. نبدأ بالأردن، ثم نضيف خدمات إقليمية ودولية وأدلة قد تساعد القارئ في مكان إقامته. القائمة غير شاملة، وترتيبها حسب الموقع ونوع الخدمة وليس حسب الجودة.</p><ul><li>لتقييم ADHD أو رعايته، نبحث عن ذكر صريح للخدمة في موقع مقدمها أو الجهة الصحية المسؤولة.</li><li>نوضح إن كان المورد علاجاً نفسياً أو دعماً تعليمياً أو نمائياً أو دليلاً آخر؛ لا نحوله إلى عيادة تشخيص لمجرد ذكر ADHD.</li><li>ننشر الأعمار وشروط الإقامة والإحالة المعلنة، ونشير إلى ما يحتاج إلى تأكيد.</li><li>نضع الخدمات التخصصية المقيدة في قسم منفصل، مع القيود ظاهرة قبل رابط التواصل.</li></ul>'
        body += '<h2>ما الذي راجعناه؟</h2><p>في <time datetime="2026-11-19">19 نوفمبر 2026</time> راجعنا اسم الجهة ووصف الخدمة والأعمار والموقع ووسيلة التواصل وشروط الوصول المنشورة. لكل بطاقة روابط المصادر التي استُخدمت. نعتمد على موقع مقدم الخدمة أو المؤسسة أو جهة صحية عامة؛ ملف مقدم الخدمة يثبت ما يعلنه، ولا يثبت صحة كل مؤهلاته.</p><p>عند اختلاف المصادر لا نختار رقماً بصمت. مثلاً، الصفحة الرئيسية لمركز فيلادلفيا تذكر الأعمار 4–18 بينما إعلان أقدم يذكر 3–18؛ لذلك تطلب البطاقة تأكيد العمر مباشرة. وكذلك تذكر بطاقة خدمة مودسلي الوطنية إغلاق الإحالات الوطنية الجديدة في نوفمبر 2026.</p>'
        body += '<h2>ما الذي لم نتحقق منه؟</h2><ul><li>سريان ترخيص الممارس أو المنشأة لدى الجهة التنظيمية.</li><li>جودة الرعاية أو نتائجها أو كفاية التدريب أو ملاءمة المختص لحالتك.</li><li>المواعيد المتاحة حالياً أو السعر أو التغطية التأمينية أو إمكانية الوصول للمكان.</li><li>السماح بتقديم علاج عن بعد أو وصف دواء عبر الحدود.</li></ul><p>لم نتصل بالممارسين أو نحجز مواعيد. أُجري البحث والصياغة والترجمة بمساعدة الذكاء الاصطناعي؛ لم تُجرَ مراجعة سريرية مستقلة. تاريخ المراجعة يصف وقت فحصنا للمصدر، وليس ضماناً أن مقدم الخدمة حدّث كل معلوماته في ذلك اليوم.</p>'
        body += '<h2>قبل الاعتماد على إدراج</h2><ol><li>اقرأ نوع الخدمة والفئة العمرية وشروط الوصول؛ التدريب والدعم النفسي والتشخيص والوصفة الدوائية خدمات مختلفة.</li><li>افتح المصدر واتصل بالجهة لتأكيد قبول عمرك ومكان إقامتك والمواعيد والكلفة والتقرير والمتابعة.</li><li>اطلب اسم من سيقدم الخدمة ومهنته ورقم ترخيصه، وتحقق من سريانه مع الجهة التنظيمية المناسبة.</li><li>في الأردن، اقرأ دليلنا لمسار التقييم والتحقق من المؤهلات قبل الدفع.</li></ol>'
        body += para('لا يثبت الإدراج في جمعية مهنية أو دليل آخر وجود ترخيص ساري. كما أن توفر جلسة عبر الإنترنت لا يعني السماح بتقديم الخدمة في كل بلد.')
        body += '<p>' + link('/ar/learn/assessment-in-jordan/', 'بدء التقييم والتحقق من المؤهلات في الأردن') + ' · ' + link('/ar/tools/appointment-prep/', 'قائمة أسئلة الموعد') + '</p>'
        body += '<h2>كيف نتعامل مع الأسماء المقترحة؟</h2><p>الاقتراح المجتمعي نقطة بداية للبحث وليس دليلاً على المؤهلات أو جودة الرعاية. لا ننشر اسماً بلا مصدر مناسب يوضح الخدمة ووسيلة تواصل. نقص المعلومات العامة سبب لعدم الإدراج؛ ليس حكماً على الممارس. تتضمن هذه النسخة 18 مورداً، منها ستة في الأردن وخدمتان دوليتان بإحالة تخصصية مقيدة.</p>'
        body += '<h2>الإبلاغ عن خطأ أو اقتراح تحديث</h2><p>أرسل رابط الإدراج والمعلومة المقترح تصحيحها ورابط مصدر حالي إلى ' + link('mailto:naref@adhdjo.org', 'naref@adhdjo.org') + '. لا ترسل ملفاً طبياً أو معلومات تعريفية عن مريض. سنقارن التصحيح بالمصدر قبل تعديل الإدراج؛ إرسال اقتراح لا يضمن إضافته.</p><p>قد تتغير تفاصيل الخدمة بعد تاريخ المراجعة. تأكد منها مباشرة في كل مرة تحجز فيها.</p>'
        body += '<p>' + link('/ar/support/', 'العودة إلى دليل الدعم') + ' · ' + link('/ar/editorial/', 'سياسة إعداد المحتوى') + '</p>'
    else:
        body += '<p class="notice"><strong>This is an information check, not practitioner accreditation.</strong> “Published information checked” means we compared a listing with its source pages. It does not mean ADHDJO has verified a licence, assessed quality or recommended the service.</p>'
        body += '<h2>What qualifies for inclusion?</h2><p>We select resources that publish a relevant service and a usable contact route. Jordan comes first, followed by regional and international services and directories that may help readers where they live. This is not a complete list. Entries are grouped by location and service type, not ranked by quality.</p><ul><li>For ADHD assessment or care, we look for an explicit service description on the provider’s or responsible health-service website.</li><li>We identify psychological therapy, learning or developmental support, and other directories separately. Mentioning ADHD does not automatically make a resource a diagnostic clinic.</li><li>We state published age, residence and referral restrictions and identify details that need confirmation.</li><li>Restricted specialist services appear in a separate section, with conditions visible before the contact link.</li></ul>'
        body += '<h2>What did we check?</h2><p>On <time datetime="2026-11-19">19 November 2026</time>, we checked published names, service descriptions, ages, location, contact routes and access restrictions. Each card links to the sources used. We use the provider, organization or public health-service website; a provider’s profile establishes what it says, not the validity of every credential it claims.</p><p>When sources disagree, we flag the difference. For example, the Philadelphia center’s main page lists ages 4–18 while an older notice says 3–18, so its card asks you to confirm age eligibility. The Maudsley national service card also records the November 2026 closure to new national referrals.</p>'
        body += '<h2>What remains unconfirmed?</h2><ul><li>Current practitioner or facility licences with the relevant regulator.</li><li>Clinical quality, outcomes, adequacy of training or suitability for your needs.</li><li>Current appointment availability, price, insurance cover or physical accessibility.</li><li>Permission to provide remote care or prescribe across borders.</li></ul><p>We did not contact practitioners or book appointments. Research, drafting and translation were AI-assisted; independent clinical review has not been completed. The date records when we checked the source, not a guarantee that the provider updated every detail on that day.</p>'
        body += '<h2>Before relying on a listing</h2><ol><li>Read the service type, age group and access conditions. Coaching, psychological support, diagnosis and prescribing are different services.</li><li>Open the source and contact the service to confirm your age and location are eligible, and ask about appointments, full cost, the report and follow-up.</li><li>Ask for the treating professional’s name, profession and licence number, then check current status with the appropriate regulator.</li><li>In Jordan, use our guide to the assessment route and checking credentials before paying.</li></ol>'
        body += para('Professional association membership or inclusion in another directory does not establish a current licence. An online appointment option also does not establish permission to treat patients in every country.')
        body += '<p>' + link('/en/learn/assessment-in-jordan/', 'Assessment and checking credentials in Jordan') + ' · ' + link('/en/tools/appointment-prep/', 'Prepare an appointment checklist') + '</p>'
        body += '<h2>How are suggested names handled?</h2><p>A community suggestion is a research lead, not evidence of qualifications or quality. We do not publish a name without a suitable source describing the service and a contact route. Insufficient public information is a reason for omission, not a judgment that a practitioner is unqualified. This edition contains 18 resources, including six Jordan options and two restricted international specialist referral services.</p>'
        body += '<h2>Report a correction or suggest an update</h2><p>Send the listing link, the detail to correct and a current source URL to ' + link('mailto:naref@adhdjo.org', 'naref@adhdjo.org') + '. Do not send medical records or identifying patient information. We will compare the correction with the source before changing the listing; a suggestion does not guarantee inclusion.</p><p>Service details can change after the review date. Confirm them directly each time you book.</p>'
        body += '<p>' + link('/en/support/', 'Return to the support directory') + ' · ' + link('/en/editorial/', 'Editorial policy') + '</p>'
    body += '</div></section>'
    page(lang, lang + '/support/methodology', title, intro, body)


def main():
    if len({r['id'] for r in RECORDS}) != len(RECORDS):
        raise ValueError('Duplicate directory IDs')
    for record in RECORDS:
        if not record['sources'] or not record['contacts'] and not record['url']:
            raise ValueError('Every entry needs evidence and an actionable public route')
        if record['licence_checked'] or record['availability_confirmed']:
            raise ValueError('This review does not independently establish licensing or availability')
    for lang in ('en', 'ar'):
        directory(lang)
        methodology(lang)
    print(f'Rendered {len(RECORDS)} entries and methodology in English and Arabic.')


if __name__ == '__main__':
    main()
