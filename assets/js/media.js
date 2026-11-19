'use strict';
(() => {
  const library = document.querySelector('[data-media-library]');
  if (!library) return;
  const ar = document.documentElement.lang === 'ar';
  const search = document.querySelector('[data-media-search]');
  const platform = document.querySelector('[data-media-platform]');
  const kind = document.querySelector('[data-media-kind]');
  const status = document.querySelector('[data-media-status]');
  const empty = document.querySelector('[data-media-empty]');
  const cards = [...library.querySelectorAll('[data-media-item]')];
  const stages = [...library.querySelectorAll('[data-video-player]')];
  const placeholders = new Map(stages.map(stage => [stage, [...stage.childNodes].map(node => node.cloneNode(true))]));
  const normalize = value => value.toLocaleLowerCase().normalize('NFKD')
    .replace(/[\u0300-\u036f\u064b-\u065f\u0670\u0640]/g, '').replace(/[أإآ]/g, 'ا').trim();
  function unload(stage) {
    if (!stage.querySelector('iframe')) return;
    stage.replaceChildren(...placeholders.get(stage).map(node => node.cloneNode(true)));
  }
  function filter() {
    const words = normalize(search.value).split(/\s+/).filter(Boolean);
    let count = 0;
    cards.forEach(card => {
      const matches = (!platform.value || card.dataset.platform === platform.value)
        && (!kind.value || card.dataset.kind === kind.value)
        && words.every(word => normalize(card.dataset.search || card.textContent).includes(word));
      card.hidden = !matches;
      if (matches) count += 1;
      else card.querySelectorAll('[data-video-player]').forEach(unload);
    });
    library.querySelectorAll('[data-media-group]').forEach(group => {
      group.hidden = ![...group.querySelectorAll('[data-media-item]')].some(card => !card.hidden);
    });
    status.textContent = ar ? `روابط الفيديو: ${count} من ${cards.length}` : `Video links: ${count} of ${cards.length}`;
    empty.hidden = count !== 0;
  }
  search.addEventListener('input', filter);
  platform.addEventListener('change', filter);
  kind.addEventListener('change', filter);
  document.querySelector('[data-media-clear]').addEventListener('click', () => {
    search.value = ''; platform.value = ''; kind.value = ''; filter(); search.focus();
  });
  document.querySelectorAll('.media-feature').forEach(link => link.addEventListener('click', () => {
    search.value = ''; platform.value = ''; kind.value = ''; filter();
  }));
  library.addEventListener('click', event => {
    const button = event.target.closest('[data-video-load]');
    if (!button || !library.contains(button)) return;
    const videoId = button.dataset.youtubeId;
    if (!/^[A-Za-z0-9_-]{11}$/.test(videoId || '')) return;
    const stage = button.closest('[data-video-player]');
    if (!stage) return;
    stages.forEach(unload);
    const player = document.createElement('iframe');
    player.src = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`;
    player.title = button.dataset.videoTitle || (ar ? 'مشغل فيديو YouTube' : 'YouTube video player');
    player.allow = 'encrypted-media; picture-in-picture; fullscreen';
    player.allowFullscreen = true;
    player.referrerPolicy = 'strict-origin-when-cross-origin';
    const close = document.createElement('button');
    close.type = 'button'; close.className = 'media-player-close';
    close.textContent = ar ? 'إغلاق المشغل' : 'Close player';
    close.addEventListener('click', () => {
      unload(stage); stage.querySelector('[data-video-load]')?.focus();
    });
    stage.replaceChildren(player, close);
    player.focus();
  });
  filter();
})();
