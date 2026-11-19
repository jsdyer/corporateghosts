const byId = id => document.getElementById(id);
const origin = 'https://orgbook.gov.bc.ca';
const form = byId('regional-form');
const province = byId('province');
const term = byId('term');
const historyField = byId('history');
const state = new URLSearchParams(location.search);
const pageSize = 10;
let current = 1;
let generation = 0;
let controller;
let coops;

function textElement(tag, value) {
  const el = document.createElement(tag);
  el.textContent = value;
  return el;
}

function recordCard(name, detail, url, label) {
  const card = document.createElement('article');
  card.className = 'panel record';
  const link = textElement('a', label);
  link.href = url;
  card.append(textElement('h3', name), textElement('p', detail), link);
  return card;
}

function explain() {
  const bc = province.value === 'bc';
  byId('status-field').hidden = !bc;
  byId('scope').textContent = bc
    ? 'Search by legal name or BC Registries ID. Each result opens the organization’s verified credentials.'
    : 'Search a co-operative name, registry ID, town or type. For other company types, use RJSC Connect below.';
  byId('example').textContent = bc ? 'Try historical telegraph companies' : 'Try Dartmouth housing co-ops';
  term.placeholder = bc ? 'Telegraph or BC0401241' : 'Dartmouth housing or 3057952';
}

function save() {
  const params = new URLSearchParams({province:province.value});
  if (term.value.trim()) params.set('q',term.value.trim());
  if (province.value === 'bc') params.set('historical',historyField.value);
  if (current > 1) params.set('page',String(current));
  window.history.replaceState(null,'','?' + params);
}

async function search(page = 1) {
  const request = ++generation;
  controller?.abort();
  controller = new AbortController();
  const q = term.value.trim();
  const bc = province.value === 'bc';
  current = page;
  save();
  const status = byId('result-status');
  const results = byId('matches');
  results.replaceChildren();
  byId('paging').hidden = true;
  if (bc && q.length < 2) {
    status.textContent = 'Enter at least two characters or try a historical telegraph company.';
    return;
  }
  status.textContent = 'Searching…';
  try {
    let cards, total, lastPage, source;
    if (bc) {
      const url = new URL('/api/v4/search/topic',origin);
      url.search = new URLSearchParams({q, inactive: historyField.value, page: String(page)});
      const response = await fetch(url,{signal:AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]),credentials:'omit'});
      if (!response.ok) throw Error('OrgBook BC returned HTTP ' + response.status);
      const data = await response.json();
      if (!Array.isArray(data.results) || !Number.isFinite(data.total)) throw Error('Unexpected OrgBook BC response');
      cards = data.results.map(row => {
        const name = row.names.find(n => n.type === 'entity_name')?.text || row.names[0]?.text || row.source_id;
        const detail = [row.source_id, row.inactive ? 'Historical registration' : 'Current registration'];
        const registered = row.attributes.find(a => a.type === 'registration_date')?.value;
        if (registered) detail.push('Registered ' + registered.slice(0,10));
        return recordCard(name,detail.join(' · '),origin + '/en/organization/' + encodeURIComponent(row.source_id),'Open OrgBook record ↗');
      });
      total = data.total;
      lastPage = Math.ceil(total/data.page_size);
      source = 'OrgBook BC';
    } else {
      if (!coops) {
        const response = await fetch('./ns-coops.json');
        if (!response.ok) throw Error('Could not load the NS edition');
        coops = await response.json();
      }
      const norm = s => s.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase();
      const words = norm(q).split(/\s+/).filter(Boolean);
      const matched = coops.rows.filter(row => words.every(w => norm(row.join(' ')).includes(w)));
      total = matched.length;
      lastPage = Math.ceil(total/pageSize);
      current = Math.min(page,Math.max(lastPage,1));
      cards = matched.slice((current-1)*pageSize,current*pageSize).map(([id,name,town,date,type,profit]) =>
        recordCard(name,[id,town,type,{N:'Non-profit',P:'For-profit'}[profit],date && 'Incorporated ' + date].filter(Boolean).join(' · '),'https://rjsc.novascotia.ca/','Look up this ID in RJSC Connect ↗'));
      source = coops.count + ' NS co-operatives listed ' + coops.as_of;
    }
    if (request !== generation) return;
    results.replaceChildren(...cards);
    status.textContent = total.toLocaleString() + ' matching records · ' + source + (total ? '' : '. Try another name, registry or status.');
    byId('paging').hidden = lastPage < 2;
    byId('page').textContent = 'Page ' + current + ' of ' + Math.max(1,lastPage);
    byId('prev').disabled = current === 1;
    byId('next').disabled = current >= lastPage;
    save();
  } catch (error) {
    if (request === generation) {
      status.textContent = 'Could not complete the search. Try again or open the source register below.';
    }
  }
}

province.value = state.get('province') === 'ns' ? 'ns' : 'bc';
term.value = (state.get('q') || '').slice(0,120);
historyField.value = state.get('historical') === 'false' ? 'false' : 'true';
form.addEventListener('submit', e => {e.preventDefault(); search();});
province.addEventListener('change', () => {term.value = ''; explain(); search();});
historyField.addEventListener('change', () => search());
byId('example').addEventListener('click', () => {
  term.value = province.value === 'bc' ? 'telegraph' : 'Dartmouth housing';
  historyField.value = 'true';
  search();
});
byId('prev').addEventListener('click', () => search(current-1));
byId('next').addEventListener('click', () => search(current+1));
explain();
search(Math.max(1,Math.floor(Number(state.get('page')) || 1)));
