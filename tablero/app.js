/* Tablero de administración de Asistime.
   Lee el libro central (Supabase de la casa) con un usuario logueado cuyo
   email esté en `administradores`. Sin sesión, la base no devuelve nada:
   la clave de acá abajo es la pública (anon) y sola no abre ninguna tabla. */
'use strict';

const URL_CASA = 'https://qxjvtxumkljsroukpkny.supabase.co';
const CLAVE_PUBLICA = 'sb_publishable_VXij76kntB3NPIb8HbBg3w_zxEWU7Ux';
const PISO_USD = 1.5;               // el mismo de app/cobro.py
const LATIDO_VIEJO_MIN = 10;
const TIPOS = ['placa', 'reel', 'video', 'foto', 'publicacion'];
const NOMBRE_TIPO = { placa: 'Placas', reel: 'Reels', video: 'Videos', foto: 'Fotos', publicacion: 'Publicaciones' };

const sb = supabase.createClient(URL_CASA, CLAVE_PUBLICA);
const app = document.getElementById('app');

const D = { clientes: [], saldos: [], libroMes: [], infraMes: [], latidos: [], cargas: [],
            cierres: [], infra: [], libro: [], sesion: null };
let mesSel = mesDe(new Date());

// ── utilidades ─────────────────────────────────────────────────────────
function mesDe(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`; }
function mesAnterior(m) { const d = new Date(m + 'T00:00:00'); d.setMonth(d.getMonth() - 1); return mesDe(d); }
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
function nombreMes(m) { const [a, mm] = m.split('-'); return `${MESES[+mm - 1]} ${a}`; }
function mesDeFecha(ts) { return ts ? ts.slice(0, 7) + '-01' : null; }
function usd(x, dec = 2) { return 'US$ ' + (+x || 0).toLocaleString('es-UY', { minimumFractionDigits: dec, maximumFractionDigits: dec }); }
function num(x, dec = 0) { return (+x || 0).toLocaleString('es-UY', { minimumFractionDigits: dec, maximumFractionDigits: dec }); }
function pct(x) { return isFinite(x) ? num(x * 100, 0) + ' %' : '—'; }
function fecha(ts) { return ts ? new Date(ts).toLocaleDateString('es-UY', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—'; }
function fechaHora(ts) { return ts ? new Date(ts).toLocaleString('es-UY', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'; }
function hace(ts) {
  if (!ts) return 'nunca';
  const m = Math.round((Date.now() - new Date(ts)) / 60000);
  if (m < 1) return 'recién'; if (m < 60) return `hace ${m} min`;
  const h = Math.round(m / 60); if (h < 48) return `hace ${h} h`;
  return `hace ${Math.round(h / 24)} días`;
}
function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function suma(arr, k) { return arr.reduce((a, r) => a + (+r[k] || 0), 0); }
function cliente(marca) { return D.clientes.find(c => c.marca === marca); }
function saldoDe(marca) { return D.saldos.find(s => s.marca === marca) || {}; }
function latidoDe(marca) { return D.latidos.find(l => l.marca === marca); }
function infraDe(marca, mes) { return D.infraMes.find(i => i.marca === marca && i.mes === mes) || {}; }
function filasMes(mes, marca) { return D.libroMes.filter(r => r.mes === mes && (!marca || r.marca === marca)); }
function esHistorial(r) { return r.extra && r.extra.cargado === 'historial'; }
function mesesDisponibles() {
  const s = new Set(D.libroMes.map(r => r.mes)); s.add(mesDe(new Date()));
  return [...s].sort().reverse();
}
function selectorMes() {
  return `<label class="eti" style="display:flex;gap:8px;align-items:center">Mes
    <select id="mes">${mesesDisponibles().map(m => `<option value="${m}" ${m === mesSel ? 'selected' : ''}>${nombreMes(m)}</option>`).join('')}</select></label>`;
}
function estiloMarca(c) {
  const i = (c && c.identidad) || {};
  return `--m-acento:${i.acento || '#4D90FF'};--m-tinta:${i.tinta || 'var(--tinta)'};--m-fondo:${i.fondo || 'var(--papel)'};--m:${i.acento || '#4D90FF'}`;
}
function csv(nombre, filas) {
  if (!filas.length) return;
  const cols = Object.keys(filas[0]);
  const linea = r => cols.map(c => { const v = r[c] == null ? '' : String(typeof r[c] === 'object' ? JSON.stringify(r[c]) : r[c]); return /[",\n;]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(';');
  const blob = new Blob(['﻿' + cols.join(';') + '\n' + filas.map(linea).join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = nombre; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

// ── datos ──────────────────────────────────────────────────────────────
async function q(promesa, nombre) {
  const { data, error } = await promesa;
  if (error) { console.error(nombre, error); throw new Error(`${nombre}: ${error.message}`); }
  return data || [];
}
async function cargar() {
  const [clientes, saldos, libroMes, infraMes, latidos, cargas, cierres, infra, libro] = await Promise.all([
    q(sb.from('clientes').select('*').order('nombre'), 'clientes'),
    q(sb.from('saldos').select('*'), 'saldos'),
    q(sb.from('libro_mes').select('*'), 'libro_mes'),
    q(sb.from('infra_mes').select('*'), 'infra_mes'),
    q(sb.from('latidos').select('*'), 'latidos'),
    q(sb.from('cargas').select('*').order('creado_en', { ascending: false }), 'cargas'),
    q(sb.from('cierres').select('*').order('mes', { ascending: false }), 'cierres'),
    q(sb.from('infraestructura').select('*').order('mes', { ascending: false }), 'infraestructura'),
    q(sb.from('libro').select('*').order('creado_en', { ascending: false }).limit(1000), 'libro'),
  ]);
  Object.assign(D, { clientes, saldos, libroMes, infraMes, latidos, cargas, cierres, infra, libro });
}

// ── sesión ─────────────────────────────────────────────────────────────
function vistaLogin(msg = '') {
  app.innerHTML = `<div class="login">
    <h1>Tablero Asistime</h1>
    <p>Costos, márgenes y cobros por cliente. Entrás con tu email y tu contraseña.</p>
    ${msg ? `<p class="${msg.startsWith('✓') ? 'ok-linea' : 'aviso-linea'}">${esc(msg)}</p>` : ''}
    <form id="login" style="flex-direction:column"><input type="email" name="email" required placeholder="tu@email" autocomplete="email">
      <input type="password" name="clave" required placeholder="contraseña" autocomplete="current-password">
      <button class="boton">Entrar</button></form>
    <p class="nota" style="margin-top:14px"><button type="button" class="boton sec" id="enlace">Prefiero un enlace por email</button></p>
  </div>`;
  document.getElementById('login').onsubmit = async e => {
    e.preventDefault();
    const d = datos(e.target);
    const { error } = await sb.auth.signInWithPassword({ email: d.email.trim(), password: d.clave });
    if (error) vistaLogin('No pude entrar: ' + error.message);
  };
  document.getElementById('enlace').onclick = async () => {
    const email = document.querySelector('#login input[name=email]').value.trim();
    if (!email) return vistaLogin('Escribí el email primero.');
    const { error } = await sb.auth.signInWithOtp({ email, options: { emailRedirectTo: location.origin + location.pathname } });
    vistaLogin(error ? 'No pude mandar el enlace: ' + error.message : '✓ Enlace enviado. Revisá el correo y abrilo en este mismo navegador.');
  };
}

async function arrancar() {
  const { data: { session } } = await sb.auth.getSession();
  D.sesion = session;
  if (!session) return vistaLogin();
  app.innerHTML = '<div class="login"><h1>Tablero Asistime</h1><p>Leyendo el libro…</p></div>';
  try { await cargar(); }
  catch (e) {
    app.innerHTML = `<div class="login"><h1>Tablero Asistime</h1><p class="aviso-linea">${esc(e.message)}</p>
      <p>Si la base contestó vacío o con error de permisos, tu email no está en <code>administradores</code>.</p>
      <p><button class="boton sec" id="salir">Salir</button></p></div>`;
    document.getElementById('salir').onclick = () => sb.auth.signOut().then(() => location.reload());
    return;
  }
  render();
}
sb.auth.onAuthStateChange((ev) => { if (ev === 'SIGNED_IN' || ev === 'SIGNED_OUT') arrancar(); });
window.addEventListener('hashchange', render);

// ── marco ──────────────────────────────────────────────────────────────
function render() {
  if (!D.sesion) return;
  const ruta = location.hash.replace(/^#\/?/, '').split('/');
  const vista = ruta[0] || 'resumen';
  const lateral = `<nav class="lateral">
    <div class="marca">Tablero <span>Asistime</span></div>
    ${enlace('resumen', 'Resumen', vista)}${enlace('piezas', 'Piezas', vista)}${enlace('facturacion', 'Facturación', vista)}
    ${enlace('infra', 'Infraestructura', vista)}${enlace('salud', 'Salud del sistema', vista)}${enlace('config', 'Configuración', vista)}
    <div class="grupo eti" style="padding:0 10px">Clientes</div>
    ${D.clientes.filter(c => c.activo).map(c => `<a class="cli ${vista === 'cliente' && ruta[1] === c.marca ? 'activo' : ''}" href="#/cliente/${c.marca}" style="--m:${(c.identidad || {}).acento || '#4D90FF'}"><i></i>${esc(c.nombre)}</a>`).join('')}
    <div class="pie">${esc(D.sesion.user.email)}<br><button id="salir">Salir</button> · <button id="recargar">Actualizar</button></div>
  </nav>`;
  let cuerpo;
  try {
    cuerpo = { resumen: vResumen, cliente: () => vCliente(ruta[1]), piezas: vPiezas, facturacion: vFacturacion,
               infra: vInfra, salud: vSalud, config: vConfig }[vista]?.() ?? vResumen();
  } catch (e) { console.error(e); cuerpo = `<p class="aviso-linea">Algo se rompió dibujando esta pantalla: ${esc(e.message)}</p>`; }
  app.innerHTML = `<div class="marco">${lateral}<main>${cuerpo}</main></div>`;
  document.getElementById('salir').onclick = () => sb.auth.signOut().then(() => location.reload());
  document.getElementById('recargar').onclick = async () => { app.classList.add('cargando'); await cargar(); app.classList.remove('cargando'); render(); };
  const sel = document.getElementById('mes'); if (sel) sel.onchange = e => { mesSel = e.target.value; render(); };
  document.querySelectorAll('tr.click[data-href]').forEach(tr => tr.onclick = () => location.hash = tr.dataset.href);
  enganchar(vista, ruta);
}
function enlace(id, nombre, vista) { return `<a href="#/${id}" class="${vista === id ? 'activo' : ''}">${nombre}</a>`; }

// ── Resumen ────────────────────────────────────────────────────────────
function totales(mes, marca) {
  const f = filasMes(mes, marca);
  const t = { costo: suma(f, 'costo_usd'), cobrado: suma(f, 'precio_usd'), creditos: suma(f, 'creditos'),
              piezas: suma(f, 'piezas'), segundos: suma(f, 'segundos'), porTipo: {} };
  TIPOS.forEach(tp => t.porTipo[tp] = suma(f.filter(r => r.tipo === tp), 'piezas'));
  t.margen = t.cobrado - t.costo;
  const infra = marca ? +infraDe(marca, mes).infra_usd || 0 : suma(D.infra.filter(i => i.mes === mes), 'monto_usd');
  t.infra = infra; t.efectivo = t.cobrado - t.costo - infra;
  return t;
}
function kpi(eti, valor, det = '', clase = '') { return `<div class="kpi ${clase}"><div class="eti">${eti}</div><div class="v">${valor}</div>${det ? `<div class="d">${det}</div>` : ''}</div>`; }
function delta(actual, anterior, inv = false) {
  if (!anterior) return `mes anterior: —`;
  const d = (actual - anterior) / Math.abs(anterior);
  const cls = (d >= 0) !== inv ? 'up' : 'down';
  return `<span class="${cls}">${d >= 0 ? '+' : ''}${pct(d)}</span> vs. ${nombreMes(mesAnterior(mesSel)).split(' ')[0]}`;
}

function alertas() {
  const a = [];
  const ahora = Date.now();
  for (const c of D.clientes.filter(c => c.activo)) {
    const s = saldoDe(c.marca), l = latidoDe(c.marca), ref = `#/cliente/${c.marca}`;
    if (c.cobra && s.saldo_usd != null && +s.saldo_usd < PISO_USD)
      a.push(['grave', `<a href="${ref}">${esc(c.nombre)}</a> · saldo ${usd(s.saldo_usd)}, bajo el piso de ${usd(PISO_USD)}: el worker le va a frenar los pedidos`]);
    if (+s.cargas_sin_espejar > 0)
      a.push(['aviso', `<a href="${ref}">${esc(c.nombre)}</a> · ${s.cargas_sin_espejar} carga(s) anotadas que el worker todavía no copió a su cuenta`]);
    if (!l) a.push(['aviso', `<a href="${ref}">${esc(c.nombre)}</a> · el worker nunca dejó latido para esta marca (¿está desplegado con el libro?)`]);
    else {
      const min = (ahora - new Date(l.ultimo_ciclo)) / 60000;
      if (min > LATIDO_VIEJO_MIN) a.push(['grave', `<a href="#/salud">${esc(c.nombre)}</a> · último ciclo ${hace(l.ultimo_ciclo)}: el worker no está corriendo`]);
      if (l.errores > 0) a.push(['aviso', `<a href="${ref}">${esc(c.nombre)}</a> · ${l.errores} pedido(s) con error en las últimas 24 h`]);
      if (l.pendientes > 3) a.push(['aviso', `<a href="${ref}">${esc(c.nombre)}</a> · ${l.pendientes} pedidos esperando`]);
      const ig = (l.detalle || {}).ig;
      if (ig) {
        if (ig.activa === false) a.push(['grave', `<a href="${ref}">${esc(c.nombre)}</a> · la cuenta de Instagram está inactiva${ig.mensaje ? ': ' + esc(ig.mensaje) : ''}`]);
        else if (ig.expira_en) {
          const dias = (new Date(ig.expira_en) - ahora) / 86400000;
          if (dias < 0) a.push(['grave', `<a href="${ref}">${esc(c.nombre)}</a> · el token de Instagram venció ${hace(ig.expira_en)}`]);
          else if (dias < 10) a.push(['aviso', `<a href="${ref}">${esc(c.nombre)}</a> · el token de Instagram vence en ${Math.ceil(dias)} días`]);
        }
      }
    }
    const t = totales(mesSel, c.marca);
    if (t.creditos > 0 && c.precio_credito_usd == null)
      a.push(['aviso', `<a href="${ref}">${esc(c.nombre)}</a> · ${num(t.creditos)} créditos de Magnific este mes sin precio por crédito cargado: no entran al costo`]);
    const sinCobrar = D.libro.filter(r => r.marca === c.marca && mesDeFecha(r.creado_en) === mesSel && +r.costo_usd > 0 && +r.precio_usd === 0 && !esHistorial(r));
    if (c.cobra && sinCobrar.length)
      a.push(['aviso', `<a href="${ref}">${esc(c.nombre)}</a> · ${sinCobrar.length} pieza(s) del mes con costo y sin cobro (${usd(suma(sinCobrar, 'costo_usd'))})`]);
  }
  return a;
}

function vResumen() {
  const t = totales(mesSel), ant = totales(mesAnterior(mesSel));
  const ranking = D.clientes.filter(c => c.activo).map(c => ({ c, t: totales(mesSel, c.marca) })).sort((a, b) => b.t.costo - a.t.costo);
  const max = Math.max(...ranking.map(r => r.t.costo), 0.01);
  const al = alertas();
  return `<div class="cab"><div><h1>Resumen</h1><div class="sub">Lo que costó, lo que se cobró y lo que hay que mirar.</div></div>${selectorMes()}</div>
  <div class="kpis">
    ${kpi('Costo directo', usd(t.costo), delta(t.costo, ant.costo, true))}
    ${kpi('Cobrado', usd(t.cobrado), delta(t.cobrado, ant.cobrado))}
    ${kpi('Margen bruto', usd(t.margen), t.cobrado ? pct(t.margen / t.cobrado) + ' del cobrado' : 'nada cobrado')}
    ${kpi('Margen efectivo', usd(t.efectivo), `descontando ${usd(t.infra)} de infraestructura`, t.efectivo < 0 ? 'grave' : '')}
    ${kpi('Piezas', num(t.piezas), TIPOS.filter(x => t.porTipo[x]).map(x => `${t.porTipo[x]} ${NOMBRE_TIPO[x].toLowerCase()}`).join(' · ') || '—')}
    ${kpi('Créditos Magnific', num(t.creditos), 'de la cuenta de Asistime')}
    ${kpi('Tiempo de worker', num(t.segundos / 60) + '<small>min</small>', 'lo que reparte la infraestructura')}
  </div>
  <div class="dos">
    <div class="caja"><h3>Clientes en ${nombreMes(mesSel)}</h3>
      <div class="tabla"><table><thead><tr><th>Cliente</th><th class="num">Piezas</th><th class="num">Costo</th><th class="num">Cobrado</th><th class="num">Margen</th><th class="num">Efectivo</th><th class="num">Saldo</th></tr></thead>
      <tbody>${ranking.map(({ c, t }) => `<tr class="click" data-href="#/cliente/${c.marca}"><td><span class="punto" style="background:${(c.identidad || {}).acento || '#4D90FF'}"></span>${esc(c.nombre)}${c.cobra ? '' : ' <span class="chip">no cobra</span>'}</td>
        <td class="num">${num(t.piezas)}</td><td class="num">${usd(t.costo)}</td><td class="num">${usd(t.cobrado)}</td><td class="num">${c.cobra ? pct(t.cobrado ? t.margen / t.cobrado : NaN) : '—'}</td><td class="num">${usd(t.efectivo)}</td>
        <td class="num">${c.cobra ? usd(saldoDe(c.marca).saldo_usd) : '—'}</td></tr>`).join('') || '<tr><td colspan="7" class="vacio">Sin clientes activos</td></tr>'}</tbody>
      <tfoot><tr><td>Total</td><td class="num">${num(t.piezas)}</td><td class="num">${usd(t.costo)}</td><td class="num">${usd(t.cobrado)}</td><td class="num">${pct(t.cobrado ? t.margen / t.cobrado : NaN)}</td><td class="num">${usd(t.efectivo)}</td><td></td></tr></tfoot></table></div>
      <h3>Costo por cliente</h3>
      ${ranking.map(({ c, t }) => `<div class="barra" style="--m:${(c.identidad || {}).acento || '#4D90FF'}"><span class="n">${esc(c.nombre)}</span><span class="b" style="width:${Math.round(t.costo / max * 45)}%"></span><span class="m">${usd(t.costo)}</span></div>`).join('')}
    </div>
    <div class="caja"><h3>Alertas</h3>
      ${al.length ? al.map(([g, m]) => `<div class="alerta"><span class="punto ${g}" style="margin-top:6px"></span><span>${m}</span></div>`).join('') : '<div class="alerta"><span class="punto ok" style="margin-top:6px"></span><span>Nada que mirar.</span></div>'}
      <h3 style="margin-top:18px">Worker</h3>
      ${D.clientes.filter(c => c.activo).map(c => { const l = latidoDe(c.marca); return `<div class="barra"><span class="n">${esc(c.nombre)}</span><span class="m">${l ? hace(l.ultimo_ciclo) : 'sin latido'}</span></div>`; }).join('')}
    </div>
  </div>
  ${grafico(null)}`;
}

// ── gráfico de 6 meses ─────────────────────────────────────────────────
function grafico(marca, color) {
  const meses = []; let m = mesSel; for (let i = 0; i < 6; i++) { meses.unshift(m); m = mesAnterior(m); }
  const serie = meses.map(mm => ({ mes: mm, ...totales(mm, marca) }));
  const max = Math.max(...serie.map(s => Math.max(s.costo, s.cobrado)), 1);
  const W = 720, H = 190, pad = { l: 52, r: 12, t: 14, b: 26 }, gw = (W - pad.l - pad.r) / meses.length;
  const y = v => pad.t + (H - pad.t - pad.b) * (1 - v / max);
  const ticks = [0, 0.5, 1].map(f => f * max);
  return `<h2>Costo y cobrado, últimos seis meses</h2>
  <svg class="graf" viewBox="0 0 ${W} ${H}" style="${color ? `--m:${color}` : ''}" role="img" aria-label="Costo y cobrado por mes">
    ${ticks.map(v => `<line class="grilla" x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}"/><text x="${pad.l - 6}" y="${y(v) + 3}" text-anchor="end">${num(v, 0)}</text>`).join('')}
    ${serie.map((s, i) => { const x = pad.l + i * gw, bw = gw * 0.28; return `
      <rect class="costo" x="${x + gw * 0.18}" y="${y(s.costo)}" width="${bw}" height="${y(0) - y(s.costo)}" rx="2"><title>Costo ${usd(s.costo)}</title></rect>
      <rect class="cobrado" x="${x + gw * 0.52}" y="${y(s.cobrado)}" width="${bw}" height="${y(0) - y(s.cobrado)}" rx="2"><title>Cobrado ${usd(s.cobrado)}</title></rect>
      <text x="${x + gw / 2}" y="${H - 8}" text-anchor="middle">${nombreMes(s.mes).slice(0, 3)} ${s.mes.slice(2, 4)}</text>`; }).join('')}
  </svg><p class="leyenda">Gris: costo directo en dólares. Color: cobrado al cliente. Los créditos de Magnific no están acá salvo que tengan precio.</p>`;
}

// ── Cliente ────────────────────────────────────────────────────────────
function vCliente(marca) {
  const c = cliente(marca);
  if (!c) return `<p class="aviso-linea">No conozco la marca «${esc(marca)}».</p>`;
  const i = c.identidad || {}, s = saldoDe(marca), l = latidoDe(marca), t = totales(mesSel, marca), ant = totales(mesAnterior(mesSel), marca);
  const filas = filasMes(mesSel, marca);
  const precioProm = t.piezas && t.cobrado ? t.cobrado / suma(filas.filter(r => +r.precio_usd > 0), 'cobradas') : 0;
  const quedan = c.cobra && precioProm > 0 ? Math.floor(Math.max(0, +s.saldo_usd) / precioProm) : null;
  const piezas = D.libro.filter(r => r.marca === marca);
  const galeria = piezas.filter(r => r.url).slice(0, 12);
  const cargas = D.cargas.filter(k => k.marca === marca);
  const ig = (l && l.detalle && l.detalle.ig) || null;
  const costoCred = c.precio_credito_usd != null ? t.creditos * +c.precio_credito_usd : null;
  return `<div class="cab marca" style="${estiloMarca(c)}"><div style="display:flex;gap:16px;align-items:center">${i.logo ? `<img src="${esc(i.logo)}" alt="">` : ''}<div><h1>${esc(c.nombre)}</h1><div class="sub">${esc(marca)} · margen ×${num(c.margen, 2)} · ${c.cobra ? 'cobra en ' + c.moneda_factura : 'no cobra'}${c.activo ? '' : ' · inactivo'}</div></div></div>${selectorMes()}</div>
  <div class="kpis">
    ${c.cobra ? kpi('Saldo', usd(s.saldo_usd), quedan != null ? `alcanza para ~${quedan} piezas al precio del mes` : '', +s.saldo_usd < PISO_USD ? 'grave' : '') : kpi('Costo acumulado', usd(s.costo_usd), 'la casa no se cobra')}
    ${kpi('Cobrado en el mes', usd(t.cobrado), delta(t.cobrado, ant.cobrado))}
    ${kpi('Costo directo', usd(t.costo), delta(t.costo, ant.costo, true))}
    ${kpi('Margen efectivo', usd(t.efectivo), `bruto ${usd(t.margen)} menos ${usd(t.infra)} de infra`, t.efectivo < 0 && c.cobra ? 'grave' : '')}
    ${kpi('Piezas', num(t.piezas), TIPOS.filter(x => t.porTipo[x]).map(x => `${t.porTipo[x]} ${NOMBRE_TIPO[x].toLowerCase()}`).join(' · ') || '—')}
    ${kpi('Créditos Magnific', num(t.creditos), costoCred != null ? `≈ ${usd(costoCred)} al precio cargado` : t.creditos ? 'sin precio por crédito' : '', t.creditos && costoCred == null ? 'aviso' : '')}
  </div>
  <div class="dos">
    <div>
      <div class="caja"><h3>${nombreMes(mesSel)} por tipo</h3>
        <div class="tabla"><table><thead><tr><th>Tipo</th><th class="num">Piezas</th><th class="num">Cobradas</th><th class="num">Costo</th><th class="num">Créditos</th><th class="num">Cobrado</th><th class="num">Margen</th></tr></thead>
        <tbody>${TIPOS.map(tp => { const f = filas.filter(r => r.tipo === tp); if (!f.length) return ''; const co = suma(f, 'costo_usd'), pr = suma(f, 'precio_usd'); return `<tr><td>${NOMBRE_TIPO[tp]}</td><td class="num">${num(suma(f, 'piezas'))}</td><td class="num">${num(suma(f, 'cobradas'))}</td><td class="num">${usd(co, 4)}</td><td class="num">${num(suma(f, 'creditos'))}</td><td class="num">${usd(pr)}</td><td class="num">${usd(pr - co)}</td></tr>`; }).join('') || '<tr><td colspan="7" class="vacio">Nada este mes</td></tr>'}</tbody></table></div>
        <button class="boton sec" id="csv-mes">Exportar el mes (CSV)</button>
      </div>
      ${grafico(marca, i.acento)}
      <h2>Últimas piezas</h2>
      ${galeria.length ? `<div class="galeria">${galeria.map(r => `<a href="${esc(r.url)}" target="_blank" rel="noopener" title="${esc(r.titulo || '')}">${/\.(png|jpe?g|webp|avif|gif)(\?|$)/i.test(r.url) ? `<img src="${esc(r.url)}" alt="" loading="lazy">` : `<div class="v">▶ ${NOMBRE_TIPO[r.tipo]}</div>`}<div class="t">${esc(r.titulo || r.tipo)} · ${usd(r.precio_usd)}</div></a>`).join('')}</div>` : '<p class="vacio">Todavía no hay piezas con enlace en el libro.</p>'}
      <h2>Piezas de ${nombreMes(mesSel)}</h2>
      ${tablaPiezas(piezas.filter(r => mesDeFecha(r.creado_en) === mesSel), false)}
    </div>
    <div>
      ${c.cobra ? `<div class="caja"><h3>Cuenta</h3>
        <div class="barra"><span class="n">Cargas totales</span><span class="m">${usd(s.cargas_usd)}</span></div>
        <div class="barra"><span class="n">Consumido</span><span class="m">${usd(s.consumo_usd)}</span></div>
        <div class="barra"><span class="n">Saldo</span><span class="m"><b>${usd(s.saldo_usd)}</b></span></div>
        <div class="barra"><span class="n">Última carga</span><span class="m">${fecha(s.ultima_carga)}</span></div>
        <h3 style="margin-top:14px">Cargar saldo</h3>
        <form id="carga" class="fila-form">
          <label>Tipo<select name="tipo"><option value="carga">carga (pagó)</option><option value="abono">abono (incluido)</option><option value="ajuste">ajuste</option></select></label>
          <label>US$<input name="monto" type="number" step="0.01" required style="width:100px"></label>
          <label>Detalle<input name="detalle" placeholder="transferencia 7/9"></label>
          <button class="boton">Anotar</button></form>
        <p class="nota">Queda en el libro ya; el worker la copia a la cuenta del cliente en su próximo ciclo (un minuto).${+s.cargas_sin_espejar ? ` <b>${s.cargas_sin_espejar} esperando.</b>` : ''}</p>
        <details><summary>Movimientos de saldo (${cargas.length})</summary><div class="tabla" style="margin-top:8px"><table><tbody>${cargas.slice(0, 30).map(k => `<tr><td class="min">${fecha(k.creado_en)}</td><td>${k.tipo}${k.detalle ? ' · ' + esc(k.detalle) : ''}</td><td class="num">${usd(k.monto_usd)}</td><td>${k.error ? `<span class="chip grave" title="${esc(k.error)}">error</span>` : k.espejado_en ? '<span class="chip ok">en cuenta</span>' : '<span class="chip aviso">esperando</span>'}</td></tr>`).join('') || '<tr><td class="vacio">Sin movimientos</td></tr>'}</tbody></table></div></details>
      </div>` : ''}
      <div class="caja" style="margin-top:12px"><h3>Worker e Instagram</h3>
        <div class="barra"><span class="n">Último ciclo</span><span class="m">${l ? hace(l.ultimo_ciclo) : 'sin latido'}</span></div>
        <div class="barra"><span class="n">Pedidos esperando</span><span class="m">${l ? l.pendientes : '—'}</span></div>
        <div class="barra"><span class="n">Errores (24 h)</span><span class="m">${l ? l.errores : '—'}</span></div>
        <div class="barra"><span class="n">Instagram</span><span class="m">${ig ? (ig.activa === false ? '<span class="chip grave">inactiva</span>' : '@' + esc(ig.usuario || '')) : '<span class="chip">sin cuenta</span>'}</span></div>
        ${ig && ig.expira_en ? `<div class="barra"><span class="n">Token vence</span><span class="m">${fecha(ig.expira_en)} (${Math.ceil((new Date(ig.expira_en) - Date.now()) / 86400000)} días)</span></div>` : ''}
      </div>
      <div class="caja" style="margin-top:12px"><h3>Configuración</h3>
        <form id="config" class="fila-form" style="flex-direction:column;align-items:stretch">
          <label>Nombre<input name="nombre" value="${esc(c.nombre)}" required></label>
          <div class="fila-form"><label>Margen ×<input name="margen" type="number" min="1" step="0.05" value="${c.margen}" style="width:90px"></label>
          <label>Cobra<select name="cobra"><option value="true" ${c.cobra ? 'selected' : ''}>sí</option><option value="false" ${!c.cobra ? 'selected' : ''}>no</option></select></label>
          <label>Moneda<select name="moneda_factura"><option ${c.moneda_factura === 'USD' ? 'selected' : ''}>USD</option><option ${c.moneda_factura === 'UYU' ? 'selected' : ''}>UYU</option></select></label></div>
          <div class="fila-form"><label>Tope US$/mes<input name="tope_usd_mes" type="number" step="1" value="${c.tope_usd_mes ?? ''}" style="width:110px"></label>
          <label>US$ por crédito<input name="precio_credito_usd" type="number" step="0.0001" value="${c.precio_credito_usd ?? ''}" style="width:110px"></label>
          <label>Créditos de<select name="cuenta_creditos"><option ${c.cuenta_creditos === 'asistime' ? 'selected' : ''}>asistime</option><option ${c.cuenta_creditos === 'cliente' ? 'selected' : ''}>cliente</option></select></label></div>
          <div class="fila-form"><label>Acento<input name="acento" type="color" value="${i.acento || '#4D90FF'}"></label><label>Tinta<input name="tinta" type="color" value="${i.tinta || '#0A0B14'}"></label><label>Fondo<input name="fondo" type="color" value="${i.fondo || '#F3F5FB'}"></label>
          <label>Activo<select name="activo"><option value="true" ${c.activo ? 'selected' : ''}>sí</option><option value="false" ${!c.activo ? 'selected' : ''}>no</option></select></label></div>
          <label>Logo (URL)<input name="logo" value="${esc(i.logo || '')}" placeholder="https://…/logo.png"></label>
          <label>Notas<textarea name="notas" rows="2">${esc(c.notas || '')}</textarea></label>
          <div><button class="boton">Guardar</button> <span id="config-ok" class="nota"></span></div>
        </form>
        <p class="nota">El margen se aplica desde el próximo ciclo del worker. Las piezas ya cobradas guardan el margen con el que salieron.</p>
      </div>
    </div>
  </div>`;
}

function tablaPiezas(filas, conCliente = true) {
  if (!filas.length) return '<p class="vacio">Nada acá.</p>';
  return `<div class="tabla"><table><thead><tr><th>Fecha</th>${conCliente ? '<th>Cliente</th>' : ''}<th>Tipo</th><th>Pieza</th><th>Plantilla</th><th>Modelo</th><th class="num">Seg</th><th class="num">Tokens</th><th class="num">Costo</th><th class="num">Créd.</th><th class="num">Precio</th><th>Avisos</th></tr></thead>
  <tbody>${filas.map(r => { const cl = cliente(r.marca) || {}; const tok = (+r.tokens_entrada || 0) + (+r.tokens_salida || 0); const av = Array.isArray(r.avisos) ? r.avisos.filter(Boolean) : []; return `<tr>
    <td class="min">${fechaHora(r.creado_en)}</td>${conCliente ? `<td><a href="#/cliente/${r.marca}">${esc(cl.nombre || r.marca)}</a></td>` : ''}
    <td><span class="chip tipo">${r.tipo}</span>${esHistorial(r) ? ' <span class="chip" title="cargada del historial, antes del libro">hist.</span>' : ''}</td>
    <td class="corta">${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.titulo || r.detalle || r.pieza_id.slice(0, 8))}</a>` : esc(r.titulo || r.detalle || r.pieza_id.slice(0, 8))}</td>
    <td>${esc(r.plantilla || '')}</td><td class="corta" style="max-width:140px">${esc(r.modelo || '')}</td>
    <td class="num">${r.segundos != null ? num(r.segundos) : ''}</td><td class="num">${tok ? num(tok) : ''}</td>
    <td class="num">${+r.costo_usd ? usd(r.costo_usd, 4) : ''}</td><td class="num">${+r.creditos ? num(r.creditos) : ''}</td>
    <td class="num">${+r.precio_usd ? usd(r.precio_usd) : (+r.costo_usd && (cl.cobra ?? true) && !esHistorial(r) ? '<span class="chip aviso">sin cobrar</span>' : '')}</td>
    <td>${av.length ? `<span class="chip aviso" title="${esc(av.join(' · '))}">${av.length}</span>` : ''}</td></tr>`; }).join('')}</tbody></table></div>`;
}

// ── Piezas ─────────────────────────────────────────────────────────────
const filtro = { marca: '', tipo: '', texto: '' };
function vPiezas() {
  const txt = filtro.texto.toLowerCase();
  const filas = D.libro.filter(r => (!filtro.marca || r.marca === filtro.marca) && (!filtro.tipo || r.tipo === filtro.tipo)
    && mesDeFecha(r.creado_en) === mesSel && (!txt || [r.titulo, r.detalle, r.plantilla, r.modelo].join(' ').toLowerCase().includes(txt)));
  return `<div class="cab"><div><h1>Piezas</h1><div class="sub">Todo lo que se hizo, cliente por cliente, con lo que costó y lo que se cobró.</div></div>${selectorMes()}</div>
  <div class="fila-form" style="margin-bottom:14px">
    <label>Cliente<select id="f-marca"><option value="">todos</option>${D.clientes.map(c => `<option value="${c.marca}" ${filtro.marca === c.marca ? 'selected' : ''}>${esc(c.nombre)}</option>`).join('')}</select></label>
    <label>Tipo<select id="f-tipo"><option value="">todos</option>${TIPOS.map(t => `<option value="${t}" ${filtro.tipo === t ? 'selected' : ''}>${NOMBRE_TIPO[t]}</option>`).join('')}</select></label>
    <label>Buscar<input id="f-texto" value="${esc(filtro.texto)}" placeholder="título, plantilla, modelo"></label>
    <button class="boton sec" id="csv-piezas">CSV</button>
    <span class="nota" style="margin:0">${filas.length} piezas · costo ${usd(suma(filas, 'costo_usd'))} · cobrado ${usd(suma(filas, 'precio_usd'))}</span>
  </div>
  ${tablaPiezas(filas)}
  ${D.libro.length >= 1000 ? '<p class="nota">Se muestran las últimas 1000 filas del libro.</p>' : ''}`;
}

// ── Facturación ────────────────────────────────────────────────────────
function vFacturacion() {
  const filas = D.clientes.filter(c => c.activo).map(c => {
    const t = totales(mesSel, c.marca), s = saldoDe(c.marca);
    const cargasMes = suma(D.cargas.filter(k => k.marca === c.marca && mesDeFecha(k.creado_en) === mesSel && !k.error), 'monto_usd');
    const cierre = D.cierres.find(x => x.marca === c.marca && x.mes === mesSel);
    return { c, t, s, cargasMes, cierre };
  });
  return `<div class="cab"><div><h1>Facturación</h1><div class="sub">El cierre de cada mes: qué se le cobró a cada cliente, qué pagó y cómo quedó.</div></div>${selectorMes()}</div>
  <div class="tabla"><table><thead><tr><th>Cliente</th><th class="num">Costo</th><th class="num">Infra</th><th class="num">Cobrado</th><th class="num">Margen efectivo</th><th class="num">Cargó en el mes</th><th class="num">Saldo hoy</th><th>Factura en</th><th>Cierre</th></tr></thead>
  <tbody>${filas.map(({ c, t, s, cargasMes, cierre }) => `<tr><td><a href="#/cliente/${c.marca}">${esc(c.nombre)}</a>${c.cobra ? '' : ' <span class="chip">no cobra</span>'}</td>
    <td class="num">${usd(t.costo)}</td><td class="num">${usd(t.infra)}</td><td class="num">${usd(t.cobrado)}</td><td class="num">${usd(t.efectivo)}</td>
    <td class="num">${usd(cargasMes)}</td><td class="num">${c.cobra ? usd(s.saldo_usd) : '—'}</td><td>${c.moneda_factura}</td>
    <td>${cierre ? `<span class="chip ok">cerrado ${fecha(cierre.cerrado_en)}</span>${cierre.facturado != null ? ` ${num(cierre.facturado, 2)} ${cierre.moneda}` : ''}` : '<span class="chip">abierto</span>'}</td></tr>`).join('')}</tbody>
  <tfoot><tr><td>Total</td><td class="num">${usd(suma(filas.map(f => f.t), 'costo'))}</td><td class="num">${usd(suma(filas.map(f => f.t), 'infra'))}</td><td class="num">${usd(suma(filas.map(f => f.t), 'cobrado'))}</td><td class="num">${usd(suma(filas.map(f => f.t), 'efectivo'))}</td><td class="num">${usd(suma(filas, 'cargasMes'))}</td><td colspan="3"></td></tr></tfoot></table></div>
  <div class="caja"><h3>Cerrar ${nombreMes(mesSel)}</h3>
    <form id="cierre" class="fila-form"><label>Tipo de cambio UYU por US$ (sólo para los que facturan en pesos)<input name="tc" type="number" step="0.01" placeholder="40.50" style="width:120px"></label>
    <label>Notas<input name="notas" placeholder="opcional"></label><button class="boton">Cerrar el mes para todos</button> <button type="button" class="boton sec" id="csv-cierre">CSV del mes</button></form>
    <p class="nota">Guarda una foto de estos números por cliente en <code>cierres</code>. Se puede volver a cerrar: pisa la foto anterior. No mueve saldo ni cobra nada.</p>
  </div>
  <h2>Cierres anteriores</h2>
  ${D.cierres.length ? `<div class="tabla"><table><thead><tr><th>Mes</th><th>Cliente</th><th class="num">Costo</th><th class="num">Infra</th><th class="num">Cobrado</th><th class="num">Cargas</th><th class="num">Saldo</th><th class="num">Facturado</th><th>Notas</th></tr></thead>
  <tbody>${D.cierres.map(x => `<tr><td class="min">${nombreMes(x.mes)}</td><td>${esc((cliente(x.marca) || {}).nombre || x.marca)}</td><td class="num">${usd(x.costo_usd)}</td><td class="num">${usd(x.infra_usd)}</td><td class="num">${usd(x.consumo_usd)}</td><td class="num">${usd(x.cargas_usd)}</td><td class="num">${usd(x.saldo_usd)}</td><td class="num">${x.facturado != null ? num(x.facturado, 2) + ' ' + x.moneda : '—'}</td><td>${esc(x.notas || '')}</td></tr>`).join('')}</tbody></table></div>` : '<p class="vacio">Ningún mes cerrado todavía.</p>'}`;
}

// ── Infraestructura ────────────────────────────────────────────────────
function vInfra() {
  const delMes = D.infra.filter(i => i.mes === mesSel);
  const reparto = D.infraMes.filter(i => i.mes === mesSel).sort((a, b) => b.segundos - a.segundos);
  return `<div class="cab"><div><h1>Infraestructura</h1><div class="sub">Lo que no es por pieza: Cloud Run, Supabase, las facturas de los proveedores. Se reparte entre clientes por segundos de worker.</div></div>${selectorMes()}</div>
  <div class="dos"><div class="caja"><h3>Costos de ${nombreMes(mesSel)}</h3>
    <form id="infra" class="fila-form" style="margin-bottom:12px"><label>Concepto<input name="concepto" required placeholder="Cloud Run"></label><label>Proveedor<input name="proveedor" placeholder="Google"></label><label>US$<input name="monto" type="number" step="0.01" required style="width:100px"></label><label>Notas<input name="notas"></label><button class="boton">Sumar</button></form>
    <div class="tabla"><table><thead><tr><th>Concepto</th><th>Proveedor</th><th class="num">US$</th><th></th></tr></thead><tbody>${delMes.map(i => `<tr><td>${esc(i.concepto)}${i.notas ? `<div class="nota" style="margin:0">${esc(i.notas)}</div>` : ''}</td><td>${esc(i.proveedor || '')}</td><td class="num">${usd(i.monto_usd)}</td><td><button class="boton sec" data-borrar-infra="${i.id}" style="padding:2px 8px">borrar</button></td></tr>`).join('') || '<tr><td colspan="4" class="vacio">Nada cargado este mes</td></tr>'}</tbody>
    <tfoot><tr><td colspan="2">Total</td><td class="num">${usd(suma(delMes, 'monto_usd'))}</td><td></td></tr></tfoot></table></div>
    <p class="nota">La factura de Anthropic va acá sólo si querés cruzarla contra la suma del libro: no la sumes al reparto, ya está pieza por pieza. Cloud Run, Supabase, almacenamiento y Magnific/fal por suscripción, sí.</p>
  </div>
  <div class="caja"><h3>Reparto por segundos de worker</h3>
    <div class="tabla"><table><thead><tr><th>Cliente</th><th class="num">Minutos</th><th class="num">Parte</th><th class="num">Infra US$</th></tr></thead><tbody>${reparto.map(r => `<tr><td>${esc((cliente(r.marca) || {}).nombre || r.marca)}</td><td class="num">${num(r.segundos / 60, 1)}</td><td class="num">${pct(r.segundos_total ? r.segundos / r.segundos_total : NaN)}</td><td class="num">${usd(r.infra_usd)}</td></tr>`).join('') || '<tr><td colspan="4" class="vacio">Sin piezas con segundos este mes</td></tr>'}</tbody></table></div>
  </div></div>
  <h2>Meses anteriores</h2>
  ${D.infra.filter(i => i.mes !== mesSel).length ? `<div class="tabla"><table><tbody>${D.infra.filter(i => i.mes !== mesSel).map(i => `<tr><td class="min">${nombreMes(i.mes)}</td><td>${esc(i.concepto)}</td><td>${esc(i.proveedor || '')}</td><td class="num">${usd(i.monto_usd)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="vacio">—</p>'}`;
}

// ── Salud ──────────────────────────────────────────────────────────────
function vSalud() {
  return `<div class="cab"><div><h1>Salud del sistema</h1><div class="sub">Lo que el worker deja en cada ciclo. Un ciclo dura un minuto; si el último es de hace más de ${LATIDO_VIEJO_MIN}, algo está caído.</div></div></div>
  <div class="tabla"><table><thead><tr><th>Cliente</th><th>Último ciclo</th><th class="num">Esperando</th><th class="num">Errores 24 h</th><th>Versión</th><th>En el último ciclo</th><th>Instagram</th><th>Cargas sin copiar</th></tr></thead>
  <tbody>${D.clientes.map(c => { const l = latidoDe(c.marca), s = saldoDe(c.marca); const d = (l && l.detalle) || {}; const ig = d.ig; const viejo = l && (Date.now() - new Date(l.ultimo_ciclo)) / 60000 > LATIDO_VIEJO_MIN;
    return `<tr><td><a href="#/cliente/${c.marca}">${esc(c.nombre)}</a>${c.activo ? '' : ' <span class="chip">inactivo</span>'}</td>
    <td><span class="punto ${!l ? 'aviso' : viejo ? 'grave' : 'ok'}"></span>${l ? `${hace(l.ultimo_ciclo)} <span class="nota">${fechaHora(l.ultimo_ciclo)}</span>` : 'sin latido'}</td>
    <td class="num">${l ? l.pendientes : '—'}</td><td class="num ${l && l.errores ? 'grave' : ''}">${l ? l.errores : '—'}</td><td>${esc(l ? l.version || '' : '')}</td>
    <td>${['disenos', 'reels', 'fotos', 'publicaciones'].filter(k => d[k]).map(k => `${d[k]} ${k}`).join(' · ') || '—'}</td>
    <td>${ig ? `${ig.activa === false ? '<span class="chip grave">inactiva</span>' : '<span class="chip ok">activa</span>'} @${esc(ig.usuario || '')}${ig.expira_en ? ` · vence ${fecha(ig.expira_en)}` : ''}` : '<span class="chip">sin cuenta</span>'}</td>
    <td class="num">${s.cargas_sin_espejar || 0}</td></tr>`; }).join('')}</tbody></table></div>
  <div class="caja"><h3>Qué mira esta pantalla y qué no</h3>
    <p>El latido lo escribe <code>app/libro.py</code> al final de cada cliente en cada ciclo: pendientes y errores salen de <code>disenos</code>, el estado de Instagram de <code>cuentas_ig</code>. Las cargas sin copiar son recargas anotadas acá que el worker todavía no llevó a la cuenta del cliente.</p>
    <p>No mira los reels ni las fotos atascados: eso sigue en el log de Cloud Run.</p>
  </div>`;
}

// ── Configuración ──────────────────────────────────────────────────────
function vConfig() {
  return `<div class="cab"><div><h1>Configuración</h1><div class="sub">Las marcas y su trato comercial. El worker lee esta tabla al arrancar cada ciclo.</div></div></div>
  <div class="tabla"><table><thead><tr><th>Marca</th><th>Nombre</th><th>Supabase</th><th class="num">Margen</th><th>Cobra</th><th>Moneda</th><th class="num">Tope/mes</th><th class="num">US$/crédito</th><th>Créditos de</th><th>Activo</th></tr></thead>
  <tbody>${D.clientes.map(c => `<tr class="click" data-href="#/cliente/${c.marca}"><td><span class="punto" style="background:${(c.identidad || {}).acento || '#4D90FF'}"></span>${esc(c.marca)}</td><td>${esc(c.nombre)}</td><td class="num">${esc(c.supabase_ref || '')}</td><td class="num">×${num(c.margen, 2)}</td><td>${c.cobra ? 'sí' : 'no'}</td><td>${c.moneda_factura}</td><td class="num">${c.tope_usd_mes != null ? usd(c.tope_usd_mes) : '—'}</td><td class="num">${c.precio_credito_usd != null ? num(c.precio_credito_usd, 4) : '—'}</td><td>${c.cuenta_creditos}</td><td>${c.activo ? 'sí' : 'no'}</td></tr>`).join('')}</tbody></table></div>
  <p class="nota">Tocá una fila para editarla en la pantalla del cliente.</p>
  <div class="dos"><div class="caja"><h3>Dar de alta una marca</h3>
    <form id="alta" class="fila-form"><label>Marca (igual que en el registro)<input name="marca" required placeholder="club-x-disenos" pattern="[a-z0-9-]+"></label><label>Nombre<input name="nombre" required placeholder="Club X"></label><label>Supabase ref<input name="supabase_ref" placeholder="abcdefghijklmnopqrst"></label><button class="boton">Crear</button></form>
    <p class="nota">Hasta que la marca no esté acá, el worker no puede anotarle nada en el libro (y lo dice en el log). Las claves no van acá: van en el registro de Secret Manager, como siempre.</p>
  </div>
  <div class="caja"><h3>Tu contraseña</h3>
    <form id="clave" class="fila-form"><label>Nueva contraseña<input name="clave" type="password" minlength="10" required autocomplete="new-password"></label><label>Otra vez<input name="clave2" type="password" minlength="10" required autocomplete="new-password"></label><button class="boton">Cambiar</button></form>
    <p class="nota">Diez caracteres como mínimo. Cambiá la inicial apenas entres.</p>
    <h3 style="margin-top:14px">Quién puede entrar</h3><div id="admins">Cargando…</div>
    <form id="admin-nuevo" class="fila-form" style="margin-top:10px"><label>Email<input name="email" type="email" required></label><button class="boton sec">Sumar</button></form>
    <p class="nota">Cualquiera con el enlace puede pedir entrar; sólo los emails de esta lista ven algo.</p>
  </div></div>`;
}

// ── acciones ───────────────────────────────────────────────────────────
function datos(form) { const o = {}; new FormData(form).forEach((v, k) => o[k] = v); return o; }
async function accion(fn, boton) {
  if (boton) boton.disabled = true;
  try { await fn(); await cargar(); render(); }
  catch (e) { alert('No se pudo: ' + e.message); if (boton) boton.disabled = false; }
}
function enganchar(vista, ruta) {
  const marca = ruta[1];
  const f = id => document.getElementById(id);
  if (f('carga')) f('carga').onsubmit = e => { e.preventDefault(); const d = datos(e.target); accion(() => q(sb.from('cargas').insert({ marca, tipo: d.tipo, monto_usd: +d.monto, detalle: d.detalle || null, quien: D.sesion.user.email }), 'cargas'), e.submitter); };
  if (f('config')) f('config').onsubmit = e => { e.preventDefault(); const d = datos(e.target); const c = cliente(marca);
    const fila = { nombre: d.nombre, margen: +d.margen, cobra: d.cobra === 'true', moneda_factura: d.moneda_factura, activo: d.activo === 'true',
      tope_usd_mes: d.tope_usd_mes === '' ? null : +d.tope_usd_mes, precio_credito_usd: d.precio_credito_usd === '' ? null : +d.precio_credito_usd,
      cuenta_creditos: d.cuenta_creditos, notas: d.notas || null,
      identidad: { ...(c.identidad || {}), acento: d.acento, tinta: d.tinta, fondo: d.fondo, logo: d.logo || undefined } };
    accion(() => q(sb.from('clientes').update(fila).eq('marca', marca), 'clientes'), e.submitter); };
  if (f('csv-mes')) f('csv-mes').onclick = () => csv(`${marca}-${mesSel.slice(0, 7)}.csv`, D.libro.filter(r => r.marca === marca && mesDeFecha(r.creado_en) === mesSel).map(filaCsv));
  if (f('csv-piezas')) f('csv-piezas').onclick = () => csv(`piezas-${mesSel.slice(0, 7)}.csv`, D.libro.filter(r => mesDeFecha(r.creado_en) === mesSel && (!filtro.marca || r.marca === filtro.marca) && (!filtro.tipo || r.tipo === filtro.tipo)).map(filaCsv));
  if (f('f-marca')) { f('f-marca').onchange = e => { filtro.marca = e.target.value; render(); }; f('f-tipo').onchange = e => { filtro.tipo = e.target.value; render(); };
    f('f-texto').oninput = e => { filtro.texto = e.target.value; clearTimeout(filtro.t); filtro.t = setTimeout(render, 250); }; }
  if (f('infra')) f('infra').onsubmit = e => { e.preventDefault(); const d = datos(e.target); accion(() => q(sb.from('infraestructura').insert({ mes: mesSel, concepto: d.concepto, proveedor: d.proveedor || null, monto_usd: +d.monto, notas: d.notas || null }), 'infraestructura'), e.submitter); };
  document.querySelectorAll('[data-borrar-infra]').forEach(b => b.onclick = () => { if (confirm('¿Borrar este costo?')) accion(() => q(sb.from('infraestructura').delete().eq('id', b.dataset.borrarInfra), 'infraestructura'), b); });
  if (f('cierre')) { f('cierre').onsubmit = e => { e.preventDefault(); const d = datos(e.target); const tc = d.tc ? +d.tc : null;
      const filas = D.clientes.filter(c => c.activo).map(c => { const t = totales(mesSel, c.marca), s = saldoDe(c.marca);
        const cargasMes = suma(D.cargas.filter(k => k.marca === c.marca && mesDeFecha(k.creado_en) === mesSel && !k.error), 'monto_usd');
        const enPesos = c.moneda_factura === 'UYU' && tc;
        return { marca: c.marca, mes: mesSel, costo_usd: +t.costo.toFixed(2), consumo_usd: +t.cobrado.toFixed(2), cargas_usd: +cargasMes.toFixed(2), infra_usd: +t.infra.toFixed(2),
          saldo_usd: +(+s.saldo_usd || 0).toFixed(2), facturado: c.cobra ? +(enPesos ? t.cobrado * tc : t.cobrado).toFixed(2) : null, moneda: enPesos ? 'UYU' : 'USD', tipo_cambio: enPesos ? tc : null, notas: d.notas || null, cerrado_en: new Date().toISOString() }; });
      accion(() => q(sb.from('cierres').upsert(filas, { onConflict: 'marca,mes' }), 'cierres'), e.submitter); };
    f('csv-cierre').onclick = () => csv(`cierre-${mesSel.slice(0, 7)}.csv`, D.clientes.filter(c => c.activo).map(c => { const t = totales(mesSel, c.marca); return { cliente: c.nombre, mes: mesSel, costo_usd: t.costo.toFixed(2), infra_usd: t.infra.toFixed(2), cobrado_usd: t.cobrado.toFixed(2), margen_efectivo_usd: t.efectivo.toFixed(2), saldo_usd: saldoDe(c.marca).saldo_usd, piezas: t.piezas, creditos: t.creditos }; })); }
  if (f('clave')) f('clave').onsubmit = e => { e.preventDefault(); const d = datos(e.target); if (d.clave !== d.clave2) return alert('Las dos contraseñas no coinciden.');
    accion(async () => { await q(sb.auth.updateUser({ password: d.clave }), 'contraseña'); alert('Contraseña cambiada.'); }, e.submitter); };
  if (f('alta')) f('alta').onsubmit = e => { e.preventDefault(); const d = datos(e.target); accion(() => q(sb.from('clientes').insert({ marca: d.marca, nombre: d.nombre, supabase_ref: d.supabase_ref || null }), 'clientes'), e.submitter); };
  if (f('admins')) { q(sb.from('administradores').select('email').order('email'), 'administradores').then(a => { f('admins').innerHTML = a.map(x => `<div class="barra"><span class="n">${esc(x.email)}</span>${a.length > 1 ? `<button class="boton sec" data-quitar-admin="${esc(x.email)}" style="padding:2px 8px">quitar</button>` : ''}</div>`).join('');
      f('admins').querySelectorAll('[data-quitar-admin]').forEach(b => b.onclick = () => { if (confirm(`¿Quitar a ${b.dataset.quitarAdmin}?`)) accion(() => q(sb.from('administradores').delete().eq('email', b.dataset.quitarAdmin), 'administradores'), b); }); }).catch(e => f('admins').textContent = e.message);
    f('admin-nuevo').onsubmit = e => { e.preventDefault(); const d = datos(e.target); accion(() => q(sb.from('administradores').insert({ email: d.email.trim().toLowerCase() }), 'administradores'), e.submitter); }; }
}
function filaCsv(r) { return { fecha: r.creado_en, cliente: (cliente(r.marca) || {}).nombre || r.marca, tipo: r.tipo, titulo: r.titulo, plantilla: r.plantilla, modelo: r.modelo, proveedor: r.proveedor, segundos: r.segundos, tokens_entrada: r.tokens_entrada, tokens_salida: r.tokens_salida, costo_usd: r.costo_usd, creditos: r.creditos, precio_usd: r.precio_usd, margen: r.margen_aplicado, url: r.url, avisos: Array.isArray(r.avisos) ? r.avisos.join(' · ') : '' }; }

arrancar();
