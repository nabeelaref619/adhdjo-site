(function (root) {
'use strict';
function parseCSV(text) {
 const rows=[]; let row=[],field='',quoted=false,closed=false;
 text=String(text).replace(/^\uFEFF/,'');
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(quoted){
   if(c==='"'&&text[i+1]==='"'){field+='"';i++;}
   else if(c==='"'){quoted=false;closed=true;}else field+=c;
  }else if(c==='"'&&!field&&!closed)quoted=true;
  else if(c===','||c==='\n'||c==='\r'){
   row.push(field);field='';closed=false;
   if(c!==','){if(c==='\r'&&text[i+1]==='\n')i++;if(row.some(v=>v.trim()))rows.push(row);row=[];}
  }else{if(closed||c==='"')throw new Error('Malformed CSV');field+=c;}
 }
 if(quoted)throw new Error('Incomplete CSV');
 row.push(field);if(row.some(v=>v.trim()))rows.push(row);
 if(!rows.length)throw new Error('Missing CSV header');
 const headers=rows.shift().map(v=>v.trim().toLowerCase());
 if(!headers.includes('name')||!headers.includes('status')||new Set(headers).size!==headers.length)throw new Error('Invalid directory schema');
 return rows.map(values=>{if(values.length!==headers.length)throw new Error('Invalid CSV row');return Object.fromEntries(headers.map((key,i)=>[key,values[i].trim()]));});
}
const samples=new Set(['dr. sara al-qasem','dr. faris khalidi','dr. lina haddad']);
function approvedRows(text){
 const seen=new Set();
 return parseCSV(text).filter(row=>row.status.toLowerCase()==='approved'&&row.name&&!samples.has(row.name.toLowerCase())).flatMap(row=>{
  const key=row.name.toLowerCase();if(seen.has(key))return [];seen.add(key);
  // Approval permits a community listing. Omit vetting notes, unconfirmed roles and contacts.
  return [{name:row.name,location:row.city||''}];
 });
}
function safeURL(value){
 try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u.href:'';}catch{return '';}
}
function safePhone(value){
 let p=String(value||'').replace(/[٠-٩۰-۹]/g,c=>String(c.charCodeAt(0)-(c>='۰'?1776:1632))).replace(/[\s().-]/g,'');
 if(/^00\d+$/.test(p))p='+'+p.slice(2);
 if(/^0(?:7[789]\d{7}|[2-6]\d{7})$/.test(p))p='+962'+p.slice(1);
 return /^\+[1-9]\d{6,14}$/.test(p)?p:'';
}
function withDetails(rows,details={}){
 return rows.map(row=>{
  const d=details&&Object.hasOwn(details,row.name)?details[row.name]:null,source=d&&safeURL(d.source);
  if(!source||!/^\d{4}-\d{2}-\d{2}$/.test(d.checked||''))return {...row,specialty:'Details awaiting confirmation'};
  return {...row,specialty:String(d.specialty||'Details awaiting confirmation'),clinic:String(d.clinic||''),location:String(d.location||row.location),phone:safePhone(d.phone),languages:String(d.languages||''),source,checked:d.checked,whatsapp:d.whatsapp===true};
 });
}
function filter(rows,query,location,specialty){
 const q=String(query||'').trim().toLocaleLowerCase();
 return rows.filter(r=>(!q||[r.name,r.clinic||''].some(v=>v.toLocaleLowerCase().includes(q)))&&(!location||r.location===location)&&(!specialty||r.specialty===specialty));
}
async function load(fetcher,url,timeout=12000){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
 try{const response=await fetcher(url,{signal:controller.signal,cache:'no-store',credentials:'omit'});if(!response.ok)throw new Error('Directory source unavailable');return approvedRows(await response.text());}
 finally{clearTimeout(timer);}
}
const api={parseCSV,approvedRows,safeURL,safePhone,withDetails,filter,load};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ADHDDirectory=api;
})(typeof globalThis!=='undefined'?globalThis:this);
