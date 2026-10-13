(function(root){
'use strict';
const MISSIONS=['learn-one','prepare-question','small-action','notice-support'];
function normalize(value){return String(value||'').normalize('NFKD').replace(/[\u064B-\u065F\u0640]/g,'').replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').toLocaleLowerCase().trim();}
function matchesResource(resource,query,country,type,population){const groups=resource.eligiblePopulations||resource.populations;return(!query||normalize(resource.text).includes(normalize(query)))&&(!country||resource.country===country)&&(!type||resource.type===type)&&(!population||groups.includes(population));}
function readProgress(storage){try{const d=JSON.parse(storage.getItem('adhdjo_progress_v1')||'{}');return{enabled:d.enabled===true,completed:[...new Set((Array.isArray(d.completed)?d.completed:[]).filter(x=>MISSIONS.includes(x)))]};}catch{return{enabled:false,completed:[]};}}
function saveProgress(storage,state){const clean={enabled:state.enabled===true,completed:[...new Set(state.completed.filter(x=>MISSIONS.includes(x)))]};try{storage.setItem('adhdjo_progress_v1',JSON.stringify(clean));return true;}catch{return false;}}
function updateMission(state,id,complete=true){if(!state.enabled||!MISSIONS.includes(id))return state;return{enabled:state.enabled,completed:complete?[...new Set([...state.completed,id])]:state.completed.filter(x=>x!==id)};}
function makeTimer(minutes=10){const n=Number(minutes);const duration=(Number.isFinite(n)?Math.max(1,Math.min(90,Math.floor(n))):10)*60000;return{duration,remaining:duration,state:'idle',started:null};}
function remaining(timer,now){return timer.state==='running'?Math.max(0,timer.remaining-Math.max(0,now-timer.started)):timer.remaining;}
function startTimer(timer,now){if(timer.state==='running')return timer;return{...timer,remaining:timer.remaining>0?timer.remaining:timer.duration,state:'running',started:now};}
function pauseTimer(timer,now){if(timer.state!=='running')return timer;const left=remaining(timer,now);return{...timer,remaining:left,state:left>0?'paused':'finished',started:null};}
function tickTimer(timer,now){return timer.state==='running'&&remaining(timer,now)===0?{...timer,state:'finished',remaining:0,started:null}:timer;}
const api={MISSIONS,normalize,matchesResource,readProgress,saveProgress,updateMission,makeTimer,remaining,startTimer,pauseTimer,tickTimer};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ADHDJO=api;
})(typeof globalThis==='undefined'?this:globalThis);
