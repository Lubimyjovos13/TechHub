const fs=require('fs'),path=require('path');
const src=fs.readFileSync('/app/frontend/src/i18n.js','utf8');
const m=src.match(/const resources = (\{[\s\S]*?\n\});/);
const resources=eval('('+m[1]+')');
const keys=new Set();
(function walk(d){for(const f of fs.readdirSync(d)){const p=path.join(d,f);if(fs.statSync(p).isDirectory())walk(p);else if(/\.(jsx?|tsx?)$/.test(f)){const s=fs.readFileSync(p,'utf8');for(const x of s.matchAll(/\bt\(\s*["'`]([a-zA-Z0-9_.\-]+)["'`]/g))keys.add(x[1]);}}})('/app/frontend/src');
const get=(o,k)=>k.split('.').reduce((a,b)=>a&&a[b],o);
for(const lang of ['en','ru']){const miss=[...keys].filter(k=>get(resources[lang].translation,k)===undefined);console.log(lang,miss.join(' '));}
