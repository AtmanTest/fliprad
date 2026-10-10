/* FlipRadar — moteur 100 % navigateur (aucun serveur). Données dans localStorage.
   Port fidèle du moteur Python d'origine. Aucune donnée de démo : la base démarre vide. */
(() => {
'use strict';
const COND_FACTOR = {neuf:1.0, bon:0.88, use:0.75, degrade:0.55};
const COND_LABEL = {neuf:'Neuf / scellé', bon:'Bon état', use:'Usagé', degrade:'Dégradé / incomplet'};
const SOLD = ['vendu','achat_en_cours'], WINDOW_DAYS = 120, KEY = 'fliprad.v2';

// slug, nom, catégorie, activée, sûreté, fee%, emballage, remise en état, livraison défaut, note
const NICHES = [
 ['lego','LEGO neuf scellé','Loisirs',1,90,0,4,0,5.5,'Référence unique, aucun test, valeur stable. Risque : fausse boîte rescellée.'],
 ['outils','Outils électroportatifs de marque','Matériel pro',1,78,0,3,0,7,'Demande constante, modèles robustes. Risque : usure moteur, batteries non fournies.'],
 ['pc-pro','PC portables pro reconditionnables','Électronique',1,66,0,5,12,8,'Modèles très documentés. Risques : batterie, verrou BIOS/MDM, écran.'],
 ['smartphones','Smartphones','Électronique',0,38,0,3,10,6,'Verrous iCloud/SIM, batterie, contrefaçons : retours fréquents.'],
 ['mode','Vêtements & chaussures','Mode',0,35,0,2,3,5,'Tailles, contrefaçon, retours élevés.'],
 ['maison','Meubles & électroménager','Maison & Jardin',0,40,0,0,0,0,'Encombrement, pannes cachées, transport.'],
 ['famille','Famille & puériculture','Famille',0,45,0,3,3,6,'Normes de sécurité, usure, demande saisonnière.'],
 ['emploi','Emploi','Emploi',0,0,0,0,0,0,'Pas de flip possible : catégorie exclue du scoring.'],
 ['autres','Autres','Autres',0,30,0,3,0,6,'Trop hétérogène pour un scoring fiable.'],
].map(r => ({slug:r[0],name:r[1],category:r[2],enabled:r[3],safety:r[4],fee_pct:r[5],pack_cost:r[6],prep_cost:r[7],delivery_default:r[8],note:r[9]}));

// key, niche, nom, regex, prix neuf indicatif (null si modèle abandonné)
const P = (key,niche,name,pats,newp) => ({key,niche,name,pats:pats.map(x=>new RegExp(x)),newp});
const PRODUCTS = [
 P('lego-75192','lego','LEGO Star Wars 75192 Faucon Millenium UCS',['\\b75192\\b'],849.99),
 P('lego-75313','lego','LEGO Star Wars 75313 AT-AT UCS',['\\b75313\\b'],849.99),
 P('lego-10276','lego','LEGO Icons 10276 Colisée',['\\b10276\\b'],549.99),
 P('lego-21322','lego','LEGO Ideas 21322 Barracuda Bay',['\\b21322\\b'],199.99),
 P('lego-10281','lego','LEGO Icons 10281 Bonsaï',['\\b10281\\b'],49.99),
 P('lego-42115','lego','LEGO Technic 42115 Lamborghini Sián',['\\b42115\\b'],449.99),
 P('lego-10305','lego','LEGO Icons 10305 Château des Chevaliers du Lion',['\\b10305\\b'],399.99),
 P('lego-76240','lego','LEGO Batman 76240 Batmobile Tumbler',['\\b76240\\b'],229.99),
 P('makita-dhp484','outils','Makita DHP484 perceuse-visseuse 18V',['\\bdhp\\s?484\\b'],140),
 P('makita-dtw1002','outils','Makita DTW1002 boulonneuse 1/2" 18V',['\\bdtw\\s?1002\\b'],290),
 P('dewalt-dcd796','outils','DeWalt DCD796 perceuse-visseuse 18V',['\\bdcd\\s?796\\b'],150),
 P('dewalt-dcf887','outils','DeWalt DCF887 visseuse à chocs 18V',['\\bdcf\\s?887\\b'],140),
 P('milwaukee-fpd3','outils','Milwaukee M18 FPD3 perceuse à percussion',['\\bm18\\s?fpd\\s?[23]?\\b'],200),
 P('milwaukee-fid3','outils','Milwaukee M18 FID3 visseuse à chocs',['\\bm18\\s?fid\\s?[23]?\\b'],190),
 P('bosch-gsr1855','outils','Bosch Professional GSR 18V-55',['\\bgsr\\s?18\\s?v?\\s?-?\\s?55\\b'],150),
 P('bosch-gbh1826','outils','Bosch Professional GBH 18V-26 perforateur',['\\bgbh\\s?18\\s?v?\\s?-?\\s?26\\b'],260),
 P('tp-x395','pc-pro','Lenovo ThinkPad X395',['\\bx\\s?395\\b'],null),
 P('tp-t480','pc-pro','Lenovo ThinkPad T480',['\\bt\\s?480\\b(?!\\s?s)'],null),
 P('tp-t14g2','pc-pro','Lenovo ThinkPad T14 Gen 2',['\\bt14\\b.{0,12}\\bgen\\s?2\\b','\\bt14\\s?g2\\b'],null),
 P('tp-x1c7','pc-pro','Lenovo ThinkPad X1 Carbon Gen 7',['\\bx1\\s?carbon\\b.{0,12}\\b(gen\\s?7|7th|7eme)\\b','\\bx1\\s?carbon\\s?g7\\b'],null),
 P('dell-5420','pc-pro','Dell Latitude 5420',['\\blatitude\\s?5420\\b'],null),
 P('dell-7420','pc-pro','Dell Latitude 7420',['\\blatitude\\s?7420\\b'],null),
 P('hp-840g7','pc-pro','HP EliteBook 840 G7',['\\belitebook\\s?840\\s?g\\s?7\\b'],null),
];
const PBY = Object.fromEntries(PRODUCTS.map(p => [p.key, p]));

const DEFAULTS = {buy_mode:'delivery', travel_cost:3, min_margin:15, target_roi:.2, w_speed:.25, w_conf:.25};
const now = () => Math.floor(Date.now()/1000);
const clamp = (x,lo=0,hi=1) => Math.max(lo, Math.min(hi, x));
const median = a => { if(!a.length) return null; const s=[...a].sort((x,y)=>x-y), m=s.length>>1; return s.length%2? s[m] : (s[m-1]+s[m])/2; };
const pct = (a,q) => { if(!a.length) return null; const s=[...a].sort((x,y)=>x-y), i=(s.length-1)*q, lo=Math.floor(i), hi=Math.min(lo+1,s.length-1); return s[lo]+(s[hi]-s[lo])*(i-lo); };
const norm = s => (s||'').normalize('NFKD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();

// ---------- état + persistance ----------
let S;
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch(e) {} };
function load() {
  try { const j = localStorage.getItem(KEY); if (j) { S = JSON.parse(j); return; } } catch(e) {}
  S = {niches: JSON.parse(JSON.stringify(NICHES)), settings: {...DEFAULTS}, listings: [], deals: [], nextId: 1, nextDeal: 1};
  save();
}

// ---------- normalisation ----------
function matchProduct(text) { const t = norm(text); const p = PRODUCTS.find(p => p.pats.some(r => r.test(t))); return p ? p.key : null; }
function detectCondition(text, niche) {
  const t = norm(text);
  if (niche === 'lego') return (/incomplet|manque|sans notice|sans boite|vrac|monte|deballe|ouvert/.test(t) && !t.includes('jamais ouvert')) ? 'degrade' : 'neuf';
  if (/neuf|scelle|jamais utilise|sous blister/.test(t)) return 'neuf';
  if (/incomplet|rayure|marque|abime|usure|use|etat correct|bon etat general/.test(t) && !t.includes('tres bon etat')) return 'use';
  if (/degrade|casse/.test(t)) return 'degrade';
  return 'bon';
}
const BLOCKING = /pour pieces|hors service|\bhs\b|ne demarre|ne s allume|ne fonctionne pas|en panne|casse|fissure|a reparer|icloud|bloque|verrouille par/;
const OFFPLAT = /paypal|western union|mandat|virement|whatsapp|hors leboncoin|lien de paiement|ami famille/;
function detectRisks(text, price, med, niche, reviews, rating) {
  const t = norm(text), out = [], add = (label, weight, blocking=false) => out.push({label, weight, blocking});
  if (BLOCKING.test(t)) add('Défaut ou blocage déclaré (pièces / HS / verrou)', .5, true);
  if (OFFPLAT.test(t)) add('Paiement ou contact hors plateforme : arnaque probable', .4);
  if (med && price && price < .55*med) add('Prix très inférieur au marché : arnaque ou défaut caché possible', .25);
  if (reviews === 0) add('Vendeur sans aucun avis', .1);
  else if (rating != null && reviews >= 5 && rating < 4) add(`Vendeur mal noté (${rating.toFixed(1)}/5)`, .1);
  if (niche === 'pc-pro') {
    if (/bios|mot de passe|mdm|compte administrateur|verrou/.test(t)) add('Verrou BIOS / MDM possible : à vérifier avant achat', .3);
    if (/batterie (hs|usee|faible|a changer)/.test(t)) add('Batterie à remplacer (coût à prévoir)', .15);
    if (t.includes('sans chargeur')) add('Sans chargeur (≈ 15–25 € à ajouter)', .05);
  }
  if (niche === 'lego') {
    if (/boite abimee|boite ecrasee|coin ecrase/.test(t)) add('Boîte abîmée : revente un peu plus basse', .05);
    if (/replica|compatible|type lego|moc\b/.test(t)) add('Contrefaçon / compatible possible', .5, true);
  }
  return out;
}

// ---------- contexte + valorisation ----------
function context() {
  const ctx = {settings: S.settings, now: now(), niches: Object.fromEntries(S.niches.map(n => [n.slug, n])), sold: {}, active: {}, _st: {}};
  const horizon = ctx.now - WINDOW_DAYS*86400;
  for (const r of S.listings) {
    if (!r.product_key || !(r.price > 0)) continue;
    const f = COND_FACTOR[r.condition] || .88;
    if (SOLD.includes(r.status) && r.sold_at && r.sold_at >= horizon)
      (ctx.sold[r.product_key] ||= []).push({id:r.id, price:r.price, norm:r.price/f, status:r.status, days:Math.max(0,(r.sold_at-r.first_seen)/86400), sold_at:r.sold_at, condition:r.condition});
    else if (r.status === 'active' && !r.ignored) (ctx.active[r.product_key] ||= []).push(r.price/f);
  }
  return ctx;
}
function stats(ctx, key) {
  if (ctx._st[key]) return ctx._st[key];
  const s = ctx.sold[key] || [], a = ctx.active[key] || [], norms = s.map(x=>x.norm), n = s.length;
  return ctx._st[key] = {n, n_vendu:s.filter(x=>x.status==='vendu').length, median:median(norms), p25:pct(norms,.25), p75:pct(norms,.75),
    days:s.length? median(s.map(x=>x.days)) : null,
    sold30:s.filter(x=>x.sold_at>=ctx.now-30*86400).length, sold90:s.filter(x=>x.sold_at>=ctx.now-90*86400).length,
    active_n:a.length, active_median:median(a), active_p25:pct(a,.25),
    confidence:n>=10?'haute':n>=4?'moyenne':'basse'};
}
function valuation(ctx, key, cond) {
  const st = stats(ctx,key), f = COND_FACTOR[cond]||.88, newp = PBY[key].newp;
  if (st.n >= 3) return {mid:st.median*f, low:st.p25*f, high:st.p75*f, basis:'observé', label:`${st.n} ventes observées (badges Vendu / Achat en cours), 120 j`, n:st.n, confidence:st.confidence};
  if (st.active_n >= 3) { const m = st.active_median*.9*f; return {mid:m, low:m*.9, high:m*1.1, basis:'estimé', label:`Estimé : médiane des ${st.active_n} annonces actives −10 % (aucune vente observée)`, n:0, confidence:'basse'}; }
  if (newp) { const m = newp*.6*f; return {mid:m, low:m*.85, high:m*1.15, basis:'estimé', label:'Estimé : 60 % du prix neuf indicatif (très peu de données)', n:0, confidence:'basse'}; }
  return null;
}
function maxBuy(ctx, resale, niche) {
  const s = ctx.settings, sellNet = resale*(1-niche.fee_pct/100) - niche.pack_cost - niche.prep_cost;
  const base = sellNet - (s.buy_mode==='delivery' ? niche.delivery_default : s.travel_cost);
  return Math.max(0, Math.min(base/(1+s.target_roi), base - s.min_margin));
}
const r2 = x => Math.round(x*100)/100;

function analyze(ctx, l) {
  const key = l.product_key, niche = l.niche ? ctx.niches[l.niche] : null, res = {id:l.id, analyzable:false};
  if (!key || !niche) { res.reason = 'Modèle non reconnu dans le catalogue'; return res; }
  const cond = l.condition || 'bon', val = valuation(ctx, key, cond);
  if (!val) { res.reason = 'Pas assez de données pour valoriser ce modèle'; return res; }
  const st = stats(ctx,key), s = ctx.settings, price = l.price, bfee = l.buyer_fee || 0;
  const delivery = s.buy_mode==='delivery' ? (l.delivery_fee != null ? l.delivery_fee : niche.delivery_default) : s.travel_cost;
  const acq = price + bfee + delivery, fee = val.mid*niche.fee_pct/100;
  const net = val.mid - fee - niche.pack_cost - niche.prep_cost - acq, roi = acq ? net/acq : 0;
  const risks = detectRisks(`${l.title||''} ${l.description||''}`, price, val.mid, niche.slug, l.seller_reviews, l.seller_rating);
  const risk = clamp(risks.reduce((a,r)=>a+r.weight,0), 0, .8), blocking = risks.some(r=>r.blocking);
  const days = st.days != null ? st.days : 30;
  let marginC = clamp(roi/.35);
  if (net < s.min_margin) marginC *= net > 0 ? clamp(net/s.min_margin) : 0;
  const speedC = clamp(1 - days/45);
  let confC = {haute:1, moyenne:.6, basse:.3}[val.confidence]; if (val.basis==='estimé') confC = Math.min(confC,.25);
  const base = Math.max(0, 1 - s.w_speed - s.w_conf);
  const score = 100*marginC*(base + s.w_speed*speedC + s.w_conf*confC)*(1-risk);
  const mb = maxBuy(ctx, val.mid, niche), age = (ctx.now - (l.first_seen||ctx.now))/86400, offer = mb > 0 ? Math.min(price, Math.round(mb)) : null;
  const fmt = n => Math.round(n);
  Object.assign(res, {analyzable:true, product:{key, name:PBY[key].name}, niche:niche.slug, condition:cond, condition_label:COND_LABEL[cond]||cond,
    resale:{...val, mid:r2(val.mid), low:r2(val.low), high:r2(val.high)},
    costs:{price, buyer_fee:bfee, delivery, acquisition:r2(acq), resale_fee:r2(fee), packaging:niche.pack_cost, prep:niche.prep_cost},
    net:r2(net), roi:Math.round(roi*1000)/1000, days_to_sell: st.days!=null? Math.round(days*10)/10 : null,
    score:Math.round(score*10)/10, risk:r2(risk), risks, blocking, max_buy:r2(mb), offer, age_days:Math.round(age*10)/10, confidence:val.confidence,
    why:[`Revente estimée ${fmt(val.mid)} € (${val.basis}) — ${val.label}.`,
      `Coût total d'acquisition ${fmt(acq)} € (prix ${fmt(price)} + frais ${bfee.toFixed(2)} + livraison/déplacement ${delivery.toFixed(2)}), frais de revente et préparation ${fmt(fee+niche.pack_cost+niche.prep_cost)} € → marge nette ${fmt(net)} € (${fmt(roi*100)} %).`,
      (st.days!=null ? `Vend en ~${fmt(days)} j (médiane observée), ` : 'Délai de vente inconnu (30 j supposés), ') + (risks.length ? `${risks.length} risque(s) relevé(s).` : 'aucun risque détecté.')],
    message: offer ? `Bonjour, votre annonce « ${l.title||''} » est-elle toujours disponible ? Je suis intéressé et peux vous proposer ${offer} € avec paiement via la plateforme. Cordialement.` : null});
  return res;
}
function salesRanking(ctx, slug) {
  const niche = ctx.niches[slug], rows = [], cf = COND_FACTOR[slug==='lego'?'neuf':'bon'];
  for (const p of PRODUCTS) {
    if (p.niche !== slug) continue;
    const st = stats(ctx,p.key); if (!st.n && !st.active_n) continue;
    const val = valuation(ctx, p.key, slug==='lego'?'neuf':'bon'); if (!val) continue;
    const mid = val.mid, mb = maxBuy(ctx, mid, niche), ask = st.active_p25 ? st.active_p25*cf : mid*.85;
    const acq = ask + (ctx.settings.buy_mode==='delivery' ? niche.delivery_default : ctx.settings.travel_cost);
    const net = mid*(1-niche.fee_pct/100) - niche.pack_cost - niche.prep_cost - acq, roi = acq ? net/acq : 0;
    const days = st.days != null ? st.days : 30, tot = st.sold30 + st.active_n;
    const conf = val.basis==='observé' ? {haute:1, moyenne:.75, basse:.4}[val.confidence] : .3;
    const score = 100*(.4*clamp(1-days/45) + .3*clamp(st.sold30/8) + .3*clamp(roi/.35))*conf;
    rows.push({key:p.key, name:p.name, score:Math.round(score*10)/10, basis:val.basis, confidence:val.confidence, sold30:st.sold30, sold90:st.sold90,
      days_to_sell: st.days!=null? Math.round(st.days*10)/10 : null, median_sold:r2(mid), p25:r2(val.low), p75:r2(val.high),
      active_n:st.active_n, ask_p25:r2(ask), net_at_ask:r2(net), roi:Math.round(roi*1000)/1000, max_buy:r2(mb), sale_rate: tot? st.sold30/tot : 0});
  }
  return rows.sort((a,b)=>b.score-a.score);
}
function safetyMeasured(ctx, slug) {
  const disp = [], rate = [];
  for (const p of PRODUCTS) { if (p.niche !== slug) continue; const st = stats(ctx,p.key);
    if (st.n >= 4 && st.median) disp.push((st.p75-st.p25)/st.median);
    const tot = st.sold30 + st.active_n; if (tot) rate.push(st.sold30/tot); }
  if (!disp.length) return null;
  const d = disp.reduce((a,b)=>a+b,0)/disp.length, r = rate.length ? rate.reduce((a,b)=>a+b,0)/rate.length : 0;
  return Math.round(100*(.6*(1-clamp(d/.4)) + .4*clamp(r/.5)));
}

// ---------- ingestion ----------
const STATUS = {'':'active', active:'active', 'en ligne':'active', 'achat en cours':'achat_en_cours', achat_en_cours:'achat_en_cours', vendu:'vendu', sold:'vendu'};
function upsert(d) {
  const t = now(), text = `${d.title} ${d.description||''}`, key = d.product_key || matchProduct(text), niche = key ? PBY[key].niche : null;
  const cond = d.condition || (niche ? detectCondition(text, niche) : 'bon');
  const status = STATUS[(d.status||'').trim().toLowerCase().replace(/\s+/g,' ')] || 'active';
  const row = S.listings.find(r => r.source===d.source && r.ext_id===d.ext_id);
  if (!row) {
    S.listings.push({id:S.nextId++, source:d.source, ext_id:d.ext_id, url:d.url||'', title:d.title, description:d.description||'', price:d.price, status,
      location:d.location||'', condition:cond, product_key:key, niche, seller_rating:d.seller_rating??null, seller_reviews:d.seller_reviews??null,
      delivery_fee:d.delivery_fee??null, buyer_fee:d.buyer_fee||0, first_seen:d.first_seen||t, last_seen:t,
      sold_at: d.sold_at || (status!=='active' ? t : null), ignored:0});
    return 'new';
  }
  const changed = row.price !== d.price || row.status !== status;
  row.price = d.price; row.status = status; row.last_seen = t; row.sold_at = row.sold_at || (status!=='active' ? t : null);
  if (key) { row.product_key = key; row.niche = niche; }
  return changed ? 'updated' : 'unchanged';
}

// ---------- import manuel ----------
const toFloat = x => { if (x==null || String(x).trim()==='') return null; const v = parseFloat(String(x).replace(/[^0-9,.\-]/g,'').replace(',','.')); return isNaN(v)? null : v; };
function parseImport(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean); if (!lines.length) return [];
  const delim = lines[0].includes('\t') ? '\t' : ';', out = [];
  lines.forEach((line, i) => {
    const c = line.split(delim).map(x=>x.trim()); if (!c[0]) return;
    if (i===0 && ['titre','title'].includes(c[0].toLowerCase())) return;
    while (c.length < 8) c.push('');
    const [title, price, status, url, loc, cond, reviews, desc] = c, p = toFloat(price); if (p == null) return;
    let h = 0; for (const ch of `${title}|${p}|${loc}`) h = (h*31 + ch.charCodeAt(0))|0;
    out.push({source:'import-manuel', ext_id:url || ('h'+(h>>>0).toString(16)), url, title, price:p, status, location:loc, condition:cond||null, seller_reviews:/^\d+$/.test(reviews)? +reviews : null, description:desc});
  });
  return out;
}

// ---------- « API » locale (mêmes routes que l'ancien serveur) ----------
const STAGES = ['repere','contacte','achete','en_vente','vendu'];
function viewListing(ctx, r, withComps) {
  const a = analyze(ctx, r), o = {...r, analysis:a};
  if (withComps && a.analyzable) o.comps = [...(ctx.sold[r.product_key]||[])].sort((x,y)=>y.sold_at-x.sold_at).slice(0,10)
    .map(c => ({price:c.price, status:c.status, days:Math.round(c.days*10)/10, sold_ago:Math.round((ctx.now-c.sold_at)/86400*10)/10, condition:COND_LABEL[c.condition]}));
  return o;
}
function dealsView() {
  const st = {realised:0, count_sold:0, capital:0}, items = [...S.deals].sort((a,b)=>b.updated-a.updated).map(d => {
    d = {...d};
    if (d.stage==='vendu' && d.buy_price!=null && d.sell_price!=null) { d.real_net = r2(d.sell_price-d.buy_price); st.realised += d.real_net; st.count_sold++; }
    else if (['achete','en_vente'].includes(d.stage) && d.buy_price) st.capital += d.buy_price;
    return d; });
  st.realised = r2(st.realised); return {items, stats:st, stages:STAGES};
}
async function api(path, o) {
  const [p, qs] = path.split('?'), q = new URLSearchParams(qs||''), m = (o && o.m) || 'GET', b = (o && o.b) || {};
  let x;
  if (m==='GET') {
    if (p==='/niches') { const ctx = context();
      return S.niches.map(n => { const it = {...n};
        if (n.enabled) { const rows = S.listings.filter(r => r.niche===n.slug && r.status==='active' && !r.ignored); let best = null, deals = 0;
          for (const r of rows) { const a = analyze(ctx,r); if (a.analyzable && !a.blocking && a.net>0) { deals++; if (!best || a.score>best.a.score) best = {r,a}; } }
          Object.assign(it, {active:rows.length, deals, sold30:PRODUCTS.filter(p=>p.niche===n.slug).reduce((s,p)=>s+stats(ctx,p.key).sold30,0), safety_measured:safetyMeasured(ctx,n.slug),
            best: best ? {id:best.r.id, title:best.r.title, net:best.a.net, score:best.a.score} : null}); }
        return it; }).sort((a,b)=>b.enabled-a.enabled || b.safety-a.safety); }
    if (x = p.match(/^\/niche\/([\w-]+)\/buys$/)) { const ctx = context(), mp = +q.get('max_price')||0, mm = +q.get('min_margin')||0, res = [];
      for (const r of S.listings) { if (r.niche!==x[1] || r.status!=='active' || r.ignored || (mp && r.price>mp)) continue;
        const v = viewListing(ctx,r), a = v.analysis; if (!a.analyzable || a.blocking || a.net<mm || a.net<=0) continue; res.push(v); }
      res.sort((a,b)=>b.analysis.score-a.analysis.score); return {items:res.slice(0,10), total_candidates:res.length}; }
    if (x = p.match(/^\/niche\/([\w-]+)\/sales$/)) return {items:salesRanking(context(), x[1]).slice(0,10)};
    if (x = p.match(/^\/listing\/(\d+)$/)) { const r = S.listings.find(r=>r.id===+x[1]); if (!r) throw new Error('introuvable'); return viewListing(context(), r, true); }
    if (p==='/settings') return {...S.settings};
    if (p==='/deals') return dealsView();
    if (p==='/sources') { const g = {}; for (const r of S.listings) { const e = g[r.source] ||= {source:r.source, n:0, last:0}; e.n++; e.last = Math.max(e.last, r.last_seen); } return Object.values(g); }
  }
  if (m==='POST') {
    if (p==='/settings') { for (const k in b) if (k in DEFAULTS) S.settings[k] = typeof DEFAULTS[k]==='string' ? String(b[k]) : parseFloat(b[k]); save(); return {...S.settings}; }
    if (p==='/analyze') { const title = (b.title||'').trim(), price = toFloat(b.price); if (!title || price==null) throw new Error('titre et prix requis');
      const text = `${title} ${b.description||''}`, key = matchProduct(text), niche = key ? PBY[key].niche : null, ctx = context();
      return {title, price, analysis:analyze(ctx, {id:null, title, description:b.description||'', price, product_key:key, niche, condition:b.condition || (niche? detectCondition(text,niche):'bon'),
        seller_reviews:toFloat(b.reviews), seller_rating:null, delivery_fee:toFloat(b.delivery_fee), buyer_fee:0, first_seen:now()})}; }
    if (p==='/reset') { localStorage.removeItem(KEY); load(); return {ok:true}; }
    if (p==='/import') { const items = parseImport(b.text||''), c = {new:0, updated:0, unchanged:0, unrecognized:0};
      for (const d of items) { c[upsert(d)]++; if (!matchProduct(`${d.title} ${d.description||''}`)) c.unrecognized++; } save(); return {parsed:items.length, ...c}; }
    if (x = p.match(/^\/listing\/(\d+)\/ignore$/)) { const r = S.listings.find(r=>r.id===+x[1]); if (r) r.ignored = 1; save(); return {ok:true}; }
    if (p==='/deals') { const t = now(); S.deals.push({id:S.nextDeal++, listing_id:b.listing_id, title:b.title||'', stage:'repere', est_net:b.est_net, buy_price:b.buy_price, sell_price:null, notes:'', created:t, updated:t}); save(); return dealsView(); }
  }
  if (m==='PATCH') {
    if (x = p.match(/^\/deals\/(\d+)$/)) { const d = S.deals.find(d=>d.id===+x[1]); if (!d) throw new Error('introuvable');
      for (const k of ['stage','buy_price','sell_price','notes']) if (k in b) { if (k==='stage' && !STAGES.includes(b[k])) throw new Error('étape invalide');
        d[k] = (k==='buy_price'||k==='sell_price') ? toFloat(b[k]) : b[k]; }
      d.updated = now(); save(); return dealsView(); }
    if (x = p.match(/^\/niche\/([\w-]+)$/)) { const n = S.niches.find(n=>n.slug===x[1]); if (n) for (const k of ['fee_pct','pack_cost','prep_cost','delivery_default','enabled']) if (k in b) n[k] = parseFloat(b[k]) || 0; save(); return {ok:true}; }
  }
  if (m==='DELETE' && (x = p.match(/^\/deals\/(\d+)$/))) { S.deals = S.deals.filter(d=>d.id!==+x[1]); save(); return dealsView(); }
  throw new Error('route inconnue');
}
load();
// Données collectées par le cron GitHub Actions (alertes e-mail) : docs/data/listings.json
const ready = fetch('data/listings.json', {cache:'no-store'}).then(r => r.ok ? r.json() : []).then(items => {
  let n = 0; for (const d of items) if (d && d.ext_id && d.title && d.price > 0) { if (upsert(d) === 'new') n++; } if (n) save(); }).catch(() => {});
const apiReady = async (p, o) => { await ready; return api(p, o); };
window.FlipAPI = apiReady;
window.FlipEngine = {matchProduct, detectCondition, detectRisks, analyze, context, upsert, parseImport, norm};
})();
