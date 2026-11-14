#!/usr/bin/env node
// Prueba la agenda en Chromium sin conexión, con una base de datos simulada hecha con los JSON de datos/.
// Uso, desde la raíz del repo:  node pruebas/pagina.js
// Recorre las 5 pestañas en modo claro y oscuro a 390, 360 y 320 px y comprueba: errores de JavaScript,
// scroll lateral, pestañas en una sola línea, que cada pestaña pinta algo, fotos que faltan y que la página
// no escribe en la base de datos. Deja capturas en pruebas/capturas/ y termina con «OK» o con los fallos.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const RAIZ = path.resolve(__dirname, '..');
const leer = (f) => JSON.parse(fs.readFileSync(path.join(RAIZ, 'datos', f), 'utf8'));
const DOCS = {
  'agenda/snapshot': leer('agenda.json'),
  'meta/atacantes': leer('atacantes-incursiones.json'),
  'meta/atacantes-max': leer('atacantes-max.json'),
  'meta/tanques-max': leer('tanques-max.json'),
  'meta/rocket': leer('rocket.json'),
  'meta/raids': leer('raids.json'),
};
const esc = (o) => JSON.stringify(o).replace(/</g, '\\u003c');
// Imita window.claude.use("db"); si la página intenta escribir, queda apuntado en window.__escrituras
const simulacion = '<script>(function(){var D=' + esc(DOCS) + ',w=window.__escrituras=[];' +
  'function s(p){var d=D[p];return {exists:!!d,data:function(){return d||null},metadata:{fromCache:false}}}' +
  'function anota(t,p){w.push(t+" "+p);return Promise.resolve()}' +
  'var db={doc:function(p){return {onSnapshot:function(cb){setTimeout(function(){cb(s(p))},50);return function(){}},' +
  'get:function(){return Promise.resolve(s(p))},set:function(){return anota("set",p)},' +
  'update:function(){return anota("update",p)},delete:function(){return anota("delete",p)}}}};' +
  'window.claude={use:async function(n){return n==="db"?db:null}};})();<\/script>';
const pagina = fs.readFileSync(path.join(RAIZ, 'pokemon-go-agenda', 'index.html'), 'utf8');
const PRUEBA = path.join(RAIZ, 'pokemon-go-agenda', '_prueba.html'); // junto a sprites2.webp, para que salgan las fotos
const CAPTURAS = path.join(__dirname, 'capturas');

// Qué se cuenta en cada pestaña
const PESTAÑAS = {
  agenda: '#view-agenda .item',
  pases: '#pay .payrow',
  atacantes: '#view-atacantes .ovc',
  raids: '#rd-body .rdc',
  rocket: '#rk-body .rkc',
};

async function caso(navegador, esquema, ancho) {
  const p = await navegador.newPage({ viewport: { width: ancho, height: 900 }, colorScheme: esquema });
  const errores = [];
  p.on('pageerror', (e) => errores.push(e.message));
  await p.goto('file://' + PRUEBA, { waitUntil: 'networkidle' }).catch(() => {});
  await p.waitForTimeout(800);
  const fallos = [];
  const tabs = await p.evaluate(() => {
    const t = document.querySelector('.tabs');
    const bs = [...t.querySelectorAll('.tab')];
    return { filas: new Set(bs.map((x) => Math.round(x.getBoundingClientRect().top))).size, sale: t.scrollWidth > t.clientWidth };
  });
  if (tabs.filas !== 1 || tabs.sale) fallos.push('las pestañas no caben en una línea');
  const cuenta = [];
  for (const [vista, sel] of Object.entries(PESTAÑAS)) {
    await p.click('#tab-' + vista);
    await p.waitForTimeout(250);
    const r = await p.evaluate((sel) => ({
      n: document.querySelectorAll(sel).length,
      sinFoto: document.querySelectorAll('.view:not([hidden]) .spr.none').length,
      lateral: document.documentElement.scrollWidth > window.innerWidth,
    }), sel);
    cuenta.push(vista + ' ' + r.n + (r.sinFoto ? ' (' + r.sinFoto + ' sin foto)' : ''));
    if (!r.n) fallos.push(vista + ': no pinta nada');
    if (r.lateral) fallos.push(vista + ': hay scroll lateral');
    await p.screenshot({ path: path.join(CAPTURAS, `${vista}-${esquema}-${ancho}.png`) });
  }
  // Atacantes: los tres modos (incursiones, Combates Max y tanques) caben en una línea y pintan algo
  await p.click('#tab-atacantes');
  const seg = await p.evaluate(() => new Set([...document.querySelectorAll('#atk-mode .seg-b')].map((b) => Math.round(b.getBoundingClientRect().top))).size);
  if (seg !== 1) fallos.push('los modos de Atacantes no caben en una línea');
  const sale = await p.evaluate(() => [...document.querySelectorAll('#atk-mode, #atk-mode .seg-b')].some((x) => x.scrollWidth > x.clientWidth + 1));
  if (sale) fallos.push('el texto de los modos de Atacantes se sale de su botón');
  for (const modo of ['raid', 'max', 'tank']) {
    await p.click(`#atk-mode [data-mode="${modo}"]`);
    await p.waitForTimeout(150);
    const ov = await p.evaluate(() => document.querySelectorAll('#view-atacantes .ovc').length);
    await p.click('#atk-types .f:nth-child(3)');
    await p.waitForTimeout(150);
    const r = await p.evaluate(() => ({ n: document.querySelectorAll('#atk-body .arow').length, lateral: document.documentElement.scrollWidth > window.innerWidth }));
    cuenta.push(modo + ' ' + ov + '/' + r.n);
    if (!ov || !r.n) fallos.push('atacantes ' + modo + ': no pinta nada');
    if (r.lateral) fallos.push('atacantes ' + modo + ': hay scroll lateral');
    if (await p.evaluate(() => [...document.querySelectorAll('#atk-mode, #atk-mode .seg-b')].some((x) => x.scrollWidth > x.clientWidth + 1))) fallos.push('atacantes ' + modo + ': el texto de los modos se sale o se corta');
    if (modo === 'tank') await p.screenshot({ path: path.join(CAPTURAS, `tanques-${esquema}-${ancho}.png`), fullPage: true });
    // General: 10 de todos los tipos
    await p.click('#atk-types .f:nth-child(2)');
    await p.waitForTimeout(150);
    const g = await p.evaluate(() => ({ txt: document.querySelector('#atk-types .f:nth-child(2)').textContent, n: document.querySelectorAll('#atk-body .arow').length, lateral: document.documentElement.scrollWidth > window.innerWidth }));
    cuenta[cuenta.length - 1] += '/' + g.n;
    if (g.txt !== 'General' || g.n !== 10) fallos.push('atacantes ' + modo + ': la lista General no tiene 10');
    if (g.lateral) fallos.push('atacantes ' + modo + ' general: hay scroll lateral');
    await p.screenshot({ path: path.join(CAPTURAS, `general-${modo}-${esquema}-${ancho}.png`), fullPage: true });
    await p.click('#atk-types .f:nth-child(1)');
  }
  const escrituras = await p.evaluate(() => window.__escrituras);
  if (escrituras.length) fallos.push('la página escribe en la base de datos: ' + escrituras.join(', '));
  if (errores.length) fallos.push('errores de JavaScript: ' + errores.join(' | '));
  await p.close();
  return { cuenta, fallos };
}

(async () => {
  fs.mkdirSync(CAPTURAS, { recursive: true });
  fs.writeFileSync(PRUEBA, '<!doctype html><html lang="es"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + simulacion + pagina + '</body></html>');
  const navegador = await chromium.launch();
  let fallos = 0;
  try {
    for (const esquema of ['light', 'dark']) {
      for (const ancho of [540, 430, 390, 360, 320]) {
        const r = await caso(navegador, esquema, ancho);
        fallos += r.fallos.length;
        console.log((esquema === 'light' ? 'claro ' : 'oscuro') + ' ' + ancho + ' px: ' + r.cuenta.join(' · ') +
          r.fallos.map((f) => '\n  FALLO ' + f).join(''));
      }
    }
  } finally {
    await navegador.close();
    fs.unlinkSync(PRUEBA);
  }
  console.log(fallos ? fallos + ' fallos' : 'OK');
  process.exit(fallos ? 1 : 0);
})();
