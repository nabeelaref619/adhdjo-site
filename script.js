'use strict';
const DIRECTORY_URL='https://docs.google.com/spreadsheets/d/e/2PACX-1vTIWsEjPZgk82OchrMVhVJksdB43JyOg1ZuiijDRAXaJxU0beYlPCqG4kvvC3abUbhig1uYz5IKNUFL/pub?output=csv';
let directory=[],state='loading';
const $=id=>document.getElementById(id);
function textNode(tag,text,className){const el=document.createElement(tag);el.textContent=text;if(className)el.className=className;return el;}
function toggleMenu(open=!$('mobileMenu').classList.contains('open')){$('mobileMenu').classList.toggle('open',open);$('hamburger').setAttribute('aria-expanded',String(open));}
function showPage(moveFocus=false){
 if(location.hash==='#main'){$('main').focus({preventScroll:true});return;}
 const id=['home','doctors','content'].includes(location.hash.slice(1))?location.hash.slice(1):'home';
 document.querySelectorAll('.page-section').forEach(el=>{el.classList.toggle('active',el.id==='page-'+id);el.hidden=el.id!=='page-'+id;});
 document.querySelectorAll('[data-page]').forEach(a=>{const active=a.dataset.page===id;a.classList.toggle('active',active);if(active)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
 toggleMenu(false);document.title=(id==='doctors'?'Community directory':id==='content'?'Practical resources':'ADHD community in Jordan')+' — adhdjo';
 if(moveFocus){$('main').focus({preventScroll:true});window.scrollTo({top:0,behavior:'auto'});}
}
function options(id,values,label){
 const select=$(id),previous=select.value;select.replaceChildren(new Option(label,''));
 [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b)).forEach(v=>select.add(new Option(v,v)));
 if(values.includes(previous))select.value=previous;
}
function renderGrid(){
 const grid=$('grid');grid.replaceChildren();
 if(state==='loading'){$('count-label').textContent='Loading…';$('directory-status').textContent='Loading the community directory…';return;}
 if(state==='error'){$('count-label').textContent='Unavailable';$('directory-status').textContent='The directory could not be loaded. Please try again. No sample listings are shown.';$('retry-directory').hidden=false;return;}
 $('retry-directory').hidden=true;
 const rows=ADHDDirectory.filter(directory,$('search').value,$('filter-city').value,$('filter-spec').value);
 $('count-label').textContent=rows.length+' community listing'+(rows.length===1?'':'s');
 $('directory-status').textContent=!directory.length?'There are no approved community listings available yet.':!rows.length?'No listings match these filters. Clear the search or try another location.':'Community recommendations are not medical endorsements. Confirm identity, qualifications and current availability directly with the provider.';
 rows.forEach(row=>{
  const card=textNode('article','','card');card.append(textNode('span','Community listed','card-badge'));
  const name=textNode('h3',row.name,'card-name');name.dir='auto';card.append(name);card.append(textNode('p',row.specialty,'card-specialty'));
  const meta=textNode('div','','card-meta');
  if(row.location){const p=textNode('p','Reported location: '+row.location);p.dir='auto';meta.append(p);}
  if(row.clinic){const p=textNode('p',row.clinic);p.dir='auto';meta.append(p);}
  if(row.languages)meta.append(textNode('p','Languages: '+row.languages));
  if(row.source){const a=textNode('a','Provider source · checked '+row.checked);a.href=row.source;a.target='_blank';a.rel='noopener noreferrer';meta.append(a);}
  else meta.append(textNode('p','Qualifications and contact details have not been independently confirmed.'));
  card.append(meta);
  if(row.phone){
   const actions=textNode('div','','card-actions'),call=textNode('a','Call '+row.name,'btn-sm primary');call.href='tel:'+row.phone;actions.append(call);
   if(row.whatsapp){const wa=textNode('a','WhatsApp','btn-sm');wa.href='https://wa.me/'+row.phone.slice(1);wa.target='_blank';wa.rel='noopener noreferrer';actions.append(wa);}card.append(actions);
  }
  grid.append(card);
 });
}
async function loadDirectory(){
 state='loading';$('retry-directory').hidden=true;renderGrid();
 try{
  const rows=await ADHDDirectory.load(fetch,DIRECTORY_URL);let details={};
  try{const response=await fetch('provider-details.json',{cache:'no-store'});if(response.ok)details=await response.json();}catch{/* Names remain usable if supplemental details fail. */}
  directory=ADHDDirectory.withDetails(rows,details);state='ready';
  options('filter-city',directory.map(d=>d.location),'All reported locations');options('filter-spec',directory.map(d=>d.specialty),'All specialties');
  $('stat-docs-home').textContent=directory.length;$('source-state').textContent='Public directory loaded on '+new Date().toLocaleDateString('en-GB')+'. Approval indicates permission to list, not clinical verification.';
 }catch{directory=[];state='error';$('stat-docs-home').textContent='—';$('source-state').textContent='Public directory temporarily unavailable.';}
 renderGrid();
}
window.addEventListener('hashchange',()=>showPage(true));$('hamburger').addEventListener('click',()=>toggleMenu());
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('mobileMenu').classList.contains('open')){toggleMenu(false);$('hamburger').focus();}});
document.querySelectorAll('[data-page]').forEach(a=>a.addEventListener('click',()=>toggleMenu(false)));
$('search').addEventListener('input',renderGrid);['filter-city','filter-spec'].forEach(id=>$(id).addEventListener('change',renderGrid));
$('retry-directory').addEventListener('click',loadDirectory);showPage();loadDirectory();
