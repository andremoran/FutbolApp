/* ===========================================================================
   admin.js — Lo justo para que el panel funcione sin recargar.

   Sin dependencias externas: el panel tiene que abrir aunque el cliente esté
   detrás de un cortafuegos. Todo lo que hace es POST con el token CSRF,
   avisar del resultado y refrescar.
   =========================================================================== */
(function () {
  'use strict';

  const ADM = {};
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  ADM.csrf = () => (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

  /* ─── Llamadas ────────────────────────────────────────────────────────── */
  ADM.post = async function (url, datos) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': ADM.csrf() },
      body: JSON.stringify(datos || {}),
      credentials: 'same-origin',
    });
    let j = {};
    try { j = await r.json(); } catch (e) { /* respuesta sin JSON */ }
    if (!r.ok || j.error) throw new Error(j.error || 'No se pudo completar la acción.');
    return j;
  };

  /* Envuelve una acción: bloquea el botón, avisa y recarga si toca. */
  ADM.accion = async function (boton, url, datos, opciones) {
    const o = opciones || {};
    const original = boton ? boton.innerHTML : '';
    if (boton) { boton.disabled = true; boton.innerHTML = '…'; }
    try {
      const j = await ADM.post(url, datos);
      ADM.toast(j.mensaje || 'Listo.', 'ok');
      if (o.recargar !== false) setTimeout(() => location.reload(), 700);
      return j;
    } catch (e) {
      ADM.toast(e.message, 'mal');
      if (boton) { boton.disabled = false; boton.innerHTML = original; }
      throw e;
    }
  };

  /* ─── Avisos flotantes ────────────────────────────────────────────────── */
  ADM.toast = function (texto, tipo) {
    let caja = $('#adm-toasts');
    if (!caja) {
      caja = document.createElement('div');
      caja.id = 'adm-toasts';
      document.body.appendChild(caja);
    }
    const t = document.createElement('div');
    t.className = 'adm-toast adm-toast--' + (tipo || 'ok');
    t.innerHTML = '<span>' + (tipo === 'mal' ? '⚠️' : '✅') + '</span><span>'
                + String(texto).replace(/</g, '&lt;') + '</span>';
    caja.appendChild(t);
    setTimeout(() => {
      t.style.transition = 'opacity .3s';
      t.style.opacity = '0';
      setTimeout(() => t.remove(), 320);
    }, tipo === 'mal' ? 5200 : 3200);
  };

  /* ─── Modal ───────────────────────────────────────────────────────────── */
  ADM.abrir = function (id) {
    const m = document.getElementById(id);
    if (!m) return;
    m.classList.add('on');
    const back = $('#adm-modal-back');
    if (back) back.classList.add('on');
    const primero = m.querySelector('input:not([type=hidden]), select, textarea');
    if (primero) setTimeout(() => primero.focus(), 60);
  };

  ADM.cerrar = function (id) {
    if (id) {
      const m = document.getElementById(id);
      if (m) m.classList.remove('on');
    } else {
      $$('.adm-modal').forEach(m => m.classList.remove('on'));
    }
    if (!$$('.adm-modal.on').length) {
      const back = $('#adm-modal-back');
      if (back) back.classList.remove('on');
    }
  };

  /* ─── Copiar al portapapeles ──────────────────────────────────────────── */
  ADM.copiar = async function (texto, boton) {
    try {
      await navigator.clipboard.writeText(texto);
    } catch (e) {
      // Sin permiso de portapapeles (o sin HTTPS): se selecciona a la vieja usanza.
      const ta = document.createElement('textarea');
      ta.value = texto;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch (e2) { /* nada más que hacer */ }
      ta.remove();
    }
    ADM.toast('Copiado: ' + texto, 'ok');
    if (boton) {
      const antes = boton.textContent;
      boton.textContent = '✓';
      setTimeout(() => { boton.textContent = antes; }, 1400);
    }
  };

  /* ─── Filtro de tabla en el navegador ─────────────────────────────────── */
  ADM.filtrar = function (input, selectorFilas, contador) {
    const q = (input.value || '').trim().toLowerCase();
    let n = 0;
    $$(selectorFilas).forEach(fila => {
      const visible = !q || fila.textContent.toLowerCase().indexOf(q) !== -1;
      fila.style.display = visible ? '' : 'none';
      if (visible) n++;
    });
    if (contador) {
      const c = $(contador);
      if (c) c.textContent = n;
    }
  };

  /* ─── Confirmación ────────────────────────────────────────────────────── */
  /* Para lo que no se puede deshacer se pide escribir la palabra: un
     "¿seguro?" se acepta sin leer, escribir BORRAR obliga a mirar. */
  ADM.confirmarTexto = function (mensaje, palabra) {
    const r = window.prompt(mensaje + '\n\nEscribe ' + palabra + ' para confirmar:');
    return (r || '').trim().toUpperCase() === palabra.toUpperCase();
  };

  /* ─── Arranque ────────────────────────────────────────────────────────── */
  document.addEventListener('keydown', e => { if (e.key === 'Escape') ADM.cerrar(); });
  document.addEventListener('click', e => {
    if (e.target && e.target.id === 'adm-modal-back') ADM.cerrar();
  });

  window.ADM = ADM;
})();
