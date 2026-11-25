import {config} from './config.js';
import {parseIdentifier,businessNumberFile,businessNumberMatches} from './identifiers.mjs';
import {human,validRecord,changes,addCapture,parseSaved,incorporationDate} from './live-model.mjs';
const $=id=>document.getElementById(id),key='coolcode:corporateghosts:captures',create=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const button=(text,fn)=>{const b=create('button',text);b.type='button';b.onclick=fn;return b;};
const stamp=date=>new Date(date).toLocaleString();
let saved=[],current=null,request=0;
try{saved=parseSaved(localStorage.getItem(key),config.maxSavedCaptures);}catch{$('live-status').textContent='Saved captures could not be loaded. Current lookup remains available.';}
function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})),a=create('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function fields(container,rows){container.replaceChildren(...rows.flatMap(([name,value])=>[create('dt',name),create('dd',value||'Not returned')]));}
function comparison(before,after){const section=create('section',undefined,'live-comparison');section.append(create('h3','Compared with saved capture · '+stamp(before.fetched_at)));const diffs=changes(before.data,after.data);if(!diffs.length)section.append(create('p','No changes in the compared fields. This does not prove no filing or other event occurred.'));for(const diff of diffs){const row=create('div',undefined,'change');row.append(create('strong',diff.label),create('p','Saved: '+diff.before),create('p','Selected: '+diff.after));section.append(row);}return section;}
function render(response,isSaved=false){current=response;const d=response.data;$('live-results').hidden=false;$('live-name').textContent=d.legalName;$('live-date').textContent=(isSaved?'Saved capture':'API retrieval')+' · '+stamp(response.fetched_at)+' · Corporation '+d.id;$('save-capture').disabled=isSaved;
fields($('live-fields'),[['Legal status',human(d.status)],['Status detail',human(d.statusDetail)],['Other legal-name form',d.alternateLegalName],['Governing legislation',human(d.legislation)],['Corporation type',human(d.corporationType)],['Registered office locality',d.locality],['Incorporation effective date (returned filing)',incorporationDate(d)],['Anniversary (not necessarily incorporation)',d.anniversaryDate]]);
$('live-directors').textContent=d.directors==null?'Director details were not returned.':d.directors.length?d.directors.map(x=>x.name+(x.changeType?' · '+human(x.changeType):'')).join('\n'):'No director entries returned. This is not evidence that no directors exist.';
if(d.directorsTruncated)$('live-directors').append(document.createTextNode('\nShowing up to 200 directors. Consult the official record for full details.'));
$('live-returns').textContent=d.annualReturns==null?'Annual-return compliance was not returned.':d.annualReturns.map(x=>x.year+': '+human(x.status)).join('\n')||'No annual-return entries returned.';
$('live-control').textContent=d.controlStatements==null?'Significant-control statements were not returned.':d.controlStatements.map(x=>(x.names.join(' / ')||human(x.personType))+' · '+human(x.status)+' · statement '+(x.date||'date not returned')).join('\n')||'No person statements returned. Information may be exempt, withheld or unavailable; this is not a conclusion that there are no individuals with significant control.';
if(d.controlStatementsTruncated)$('live-control').append(document.createTextNode('\nThe source result exceeded this tool’s statement limit. Consult the official record.'));
$('live-filings').replaceChildren();if(d.filings==null)$('live-filings').append(create('p','Filing history was not returned.'));else {for(const f of [...d.filings].sort((a,b)=>(b.effectiveDate||b.receivedDate||'').localeCompare(a.effectiveDate||a.receivedDate||''))){const li=create('li');li.append(create('strong',human(f.type)),create('span',' · effective '+(f.effectiveDate||'not returned')+' · received '+(f.receivedDate||'not returned')+(f.year?' · year '+f.year:'')+(f.legalName?' · '+f.legalName:'')));$('live-filings').append(li);}if(!d.filings.length)$('live-filings').append(create('p','No filing entries returned.'));if(d.filingsTruncated)$('live-filings').append(create('p','Showing up to 500 source filings. Consult the official record for full history.'));}
const earlier=saved.filter(x=>x.data.id===d.id&&x.fetched_at<response.fetched_at).sort((a,b)=>b.fetched_at.localeCompare(a.fetched_at))[0];$('live-comparison').replaceChildren(...(earlier?[comparison(earlier,response)]:[create('p','Save a capture, then look up this corporation later to compare reported fields.')]));}
function renderSaved(){$('saved-captures').replaceChildren(...[...saved].reverse().map(c=>{const row=create('li');row.append(button(c.data.legalName+' · '+c.data.id+' · '+stamp(c.fetched_at),()=>{render(c,true);$('live-status').textContent='Viewing a dated saved capture. Use Look up for a current API retrieval.';$('live-id').value=c.data.id;$('live-kind').value='corporation';}));return row;}));$('saved-count').textContent=saved.length+' saved captures on this device (maximum '+config.maxSavedCaptures+').';$('export-saved').disabled=$('clear-saved').disabled=!saved.length;}
let businessManifest;
async function businessLookup(number) {
  businessManifest ||= fetch('./data/manifest.json',{signal:AbortSignal.timeout(30000)}).then(async response => {
    if (!response.ok) throw new Error('The federal business-number index could not be loaded.');
    return response.json();
  }).catch(error => { businessManifest=null; throw error; });
  const manifest = await businessManifest;
  const file = businessNumberFile(manifest,number);
  if (!file) return {ids:[],built:manifest.built};
  const response = await fetch(new URL('./data/'+file,import.meta.url),{signal:AbortSignal.timeout(30000)});
  if (!response.ok) throw new Error('The federal business-number index could not be loaded. Try again or search the legal name.');
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (bytes.length > 2_000_000) throw new Error('The business-number index exceeds its size limit.');
  const body = bytes[0] === 31 && bytes[1] === 139
    ? new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')))
    : new Response(bytes);
  const text = await body.text();
  if (text.length > 8_000_000) throw new Error('The business-number index exceeds its size limit.');
  return {ids:businessNumberMatches(JSON.parse(text),number),built:manifest.built};
}
function provincialLinks(number) {
  const section=$('live-matches');
  const bc=create('a','Search this business number in British Columbia');
  bc.href='./provinces.html?'+new URLSearchParams({province:'bc',q:number,historical:'false'});
  const other=create('a','Open Canada’s Business Registries');
  other.href='https://ised-isde.canada.ca/cbr-rec/en/';
  section.append(create('p','CRA business numbers are used by federal and provincial businesses. The federal register does not cover every Canadian business.'),bc,create('span',' · '),other);
}
export async function lookupCorporation(id,type='corporation') {
  // Invalidate any older response even when the new input is invalid.
  const token=++request;
  $('lookup').disabled=false;$('live-results').hidden=true;$('live-matches').replaceChildren();
  let identifier;
  try { identifier=parseIdentifier(id,type); }
  catch(error){$('live-status').textContent=error.message;return;}
  $('live-id').value=String(id).trim();$('live-kind').value=type;
  $('lookup').disabled=true;
  let corporation=identifier.value,matched='';
  try {
    if(identifier.type==='business') {
      $('live-status').textContent='Matching the CRA business number against the federal snapshot…';
      const match=await businessLookup(identifier.value);
      if(token!==request)return;
      provincialLinks(identifier.value);
      if(!match.ids.length) {
        $('live-status').textContent='No federal match for this CRA business number in the snapshot dated '+stamp(match.built)+'. This does not mean the business number is invalid. Try the provincial search below.';
        return;
      }
      if(match.ids.length>1) {
        $('live-status').textContent='The federal snapshot links this business number to more than one corporation. Choose a corporation number to inspect; no match has been assumed.';
        for(const candidate of match.ids)$('live-matches').append(button('Look up federal corporation '+candidate,()=>lookupCorporation(candidate,'corporation')));
        return;
      }
      corporation=match.ids[0];
      matched='CRA business number matched federal corporation '+corporation+' using the snapshot dated '+stamp(match.built)+'. ';
    }
    $('live-status').textContent=matched+'Requesting the current federal API record…';
    const response=await fetch(config.apiGateway+'/api/corporateghosts/corporation?'+new URLSearchParams({id:corporation}),{referrerPolicy:'no-referrer',signal:AbortSignal.timeout(30000)});
    const result=await response.json();
    if(!response.ok)throw new Error(result.error?.message||'The current federal record could not be loaded.');
    if(!validRecord(result)||Number(result.data.id)!==Number(corporation))throw new Error('The API returned an unexpected corporation record.');
    if(token!==request)return;
    render(result);
    $('live-status').textContent=matched+'Federal record retrieved. Detailed fields may be up to 15 minutes old at the source; gateway responses may be cached for five minutes.';
  }catch(error){
    if(token===request)$('live-status').textContent=error.name==='TimeoutError'?'The current lookup timed out. Snapshot search and saved captures remain available.':error.message;
  }finally{if(token===request)$('lookup').disabled=false;}
}
$('live-form').onsubmit=event=>{event.preventDefault();lookupCorporation($('live-id').value,$('live-kind').value);};
$('save-capture').onclick=()=>{if(!current)return;try{const next=addCapture(saved,current,config.maxSavedCaptures);const raw=JSON.stringify(next);if(raw.length>2_000_000)throw new Error('Saved captures exceed the device limit; export and clear older captures first.');localStorage.setItem(key,raw);saved=next;renderSaved();$('save-capture').disabled=true;$('live-status').textContent='Capture saved on this device with its original retrieval time.';}catch(error){$('live-status').textContent=error.message||'Device storage is unavailable.';}};
$('export-capture').onclick=()=>{if(current)download({tool:'Corporate Ghosts',notice:'Registry evidence does not verify website ownership or trustworthiness.',capture:current},'corporateghosts-'+current.data.id+'.json');};
$('export-saved').onclick=()=>download({tool:'Corporate Ghosts',captures:saved},'corporateghosts-saved-captures.json');
$('clear-saved').onclick=()=>{try{localStorage.removeItem(key);saved=[];renderSaved();$('live-status').textContent='Saved captures removed from this device.';}catch{$('live-status').textContent='Could not access device storage.';}};
renderSaved();
