// A CRA business number identifies a business; it is not a federal corporation number.
// Resolve only exact matches published by ISED before requesting the current record.
export function parseIdentifier(input, type = 'auto') {
  if (!['auto', 'business', 'corporation'].includes(type)) throw new Error('Choose a supported number type.');
  const raw = String(input ?? '').trim();
  if (raw.length > 40) throw new Error('Enter a corporation number or nine-digit CRA business number.');
  const compact = raw.replace(/[\s-]/g, '').toUpperCase();
  const account = /^(\d{9})[A-Z]{2}\d{4}$/.exec(compact);
  if (type === 'business' || (type === 'auto' && (/^\d{9}$/.test(compact) || account))) {
    const value = account ? account[1] : compact;
    if (!/^\d{9}$/.test(value)) throw new Error('A CRA business number has nine digits; a program account may add two letters and four digits.');
    return {type:'business', value};
  }
  if (!/^\d{1,12}$/.test(compact)) throw new Error('Enter a federal corporation number or nine-digit CRA business number. Provincial IDs belong in the provincial search.');
  return {type:'corporation', value:compact};
}

export function businessSearchTerm(query) {
  try { const parsed = parseIdentifier(query); return parsed.type === 'business' ? parsed.value : null; }
  catch { return null; }
}

export function businessNumberFile(manifest, number) {
  if (!/^\d{9}$/.test(number)) throw new Error('Invalid business number.');
  const index = manifest?.business_numbers;
  if (index?.version !== 1 || index.prefix_length !== 3 || !index.shards || typeof index.shards !== 'object' || Array.isArray(index.shards)) {
    throw new Error('Business-number matching is unavailable in this snapshot. Try the legal name or federal corporation number.');
  }
  const prefix = number.slice(0,3);
  if (!Object.hasOwn(index.shards,prefix)) return null;
  const file = index.shards[prefix];
  if (typeof file !== 'string' || !new RegExp('^business-numbers-'+prefix+'-[a-f0-9]{16}\\.json\\.gz$').test(file)) throw new Error('The business-number index has an invalid file reference.');
  return file;
}

export function businessNumberMatches(document, number) {
  if (!/^\d{9}$/.test(number) || !document || typeof document !== 'object' || Array.isArray(document)) throw new Error('Invalid business-number index.');
  if (!Object.hasOwn(document,number)) return [];
  const ids = document[number];
  if (!Array.isArray(ids) || !ids.length || ids.length > 100 || ids.some(id => typeof id !== 'string' || !/^\d{1,12}$/.test(id))) throw new Error('The business-number index contains an invalid corporation reference.');
  return [...new Set(ids)];
}
