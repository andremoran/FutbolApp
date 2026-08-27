/* ============================================================================
   pizarra.js — La pizarra táctica: jugadas, rondos y ruedas de pases.

   Va en un archivo propio y no dentro de la plantilla porque son 600 líneas de
   dibujo: metidas en el HTML no se pueden leer, no las cachea el navegador y
   cualquier cambio obliga a recargar la página entera.

   CÓMO ESTÁ PENSADA
   ─────────────────
   Es un `<canvas>`, no SVG. La animación que ya funcionaba está escrita sobre
   canvas —interpola entre «momentos» con requestAnimationFrame— y rehacerla en
   SVG habría sido tocar justo lo único que no había que tocar. Así que el
   motor de reproducción es el mismo de siempre: mismo suavizado, misma
   duración por tramo y misma regla de dejar el tablero como estaba al acabar,
   porque reproducir no es editar.

   Lo único que cambió ahí: antes interpolaba `jugadores` y `rivales` por
   POSICIÓN en el array; ahora interpola cualquier elemento por su `id`. Sin
   eso, añadir un cono a mitad de una jugada descolocaba a todo el mundo.

   EL MODELO
   ─────────
     estado = {
       cancha:    'completa' | 'media' | 'tercio' | 'rondo' | 'vacia',
       elementos: [{id, tipo, x, y, n}]      // x,y en 0..1 sobre el lienzo
       trazos:    [{id, tipo, x1, y1, x2, y2}]
       momentos:  [{elementos: [{id, x, y}]}]
     }

   Las coordenadas son relativas (0..1) a propósito: la misma jugada se ve
   igual en un teléfono de 360 px y en un portátil, y se puede cambiar de
   cancha sin recolocar nada.
   ============================================================================ */
(function (global) {
  'use strict';

  // ── Qué se puede poner en el campo ────────────────────────────────────────
  //  El `r` es el radio en píxeles de lienzo; `mueve` distingue lo que se
  //  arrastra de lo que es decorado fijo (ninguno, de momento: todo se mueve).
  var TIPOS = {
    jugador:      { r: 15, color: '#047857', texto: '#fff', etiqueta: 'Jugador' },
    rival:        { r: 15, color: '#dc2626', texto: '#fff', etiqueta: 'Rival' },
    neutro:       { r: 15, color: '#f59e0b', texto: '#1f2937', etiqueta: 'Comodín' },
    portero:      { r: 15, color: '#7e6acb', texto: '#fff', etiqueta: 'Portero' },
    balon:        { r: 10, color: '#ffffff', texto: '#111', etiqueta: 'Balón' },
    cono:         { r: 11, color: '#f97316', texto: '#fff', etiqueta: 'Cono' },
    pica:         { r: 10, color: '#eab308', texto: '#111', etiqueta: 'Pica' },
    miniporteria: { r: 16, color: '#e5e7eb', texto: '#111', etiqueta: 'Miniportería' },
    aro:          { r: 13, color: '#38bdf8', texto: '#111', etiqueta: 'Aro' },
    texto:        { r: 12, color: '#ffffff', texto: '#111', etiqueta: 'Texto' }
  };

  //  Los cuatro trazos del lenguaje del fútbol. No son adorno: un entrenador
  //  lee «pase» y «conducción» por la forma de la línea sin leer la leyenda.
  var TRAZOS = {
    pase:       { etiqueta: 'Pase',       color: '#ffffff', ancho: 2.5, guion: [9, 6] },
    //  Entrecortada, no en zigzag. Se distingue del pase por el ritmo del
    //  guion: el pase son rayas largas y la conducción, puntos cortos.
    conduccion: { etiqueta: 'Conducción', color: '#ffffff', ancho: 2.5, guion: [3, 4] },
    desmarque:  { etiqueta: 'Desmarque',  color: '#fde047', ancho: 2.5 },
    tiro:       { etiqueta: 'Tiro',       color: '#ef4444', ancho: 4 }
  };

  //  Proporción del lienzo de cada cancha. Un rondo en un campo entero se ve
  //  como cuatro hormigas en una esquina: cada ejercicio pide su encuadre.
  var CANCHAS = {
    completa: { alto: 1.42, etiqueta: 'Campo entero' },
    media:    { alto: 0.95, etiqueta: 'Medio campo' },
    tercio:   { alto: 0.72, etiqueta: 'Último tercio' },
    rondo:    { alto: 1.00, etiqueta: 'Cuadro (rondo)' },
    vacia:    { alto: 1.00, etiqueta: 'Libre' }
  };

  var FORMACIONES = {
    '4-4-2':   [[.5, .08], [.18, .26], [.38, .24], [.62, .24], [.82, .26],
                [.18, .52], [.38, .50], [.62, .50], [.82, .52], [.40, .78], [.60, .78]],
    '4-3-3':   [[.5, .08], [.18, .26], [.38, .24], [.62, .24], [.82, .26],
                [.30, .48], [.50, .52], [.70, .48], [.18, .76], [.50, .80], [.82, .76]],
    '4-2-3-1': [[.5, .08], [.18, .26], [.38, .24], [.62, .24], [.82, .26],
                [.38, .44], [.62, .44], [.20, .64], [.50, .62], [.80, .64], [.50, .82]],
    '3-5-2':   [[.5, .08], [.28, .24], [.50, .22], [.72, .24],
                [.12, .48], [.34, .50], [.50, .46], [.66, .50], [.88, .48], [.38, .78], [.62, .78]],
    '5-3-2':   [[.5, .08], [.12, .28], [.30, .24], [.50, .22], [.70, .24], [.88, .28],
                [.32, .52], [.50, .50], [.68, .52], [.38, .78], [.62, .78]],
    '4-1-4-1': [[.5, .08], [.18, .26], [.38, .24], [.62, .24], [.82, .26],
                [.50, .42], [.18, .60], [.40, .58], [.60, .58], [.82, .60], [.50, .82]]
  };

  var _n = 0;
  function nuevoId() { return 'e' + (Date.now() % 100000) + (_n++); }

  function elemento(tipo, x, y, n) {
    return { id: nuevoId(), tipo: tipo, x: x, y: y, n: (n === undefined ? '' : n) };
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  LA PIZARRA
  // ══════════════════════════════════════════════════════════════════════════
  function Pizarra(lienzo, opciones) {
    this.c = lienzo;
    this.ctx = lienzo.getContext('2d');
    this.op = opciones || {};
    this.estado = { cancha: 'completa', elementos: [], trazos: [], momentos: [] };
    this.herramienta = 'mover';
    this.trazoActual = 'pase';
    this.historial = [];
    this.reproduciendo = false;
    this.arrastrando = null;
    this.dibujando = null;
    this._atar();
  }

  Pizarra.prototype.TIPOS = TIPOS;
  Pizarra.prototype.TRAZOS = TRAZOS;
  Pizarra.prototype.CANCHAS = CANCHAS;
  Pizarra.prototype.FORMACIONES = FORMACIONES;

  // ── Carga y compatibilidad ────────────────────────────────────────────────
  /*  Las jugadas guardadas antes de esta pizarra tienen otra forma:
      {jugadores, rivales, flechas}. Se traducen al vuelo — nadie va a abrir
      su jugada de hace tres meses para encontrarse el campo vacío.          */
  Pizarra.prototype.cargar = function (datos) {
    datos = datos || {};
    if (datos.elementos) {
      this.estado = {
        cancha: datos.cancha || 'completa',
        elementos: datos.elementos.map(function (e) {
          return { id: e.id || nuevoId(), tipo: e.tipo || 'jugador',
                   x: +e.x, y: +e.y, n: e.n === undefined ? '' : e.n };
        }),
        trazos: (datos.trazos || []).map(function (t) {
          return { id: t.id || nuevoId(), tipo: t.tipo || 'pase',
                   x1: +t.x1, y1: +t.y1, x2: +t.x2, y2: +t.y2 };
        }),
        momentos: datos.momentos || [],
        formacion: datos.formacion || ''
      };
    } else {
      var e = [];
      (datos.jugadores || []).forEach(function (j) {
        e.push({ id: nuevoId(), tipo: 'jugador', x: +j.x, y: +j.y, n: j.n });
      });
      (datos.rivales || []).forEach(function (r) {
        e.push({ id: nuevoId(), tipo: 'rival', x: +r.x, y: +r.y, n: '' });
      });
      this.estado = {
        cancha: 'completa',
        elementos: e,
        trazos: (datos.flechas || []).map(function (f) {
          return { id: nuevoId(), tipo: 'pase', x1: +f.x1, y1: +f.y1, x2: +f.x2, y2: +f.y2 };
        }),
        //  Los momentos viejos guardaban jugadores y rivales por separado; se
        //  descartan porque sin ids no hay forma de saber quién era quién.
        momentos: [],
        formacion: datos.formacion || ''
      };
    }
    this.redimensionar();
  };

  Pizarra.prototype.volcar = function () {
    return {
      version: 2,
      cancha: this.estado.cancha,
      elementos: this.estado.elementos,
      trazos: this.estado.trazos,
      momentos: this.estado.momentos,
      formacion: this.estado.formacion || ''
    };
  };

  // ── Medidas ───────────────────────────────────────────────────────────────
  Pizarra.prototype.redimensionar = function () {
    var ratio = (CANCHAS[this.estado.cancha] || CANCHAS.completa).alto;
    var ancho = Math.min(this.c.parentNode.clientWidth || 520, 560);
    var alto = Math.round(ancho * ratio);

    //  El campo se encoge para que quepa en la pantalla. Sin esto, en un
    //  teléfono de 667 px el campo entero llegaba hasta abajo y los botones de
    //  la animación quedaban fuera: para capturar un momento había que bajar,
    //  capturar y volver a subir, en cada paso de la jugada.
    var tope = this.op.altoMaximo ? this.op.altoMaximo() : 0;
    if (tope && alto > tope) {
      alto = Math.round(tope);
      ancho = Math.round(alto / ratio);
    }
    //  Se dibuja al doble en pantallas densas: si no, las líneas del campo y
    //  los números salen borrosos justo en el móvil, que es donde se usa.
    var dpr = Math.min(global.devicePixelRatio || 1, 2);
    this.c.width = ancho * dpr;
    this.c.height = alto * dpr;
    this.c.style.width = ancho + 'px';
    this.c.style.height = alto + 'px';
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.W = ancho;
    this.H = alto;
    this.pintar();
  };

  // ── Dibujo del campo ──────────────────────────────────────────────────────
  Pizarra.prototype.cancha = function () {
    var ctx = this.ctx, W = this.W, H = this.H, tipo = this.estado.cancha;

    ctx.fillStyle = '#15803d';
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(255,255,255,.035)';
    for (var i = 0; i < 10; i += 2) ctx.fillRect(0, i * H / 10, W, H / 10);

    ctx.strokeStyle = 'rgba(255,255,255,.85)';
    ctx.lineWidth = 2;
    var m = 12;

    if (tipo === 'vacia') return;

    if (tipo === 'rondo') {
      //  Un cuadro con rejilla: ni áreas ni círculo central, que en un rondo
      //  solo estorban. La rejilla ayuda a repartir a la gente a ojo.
      ctx.strokeRect(m, m, W - 2 * m, H - 2 * m);
      ctx.strokeStyle = 'rgba(255,255,255,.18)';
      ctx.lineWidth = 1;
      for (var g = 1; g < 4; g++) {
        ctx.beginPath();
        ctx.moveTo(m + (W - 2 * m) * g / 4, m);
        ctx.lineTo(m + (W - 2 * m) * g / 4, H - m);
        ctx.moveTo(m, m + (H - 2 * m) * g / 4);
        ctx.lineTo(W - m, m + (H - 2 * m) * g / 4);
        ctx.stroke();
      }
      return;
    }

    ctx.strokeRect(m, m, W - 2 * m, H - 2 * m);

    var areaW = (W - 2 * m) * 0.58, areaH = H * 0.16;
    var chicaW = (W - 2 * m) * 0.26, chicaH = H * 0.06;

    //  Portería de arriba: la hay en las tres canchas con marcas.
    ctx.strokeRect((W - areaW) / 2, m, areaW, areaH);
    ctx.strokeRect((W - chicaW) / 2, m, chicaW, chicaH);
    ctx.beginPath();
    ctx.arc(W / 2, m + areaH + 10, 22, 0.15 * Math.PI, 0.85 * Math.PI);
    ctx.stroke();
    this._punto(W / 2, m + areaH * 0.62);

    if (tipo === 'completa') {
      ctx.beginPath();
      ctx.moveTo(m, H / 2); ctx.lineTo(W - m, H / 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(W / 2, H / 2, Math.min(W, H) * 0.11, 0, 2 * Math.PI);
      ctx.stroke();
      this._punto(W / 2, H / 2);

      ctx.strokeRect((W - areaW) / 2, H - m - areaH, areaW, areaH);
      ctx.strokeRect((W - chicaW) / 2, H - m - chicaH, chicaW, chicaH);
      ctx.beginPath();
      ctx.arc(W / 2, H - m - areaH - 10, 22, 1.15 * Math.PI, 1.85 * Math.PI);
      ctx.stroke();
      this._punto(W / 2, H - m - areaH * 0.62);
    } else {
      //  Media y tercio: la línea de abajo es de puntos, para que se entienda
      //  que el campo sigue y no que el equipo juega en una caja.
      ctx.save();
      ctx.setLineDash([7, 7]);
      ctx.strokeStyle = 'rgba(255,255,255,.45)';
      ctx.beginPath();
      ctx.moveTo(m, H - m); ctx.lineTo(W - m, H - m);
      ctx.stroke();
      ctx.restore();
    }
  };

  Pizarra.prototype._punto = function (x, y) {
    var ctx = this.ctx;
    ctx.beginPath();
    ctx.arc(x, y, 2.5, 0, 2 * Math.PI);
    ctx.fillStyle = 'rgba(255,255,255,.85)';
    ctx.fill();
  };

  // ── Dibujo de los elementos ───────────────────────────────────────────────
  Pizarra.prototype.pintarElemento = function (e) {
    var ctx = this.ctx, meta = TIPOS[e.tipo] || TIPOS.jugador;
    var x = e.x * this.W, y = e.y * this.H, r = meta.r;

    ctx.save();
    ctx.shadowColor = 'rgba(0,0,0,.35)';
    ctx.shadowBlur = 4;
    ctx.shadowOffsetY = 2;

    if (e.tipo === 'cono') {
      ctx.beginPath();
      ctx.moveTo(x, y - r);
      ctx.lineTo(x + r * 0.85, y + r * 0.7);
      ctx.lineTo(x - r * 0.85, y + r * 0.7);
      ctx.closePath();
      ctx.fillStyle = meta.color;
      ctx.fill();
    } else if (e.tipo === 'pica') {
      ctx.fillStyle = meta.color;
      ctx.fillRect(x - 2, y - r, 4, r * 2);
      ctx.beginPath();
      ctx.ellipse(x, y + r, 7, 3, 0, 0, 2 * Math.PI);
      ctx.fillStyle = 'rgba(0,0,0,.25)';
      ctx.fill();
    } else if (e.tipo === 'miniporteria') {
      ctx.strokeStyle = meta.color;
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      ctx.moveTo(x - r, y + 5); ctx.lineTo(x - r, y - 5);
      ctx.lineTo(x + r, y - 5); ctx.lineTo(x + r, y + 5);
      ctx.stroke();
    } else if (e.tipo === 'aro') {
      ctx.strokeStyle = meta.color;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.ellipse(x, y, r, r * 0.55, 0, 0, 2 * Math.PI);
      ctx.stroke();
    } else if (e.tipo === 'balon') {
      //  Blanco con borde y un pentágono dentro. Antes era un círculo blanco
      //  con un punto: sobre el césped se leía como una mancha, y encima de
      //  una ficha clara desaparecía del todo.
      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fillStyle = '#fff';
      ctx.fill();
      ctx.shadowColor = 'transparent';
      ctx.lineWidth = 1.6;
      ctx.strokeStyle = '#111827';
      ctx.stroke();
      ctx.beginPath();
      for (var p = 0; p < 5; p++) {
        var ang = -Math.PI / 2 + p * 2 * Math.PI / 5;
        var px = x + r * 0.52 * Math.cos(ang), py = y + r * 0.52 * Math.sin(ang);
        if (p === 0) { ctx.moveTo(px, py); } else { ctx.lineTo(px, py); }
      }
      ctx.closePath();
      ctx.fillStyle = '#111827';
      ctx.fill();
    } else if (e.tipo === 'texto') {
      ctx.shadowColor = 'transparent';
      var txt = String(e.n || 'Texto');
      ctx.font = '700 13px -apple-system, Segoe UI, Roboto, sans-serif';
      var an = ctx.measureText(txt).width + 14;
      ctx.fillStyle = 'rgba(17,24,39,.82)';
      ctx.beginPath();
      //  `roundRect` es de Safari 16 en adelante. En uno anterior lanza, y
      //  como esto corre dentro del bucle de pintado, un throw aquí deja el
      //  campo entero en blanco. La esquina cuadrada se nota mucho menos.
      if (ctx.roundRect) {
        ctx.roundRect(x - an / 2, y - 11, an, 22, 6);
      } else {
        ctx.rect(x - an / 2, y - 11, an, 22);
      }
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(txt, x, y + 1);
      ctx.restore();
      return;
    } else {
      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fillStyle = meta.color;
      ctx.fill();
      ctx.shadowColor = 'transparent';
      ctx.lineWidth = 2;
      ctx.strokeStyle = 'rgba(255,255,255,.9)';
      ctx.stroke();
    }

    ctx.shadowColor = 'transparent';
    if (e.n !== '' && e.n !== undefined && e.n !== null &&
        ['jugador', 'rival', 'neutro', 'portero'].indexOf(e.tipo) >= 0) {
      ctx.fillStyle = meta.texto;
      ctx.font = '700 13px -apple-system, Segoe UI, Roboto, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(e.n), x, y + 1);
    }
    ctx.restore();
  };

  // ── Dibujo de los trazos ──────────────────────────────────────────────────
  Pizarra.prototype.pintarTrazo = function (t) {
    var ctx = this.ctx, meta = TRAZOS[t.tipo] || TRAZOS.pase;
    var x1 = t.x1 * this.W, y1 = t.y1 * this.H;
    var x2 = t.x2 * this.W, y2 = t.y2 * this.H;
    var ang = Math.atan2(y2 - y1, x2 - x1);
    var largo = Math.hypot(x2 - x1, y2 - y1);
    if (largo < 4) return;

    ctx.save();
    ctx.strokeStyle = meta.color;
    ctx.lineWidth = meta.ancho;
    ctx.lineCap = 'round';
    ctx.shadowColor = 'rgba(0,0,0,.4)';
    ctx.shadowBlur = 3;

    //  La punta se deja libre para la cabeza de la flecha: si la línea llega
    //  hasta el final, la cabeza queda montada encima y se ve un borrón.
    var fin = largo - 11;

    {
      ctx.setLineDash(meta.guion || []);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x1 + Math.cos(ang) * fin, y1 + Math.sin(ang) * fin);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.fillStyle = meta.color;
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - 12 * Math.cos(ang - 0.42), y2 - 12 * Math.sin(ang - 0.42));
    ctx.lineTo(x2 - 12 * Math.cos(ang + 0.42), y2 - 12 * Math.sin(ang + 0.42));
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  };

  Pizarra.prototype.pintar = function () {
    this.cancha();
    var self = this;
    this.estado.trazos.forEach(function (t) { self.pintarTrazo(t); });
    this.estado.elementos.forEach(function (e) { self.pintarElemento(e); });
    if (this.dibujando) this.pintarTrazo(this.dibujando);
  };

  // ── Interacción ───────────────────────────────────────────────────────────
  Pizarra.prototype._pos = function (ev) {
    var caja = this.c.getBoundingClientRect();
    var p = (ev.touches && ev.touches[0]) || ev;
    return { x: (p.clientX - caja.left) / caja.width,
             y: (p.clientY - caja.top) / caja.height };
  };

  Pizarra.prototype._elementoEn = function (p) {
    //  De arriba abajo: se coge lo último dibujado, que es lo que el dedo ve.
    for (var i = this.estado.elementos.length - 1; i >= 0; i--) {
      var e = this.estado.elementos[i];
      var meta = TIPOS[e.tipo] || TIPOS.jugador;
      var dx = (e.x - p.x) * this.W, dy = (e.y - p.y) * this.H;
      //  18 px de margen: el radio real es pequeño y un dedo no es un ratón.
      if (Math.hypot(dx, dy) <= Math.max(meta.r, 18)) return e;
    }
    return null;
  };

  Pizarra.prototype.guardarHistorial = function () {
    this.historial.push(JSON.stringify(this.estado));
    if (this.historial.length > 40) this.historial.shift();
    if (this.op.alCambiar) this.op.alCambiar();
  };

  Pizarra.prototype.deshacer = function () {
    if (!this.historial.length) return false;
    this.estado = JSON.parse(this.historial.pop());
    this.redimensionar();
    return true;
  };

  Pizarra.prototype._atar = function () {
    var self = this;

    function abajo(ev) {
      if (self.reproduciendo) return;
      ev.preventDefault();
      var p = self._pos(ev);
      var h = self.herramienta;

      if (h === 'mover') {
        var e = self._elementoEn(p);
        if (e) {
          self.guardarHistorial();
          self.arrastrando = e;
          //  Pulsación larga sobre una ficha: cambiarle el dorsal o el texto.
          //  Sin esto los números eran los que salieran y un rótulo no se
          //  podía corregir nunca. En el móvil no hay doble clic ni menú.
          self._pulsacion = setTimeout(function () {
            self.arrastrando = null;
            self.renombrar(e);
          }, 620);
        }
        return;
      }
      if (h === 'borrar') {
        var v = self._elementoEn(p);
        self.guardarHistorial();
        if (v) {
          self.estado.elementos = self.estado.elementos.filter(function (x) { return x !== v; });
        } else {
          //  Sin elemento debajo se borra el trazo más cercano: si no, la
          //  goma solo serviría para la mitad de lo que hay en el campo.
          var cerca = self._trazoCercaDe(p);
          if (cerca) {
            self.estado.trazos = self.estado.trazos.filter(function (x) { return x !== cerca; });
          }
        }
        self.pintar();
        return;
      }
      if (h === 'trazo') {
        self.dibujando = { id: nuevoId(), tipo: self.trazoActual,
                           x1: p.x, y1: p.y, x2: p.x, y2: p.y };
        return;
      }
      //  Cualquier otra herramienta es un elemento que se pone donde se toca.
      self.guardarHistorial();
      var puesto = elemento(h, p.x, p.y, self._siguienteNumero(h));
      //  Un rótulo sin texto es un rectángulo que pone «Texto» y no hay forma
      //  de cambiarlo: se pregunta al ponerlo. Si no escribe nada, no se pone
      //  —mejor eso que dejarle basura en el campo.
      if (h === 'texto') {
        var escrito = (global.prompt('¿Qué pone el rótulo?', '') || '').trim();
        if (!escrito) { self.historial.pop(); return; }
        puesto.n = escrito.slice(0, 24);
      }
      self.estado.elementos.push(puesto);
      self.pintar();
      if (self.op.alPoner) self.op.alPoner(h);
    }

    function mueve(ev) {
      if (self.reproduciendo) return;
      if (self.arrastrando) {
        ev.preventDefault();
        var p = self._pos(ev);
        //  Si el dedo se movió, ya no es una pulsación larga: es un arrastre.
        if (self._pulsacion &&
            Math.hypot((p.x - self.arrastrando.x) * self.W,
                       (p.y - self.arrastrando.y) * self.H) > 7) {
          clearTimeout(self._pulsacion);
          self._pulsacion = null;
        }
        self.arrastrando.x = Math.max(0.02, Math.min(0.98, p.x));
        self.arrastrando.y = Math.max(0.02, Math.min(0.98, p.y));
        self.pintar();
      } else if (self.dibujando) {
        ev.preventDefault();
        var q = self._pos(ev);
        self.dibujando.x2 = q.x;
        self.dibujando.y2 = q.y;
        self.pintar();
      }
    }

    function arriba() {
      if (self._pulsacion) { clearTimeout(self._pulsacion); self._pulsacion = null; }
      if (self.dibujando) {
        var t = self.dibujando;
        self.dibujando = null;
        if (Math.hypot((t.x2 - t.x1) * self.W, (t.y2 - t.y1) * self.H) > 14) {
          self.guardarHistorial();
          self.estado.trazos.push(t);
        }
        self.pintar();
      }
      self.arrastrando = null;
    }

    this.c.addEventListener('mousedown', abajo);
    this.c.addEventListener('touchstart', abajo, { passive: false });
    global.addEventListener('mousemove', mueve);
    global.addEventListener('touchmove', mueve, { passive: false });
    global.addEventListener('mouseup', arriba);
    global.addEventListener('touchend', arriba);
    global.addEventListener('resize', function () { self.redimensionar(); });
  };

  /*  Cambiarle el dorsal a una ficha o el texto a un rótulo. Es un `prompt`
      y no una ventana propia a posta: en el campo, con una mano y el sol de
      frente, el teclado del sistema es lo más rápido que hay.  */
  Pizarra.prototype.renombrar = function (e) {
    var esRotulo = e.tipo === 'texto';
    var actual = (e.n === undefined || e.n === null) ? '' : String(e.n);
    var puesto = global.prompt(
      esRotulo ? '¿Qué pone el rótulo?' : 'Dorsal o inicial de la ficha:', actual);
    if (puesto === null) return;
    this.guardarHistorial();
    e.n = puesto.trim().slice(0, esRotulo ? 24 : 3);
    this.pintar();
    if (this.op.alRenombrar) this.op.alRenombrar(e);
  };


  Pizarra.prototype._trazoCercaDe = function (p) {
    var mejor = null, mejorD = 0.05;
    this.estado.trazos.forEach(function (t) {
      //  Distancia del punto al segmento, en coordenadas relativas.
      var vx = t.x2 - t.x1, vy = t.y2 - t.y1;
      var largo2 = vx * vx + vy * vy;
      var u = largo2 ? Math.max(0, Math.min(1, ((p.x - t.x1) * vx + (p.y - t.y1) * vy) / largo2)) : 0;
      var d = Math.hypot(p.x - (t.x1 + u * vx), p.y - (t.y1 + u * vy));
      if (d < mejorD) { mejorD = d; mejor = t; }
    });
    return mejor;
  };

  Pizarra.prototype._siguienteNumero = function (tipo) {
    if (['jugador', 'rival', 'neutro', 'portero'].indexOf(tipo) < 0) return '';
    //  El siguiente al MAYOR, no «cuántos hay». Contando, al borrar al 2 y
    //  añadir otro salía un segundo 3: dos fichas con el mismo dorsal en el
    //  campo, que es justo lo que una pizarra no puede permitirse.
    var alto = 0;
    this.estado.elementos.forEach(function (e) {
      if (e.tipo !== tipo) return;
      var n = parseInt(e.n, 10);
      if (!isNaN(n) && n > alto) alto = n;
    });
    return alto + 1;
  };

  // ── Acciones ──────────────────────────────────────────────────────────────
  Pizarra.prototype.aplicarFormacion = function (nombre) {
    var puntos = FORMACIONES[nombre] || FORMACIONES['4-4-2'];
    this.guardarHistorial();
    //  Se quitan solo los propios: los rivales, conos y balones que ya estaban
    //  puestos no tienen por qué desaparecer al probar otra formación.
    this.estado.elementos = this.estado.elementos.filter(function (e) {
      return e.tipo !== 'jugador' && e.tipo !== 'portero';
    });
    var self = this;
    puntos.forEach(function (p, i) {
      self.estado.elementos.push(elemento(i === 0 ? 'portero' : 'jugador', p[0], p[1], i + 1));
    });
    this.estado.formacion = nombre;
    this.estado.cancha = 'completa';
    this.redimensionar();
  };

  Pizarra.prototype.limpiar = function () {
    this.guardarHistorial();
    this.estado.elementos = [];
    this.estado.trazos = [];
    this.estado.momentos = [];
    this.pintar();
  };

  Pizarra.prototype.borrarTrazos = function () {
    this.guardarHistorial();
    this.estado.trazos = [];
    this.pintar();
  };

  Pizarra.prototype.cambiarCancha = function (clave) {
    if (!CANCHAS[clave]) return;
    this.guardarHistorial();
    this.estado.cancha = clave;
    this.redimensionar();
  };

  // ══════════════════════════════════════════════════════════════════════════
  //  ANIMACIÓN — el motor de siempre
  //
  //  Mismo suavizado, misma duración por tramo y misma regla de dejar el
  //  tablero como estaba al acabar. Lo ÚNICO que cambió: antes emparejaba los
  //  elementos por su posición en el array y ahora los empareja por `id`, para
  //  que añadir un cono a mitad de la jugada no descoloque a todo el mundo.
  // ══════════════════════════════════════════════════════════════════════════
  Pizarra.prototype.capturarMomento = function () {
    this.estado.momentos = this.estado.momentos || [];
    if (this.estado.momentos.length >= 20) return false;
    this.estado.momentos.push({
      elementos: this.estado.elementos.map(function (e) {
        return { id: e.id, x: e.x, y: e.y };
      })
    });
    return true;
  };

  Pizarra.prototype.irAMomento = function (i) {
    var m = (this.estado.momentos || [])[i];
    if (!m) return;
    this.guardarHistorial();
    var por = {};
    m.elementos.forEach(function (e) { por[e.id] = e; });
    this.estado.elementos.forEach(function (e) {
      if (por[e.id]) { e.x = por[e.id].x; e.y = por[e.id].y; }
    });
    this.pintar();
  };

  Pizarra.prototype.borrarMomento = function (i) {
    this.estado.momentos.splice(i, 1);
  };

  Pizarra.prototype.reproducir = function (alTerminar) {
    var self = this;
    var ms = this.estado.momentos || [];
    if (ms.length < 2 || this.reproduciendo) return false;

    this.reproduciendo = true;
    //  Se guardan solo las POSICIONES, no los objetos. Devolver el array
    //  entero cambiaba la identidad de cada elemento al acabar, y cualquier
    //  cosa que tuviera cogida una ficha —la que se está arrastrando, sin ir
    //  más lejos— se quedaba apuntando a un objeto que ya no está en el
    //  tablero. Se mueven los mismos de siempre y punto.
    var antes = {};
    this.estado.elementos.forEach(function (e) { antes[e.id] = { x: e.x, y: e.y }; });

    var DURACION = 1100;                 // ms por tramo
    var tramo = 0;
    var inicio = performance.now();

    function paso(ahora) {
      var t = Math.min(1, (ahora - inicio) / DURACION);
      // Suavizado: arranca y frena despacio, como se mueve un jugador.
      var e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

      var a = {}, b = {};
      ms[tramo].elementos.forEach(function (x) { a[x.id] = x; });
      ms[tramo + 1].elementos.forEach(function (x) { b[x.id] = x; });

      self.estado.elementos.forEach(function (el) {
        var de = a[el.id], hacia = b[el.id] || de;
        if (!de) return;               // apareció después: se queda quieto
        el.x = de.x + (hacia.x - de.x) * e;
        el.y = de.y + (hacia.y - de.y) * e;
      });
      self.pintar();

      if (t < 1) {
        requestAnimationFrame(paso);
      } else if (tramo + 2 < ms.length) {
        tramo++;
        inicio = performance.now();
        requestAnimationFrame(paso);
      } else {
        self.reproduciendo = false;
        // Se deja como estaba antes de reproducir: reproducir no es editar.
        self.estado.elementos.forEach(function (e) {
          if (antes[e.id]) { e.x = antes[e.id].x; e.y = antes[e.id].y; }
        });
        self.pintar();
        if (alTerminar) alTerminar();
      }
    }
    requestAnimationFrame(paso);
    return true;
  };

  global.Pizarra = Pizarra;
})(window);
