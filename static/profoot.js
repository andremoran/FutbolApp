/* ============================================================================
   profoot.js — Comportamiento del shell de ProFoot Assistant.
   Sin dependencias: hoja inferior, iconos Feather, fetch con CSRF y helpers.
   ========================================================================= */
(function () {
  'use strict';

  var PF = window.PF = window.PF || {};

  /* ─── Hoja inferior (⋯ Ver más) ─────────────────────────────────────── */
  PF.openSheet = function (id) {
    var sheet = document.getElementById(id || 'pf-sheet-mas');
    var back = document.getElementById((id || 'pf-sheet-mas') + '-back');
    if (!sheet) return;
    sheet.classList.add('is-open');
    if (back) back.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  };

  PF.closeSheet = function (id) {
    var sheet = document.getElementById(id || 'pf-sheet-mas');
    var back = document.getElementById((id || 'pf-sheet-mas') + '-back');
    if (!sheet) return;
    sheet.classList.remove('is-open');
    if (back) back.classList.remove('is-open');
    document.body.style.overflow = '';
  };

  /* Cerrar con Escape o tocando el fondo */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.pf-sheet.is-open').forEach(function (s) { PF.closeSheet(s.id); });
    }
  });
  document.addEventListener('click', function (e) {
    var back = e.target.closest('.pf-sheet-back');
    if (back && back.id) PF.closeSheet(back.id.replace('-back', ''));
  });

  /* Arrastrar hacia abajo para cerrar — el gesto que espera quien viene de la app */
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.pf-sheet').forEach(function (sheet) {
      var y0 = null, dy = 0;
      sheet.addEventListener('touchstart', function (e) {
        // Solo desde la parte de arriba (grip/cabecera), no mientras se desplaza la lista
        if (e.target.closest('.pf-sheet__body')) return;
        y0 = e.touches[0].clientY; dy = 0;
        sheet.style.transition = 'none';
      }, { passive: true });
      sheet.addEventListener('touchmove', function (e) {
        if (y0 === null) return;
        dy = Math.max(0, e.touches[0].clientY - y0);
        sheet.style.transform = 'translateY(' + dy + 'px)';
      }, { passive: true });
      sheet.addEventListener('touchend', function () {
        if (y0 === null) return;
        sheet.style.transition = '';
        sheet.style.transform = '';
        if (dy > 90) PF.closeSheet(sheet.id);
        y0 = null;
      });
    });
  });

  /* ─── CSRF + fetch JSON ─────────────────────────────────────────────── */
  PF.csrf = function () {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute('content') : '';
  };

  /**
   * POST/GET JSON contra las APIs de /futbol/api/*.
   * Devuelve el cuerpo ya parseado; lanza Error con el mensaje del servidor si falla.
   */
  PF.api = function (url, data, method) {
    var opts = {
      method: method || (data ? 'POST' : 'GET'),
      headers: { 'Accept': 'application/json', 'X-CSRFToken': PF.csrf() },
      credentials: 'same-origin'
    };
    if (data) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(data);
    }
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (body) {
        /* Sesión caducada. El servidor ya responde 401 con login:true, pero se
           mira también el rebote a /entrar por si alguna ruta se escapa: eso
           llegaba como un 200 con HTML que no se podía leer, y esta función
           devolvía {} como si la llamada hubiera ido bien. */
        if ((r.status === 401 && body.login) || (r.redirected && /\/entrar/.test(r.url))) {
          PF.toast('Tu sesión caducó. Te llevo a entrar otra vez.', 'error');
          setTimeout(function () { location.href = body.url || '/entrar'; }, 1400);
          throw new Error('Sesión caducada');
        }
        if (!r.ok || body.error) throw new Error(body.error || ('Error ' + r.status));
        return body;
      });
    });
  };

  /* ─── Aviso flotante ────────────────────────────────────────────────── */
  PF.toast = function (msg, kind) {
    var el = document.createElement('div');
    el.textContent = msg;
    el.style.cssText =
      'position:fixed;left:50%;transform:translateX(-50%);bottom:calc(110px + env(safe-area-inset-bottom,0px));' +
      'z-index:500;padding:11px 18px;border-radius:12px;font-size:13px;font-weight:700;' +
      'box-shadow:0 8px 20px rgba(0,0,0,.18);max-width:88vw;text-align:center;' +
      'opacity:0;transition:opacity .2s,transform .2s;' +
      (kind === 'error'
        ? 'background:#fee2e2;color:#991b1b;'
        : 'background:#0f172a;color:#fff;');
    document.body.appendChild(el);
    requestAnimationFrame(function () { el.style.opacity = '1'; });
    setTimeout(function () {
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 250);
    }, 2600);
  };

  /* ─── Iconos Feather ────────────────────────────────────────────────── */
  /* Se dibujan desde un sprite propio: sin CDN, sin peticiones extra y sin
     depender de que cargue una librería externa. */
  var ICONS = {
    'home': '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    'calendar': '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    'trending-up': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    'trending-down': '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>',
    'arrow-up-right': '<line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/>',
    'arrow-down-right': '<line x1="7" y1="7" x2="17" y2="17"/><polyline points="17 7 17 17 7 17"/>',
    'sliders': '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    'clipboard': '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    'message-circle': '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8z"/>',
    'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    'target': '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    'mic': '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>',
    'cpu': '<rect x="4" y="4" width="16" height="16" rx="2" ry="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
    'more-horizontal': '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    'chevron-right': '<polyline points="9 18 15 12 9 6"/>',
    'chevron-left': '<polyline points="15 18 9 12 15 6"/>',
    'chevron-down': '<polyline points="6 9 12 15 18 9"/>',
    'arrow-left': '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    'arrow-right': '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    'plus': '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    'x': '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    'check': '<polyline points="20 6 9 17 4 12"/>',
    'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    'zap': '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    'activity': '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    'heart': '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>',
    'mail': '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
    'bell': '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    'user-plus': '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>',
    'settings': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    'award': '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
    'bar-chart-2': '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    'droplet': '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
    'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    'wind': '<path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>',
    'smile': '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>',
    'shield': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    'flag': '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    'map-pin': '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    'edit-2': '<path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>',
    // Los usa la pantalla de evaluaciones, que copia los iconos de la app.
    'layers': '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    'edit-3': '<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
    'trash-2': '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
    'send': '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    'copy': '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    'share-2': '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
    'alert-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
    'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    'info': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
    'credit-card': '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
    'lock': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    'star': '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    'log-in': '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/>',
    'gift': '<polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>',
    'grid': '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    'repeat': '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
    'play': '<polygon points="5 3 19 12 5 21 5 3"/>',
    'video': '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>',
    'camera': '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
    'refresh-cw': '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
    'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    'filter': '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    'book-open': '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    'thermometer': '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4 4 0 1 0 5 0z"/>',
    'minus': '<line x1="5" y1="12" x2="19" y2="12"/>',
    'save': '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>'
  };

  /**
   * Sustituye <i data-ico="home"></i> por el SVG correspondiente.
   * Se llama al cargar y puede re-llamarse tras inyectar HTML dinámico.
   */
  PF.icons = function (root) {
    (root || document).querySelectorAll('[data-ico]').forEach(function (el) {
      var name = el.getAttribute('data-ico');
      var path = ICONS[name];
      if (!path) return;
      var cls = 'pf-ico ' + (el.className || '');
      var svg =
        '<svg class="' + cls.trim() + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + path + '</svg>';
      el.outerHTML = svg;
    });
  };

  document.addEventListener('DOMContentLoaded', function () { PF.icons(); });

  /* ─── Iniciales para avatares (design.ts › initials) ────────────────── */
  PF.initials = function (name) {
    if (!name) return '?';
    var p = String(name).trim().split(/\s+/);
    if (p.length >= 2) return (p[0][0] + p[1][0]).toUpperCase();
    return p[0].slice(0, 2).toUpperCase();
  };

  /* ─── Selector 1-10 (AddManualPlayerScreen.tsx › RatingStat) ─────────── */
  /* Usado en "Nuevo Jugador" y "Evaluar" (ver templates/_rating.html). Cada
     bloque .pf-rating trae sus botones 1-10, una insignia y un input oculto
     que guarda el valor elegido — de ahí lo lee el JS de cada pantalla al
     enviar el formulario. */
  var RATING_LABELS = {
    1: 'Muy bajo', 2: 'Bajo', 3: 'Por debajo del promedio', 4: 'Bajo promedio',
    5: 'Promedio', 6: 'Sobre el promedio', 7: 'Bueno', 8: 'Muy bueno',
    9: 'Excelente', 10: 'Élite'
  };
  function ratingColor(v) {
    if (v >= 9) return '#10b981';
    if (v >= 7) return '#3b82f6';
    if (v >= 5) return '#f59e0b';
    if (v >= 3) return '#f97316';
    return '#ef4444';
  }
  PF.ratings = function (root) {
    (root || document).querySelectorAll('[data-rating]').forEach(function (box) {
      if (box.dataset.ratingListo) return;   // no engancharlo dos veces
      box.dataset.ratingListo = '1';

      var input = box.querySelector('[data-rating-input]');
      var badgeN = box.querySelector('[data-rating-n]');
      var badge = box.querySelector('[data-rating-badge]');
      var hint = box.querySelector('[data-rating-hint]');
      var btns = box.querySelectorAll('[data-rating-btn]');

      function pintar(v) {
        var color = ratingColor(v);
        btns.forEach(function (b) {
          var on = parseInt(b.dataset.ratingBtn, 10) === v;
          b.setAttribute('aria-pressed', on ? 'true' : 'false');
          b.style.background = on ? color : '';
          b.style.borderColor = on ? color : '';
        });
        if (badge) badge.style.background = color;
        if (badgeN) badgeN.textContent = v;
        if (hint) { hint.textContent = RATING_LABELS[v] || ''; hint.style.color = color; }
        if (input) input.value = v;
      }

      btns.forEach(function (b) {
        b.addEventListener('click', function () { pintar(parseInt(b.dataset.ratingBtn, 10)); });
      });

      pintar(parseInt(box.dataset.value, 10) || 5);
    });
  };
  document.addEventListener('DOMContentLoaded', function () { PF.ratings(); });

  /* Lee todos los .pf-rating de un formulario: {campo: valor}. */
  PF.leerRatings = function (root) {
    var datos = {};
    (root || document).querySelectorAll('[data-rating-input]').forEach(function (i) {
      datos[i.dataset.campo] = parseInt(i.value, 10);
    });
    return datos;
  };

  /* ─── Copiar al portapapeles (código de equipo) ─────────────────────── */
  PF.copy = function (text, msg) {
    var done = function () { PF.toast(msg || 'Copiado'); };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done).catch(function () { PF.fallbackCopy(text, done); });
    } else {
      PF.fallbackCopy(text, done);
    }
  };
  PF.fallbackCopy = function (text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0;';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { PF.toast('No se pudo copiar', 'error'); }
    ta.remove();
  };
})();
