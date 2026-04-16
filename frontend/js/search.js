/**
 * Search modes: GPS, draw zone, address autocomplete.
 */

let searchLat = null, searchLon = null;
let currentSearchMode = null;
let drawActive = false;
let drawing = false;
let drawnPolygon = [];
let drawPolyline = null;
let drawPolygonLayer = null;

function setSearchMode(mode) {
  currentSearchMode = mode;
  document.querySelectorAll('.search-tabs:not(.action-tabs) .search-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.search-mode').forEach(m => m.classList.remove('active'));
  document.querySelector(`.search-tab[onclick="setSearchMode('${mode}')"]`).classList.add('active');
  document.getElementById('mode-' + mode).classList.add('active');
  document.getElementById('search-btn').style.display = 'block';
  document.getElementById('action-tabs').style.display = 'flex';
  document.getElementById('k-control').style.display = mode === 'draw' ? 'none' : 'block';
  document.getElementById('map-mode-toggle').classList.remove('visible');
  if (mode === 'draw') {
    if (isMobile()) {
      drawActive = false;
      closeSidebar();
      document.getElementById('map-mode-toggle').classList.add('visible');
      setMapMode('move');
    } else {
      drawActive = true;
      map.dragging.disable();
      document.getElementById('map').classList.add('drawing');
    }
  } else {
    drawActive = false;
    map.dragging.enable();
    document.getElementById('map').classList.remove('drawing');
  }
}

function setMapMode(m) {
  document.getElementById('mode-btn-move').classList.toggle('active', m === 'move');
  document.getElementById('mode-btn-draw').classList.toggle('active', m === 'draw');
  if (m === 'draw') {
    drawActive = true;
    map.dragging.disable();
    document.getElementById('map').classList.add('drawing');
  } else {
    drawActive = false;
    map.dragging.enable();
    document.getElementById('map').classList.remove('drawing');
  }
}

/* ── Freehand drawing ── */
function drawStart(latlng) {
  drawing = true;
  clearDrawing(true);
  drawnPolygon = [latlng];
  drawPolyline = L.polyline(drawnPolygon, {
    color: '#3b82f6', weight: 3, opacity: 0.8, dashArray: '6,4'
  }).addTo(map);
}

function drawMove(latlng) {
  drawnPolygon.push(latlng);
  drawPolyline.addLatLng(latlng);
}

function drawEnd() {
  drawing = false;
  if (drawnPolygon.length < 5) return;
  if (drawPolyline) { map.removeLayer(drawPolyline); drawPolyline = null; }
  drawPolygonLayer = L.polygon(drawnPolygon, {
    color: '#3b82f6', fillColor: '#3b82f6',
    fillOpacity: 0.15, weight: 2.5
  }).addTo(map);
  document.getElementById('clear-draw-btn').classList.add('show');
  const hint = document.getElementById('draw-hint');
  hint.textContent = 'Zona seleccionada';
  hint.classList.add('done');
  if (isMobile()) {
    setMapMode('move');
    document.getElementById('map-mode-toggle').classList.remove('visible');
    openSidebar();
  }
}

/* ── Mouse events (desktop) ── */
let middlePanning = false;
let panStart = null;

map.on('mousedown', function (e) {
  if (!drawActive) return;
  if (e.originalEvent.button === 1) {
    middlePanning = true;
    panStart = e.containerPoint;
    e.originalEvent.preventDefault();
    return;
  }
  if (e.originalEvent.button === 0) drawStart(e.latlng);
});
map.on('mousemove', function (e) {
  if (middlePanning && panStart) {
    const dx = e.containerPoint.x - panStart.x;
    const dy = e.containerPoint.y - panStart.y;
    map.panBy([-dx, -dy], { animate: false });
    panStart = e.containerPoint;
    return;
  }
  if (drawing) drawMove(e.latlng);
});
map.on('mouseup', function (e) {
  if (middlePanning) { middlePanning = false; panStart = null; return; }
  if (drawing) drawEnd();
});

const mapEl = document.getElementById('map');
mapEl.addEventListener('mousedown', function (e) { if (e.button === 1) e.preventDefault(); });

/* ── Touch events (mobile) ── */
mapEl.addEventListener('touchstart', function (e) {
  if (!drawActive) return;
  e.preventDefault();
  const t = e.touches[0];
  drawStart(map.containerPointToLatLng([t.clientX, t.clientY - 56]));
}, { passive: false });
mapEl.addEventListener('touchmove', function (e) {
  if (!drawing) return;
  e.preventDefault();
  const t = e.touches[0];
  drawMove(map.containerPointToLatLng([t.clientX, t.clientY - 56]));
}, { passive: false });
mapEl.addEventListener('touchend', function (e) {
  if (drawing) { e.preventDefault(); drawEnd(); }
}, { passive: false });

/* ── Point-in-polygon (ray casting) ── */
function pointInPolygon(lat, lng, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const yi = polygon[i].lat, xi = polygon[i].lng;
    const yj = polygon[j].lat, xj = polygon[j].lng;
    if (((yi > lat) !== (yj > lat)) && (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }
  return inside;
}

function clearDrawing(silent) {
  if (drawPolyline) { map.removeLayer(drawPolyline); drawPolyline = null; }
  if (drawPolygonLayer) { map.removeLayer(drawPolygonLayer); drawPolygonLayer = null; }
  drawnPolygon = [];
  if (!silent) {
    document.getElementById('clear-draw-btn').classList.remove('show');
    document.getElementById('search-results').className = 'result-box';
    const hint = document.getElementById('draw-hint');
    hint.textContent = 'Arrastra sobre el mapa para seleccionar una zona';
    hint.classList.remove('done');
    if (isMobile()) {
      closeSidebar();
      document.getElementById('map-mode-toggle').classList.add('visible');
      setMapMode('move');
    }
  }
}

/* ── GPS locate ── */
function gpsLocate() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) { resolve(false); return; }
    navigator.geolocation.getCurrentPosition(pos => {
      searchLat = pos.coords.latitude;
      searchLon = pos.coords.longitude;
      map.setView([searchLat, searchLon], 15);
      showUserLocation(searchLat, searchLon);
      resolve(true);
    }, () => {
      resolve(false);
    }, { enableHighAccuracy: true, timeout: 8000 });
  });
}

/* ── Google Places Autocomplete ── */
let gPlacesReady = false;
let addrPredictions = [];
let addrTimer = null;
let addrIdx = -1;

async function initGooglePlaces() {
  try {
    await google.maps.importLibrary('places');
    gPlacesReady = true;
  } catch (e) { console.warn('Google Places not available, using Nominatim fallback'); }
}
initGooglePlaces();

function onAddrInput() {
  clearTimeout(addrTimer);
  const q = document.getElementById('address-input').value.trim();
  if (q.length < 2) { hideAddrList(); return; }
  addrTimer = setTimeout(() => fetchSuggestions(q), 250);
}

async function fetchSuggestions(q) {
  if (gPlacesReady) {
    try {
      const { suggestions } = await google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions({
        input: q,
        includedRegionCodes: ['mx'],
        locationBias: { north: 20.78, south: 20.55, east: -103.25, west: -103.45 },
      });
      addrPredictions = suggestions.map(s => s.placePrediction);
      renderAddrList();
    } catch { hideAddrList(); }
  } else {
    try {
      const resp = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q + ', Guadalajara, Mexico')}&limit=5`);
      const results = await resp.json();
      addrPredictions = results.map(r => ({
        _text: r.display_name.split(',').slice(0, 3).join(', '),
        _lat: r.lat, _lon: r.lon,
      }));
      renderAddrList();
    } catch { hideAddrList(); }
  }
}

function renderAddrList() {
  const list = document.getElementById('addr-list');
  addrIdx = -1;
  if (!addrPredictions.length) { hideAddrList(); return; }
  list.innerHTML = addrPredictions.map((p, i) => {
    const main = p.mainText?.text || p._text || '';
    const sub = p.secondaryText?.text || '';
    return `<div class="addr-item" onmousedown="pickAddrItem(${i})">${main}${sub ? '<small>' + sub + '</small>' : ''}</div>`;
  }).join('');
  list.classList.add('show');
}

function hideAddrList() {
  document.getElementById('addr-list').classList.remove('show');
  addrIdx = -1;
}

async function pickAddrItem(i) {
  const p = addrPredictions[i];
  document.getElementById('address-input').value = p.mainText?.text || p._text || '';
  hideAddrList();
  if (p._lat) {
    searchLat = parseFloat(p._lat);
    searchLon = parseFloat(p._lon);
    map.setView([searchLat, searchLon], 15);
    searchNearby();
  } else if (p.placeId) {
    try {
      const place = new google.maps.places.Place({ id: p.placeId });
      await place.fetchFields({ fields: ['location'] });
      if (place.location) {
        searchLat = place.location.lat();
        searchLon = place.location.lng();
        map.setView([searchLat, searchLon], 15);
        searchNearby();
      }
    } catch (e) { console.error('Place fetch error:', e); }
  }
}

function onAddrKey(e) {
  const items = document.querySelectorAll('.addr-item');
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    addrIdx = Math.min(addrIdx + 1, items.length - 1);
    items.forEach((el, i) => el.style.background = i === addrIdx ? '#f0fdf4' : '');
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    addrIdx = Math.max(addrIdx - 1, 0);
    items.forEach((el, i) => el.style.background = i === addrIdx ? '#f0fdf4' : '');
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (addrIdx >= 0) pickAddrItem(addrIdx);
    else searchNearby();
  } else if (e.key === 'Escape') {
    hideAddrList();
  }
}

/* ── Unified search ── */
async function searchNearby() {
  if (!currentSearchMode) return;
  const box = document.getElementById('search-results');

  if (currentSearchMode === 'draw') {
    if (drawnPolygon.length < 5) return;
    let latSum = 0, lonSum = 0;
    drawnPolygon.forEach(p => { latSum += p.lat; lonSum += p.lng; });
    const cLat = latSum / drawnPolygon.length;
    const cLon = lonSum / drawnPolygon.length;
    try {
      const resp = await fetch(`/api/stations/nearest?lon=${cLon}&lat=${cLat}&k=1000&real_only=true`, { headers: API_HEADERS });
      const all = await resp.json();
      const inside = all.filter(s => pointInPolygon(s.latitude, s.longitude, drawnPolygon) && passesFilter(s) && passesActionFilter(s));
      box.className = 'result-box show';
      if (!inside.length) { box.innerHTML = '<div style="color:#888">No hay estaciones dentro de la zona dibujada.</div>'; return; }
      box.innerHTML = `<div style="font-size:11px;color:#888;margin-bottom:8px">${inside.length} estacion${inside.length > 1 ? 'es' : ''} dentro de la zona</div>` +
        inside.map(s => `
        <div class="result-item" style="cursor:pointer" onclick="map.setView([${s.latitude},${s.longitude}],16)">
          <div class="result-name">${s.name}</div>
          <div class="result-meta">ID: ${s.id} &middot; ${s.available_bikes}/${s.total_slots} bicis &middot; ${Math.round(s.distance_m)}m</div>
        </div>
      `).join('');
      showSearchResults(inside); appendClearBtn();
    } catch (e) {
      if (e.message !== 'rate_limit') {
        box.className = 'result-box show';
        box.innerHTML = '<div style="color:#ef4444">Error de conexion</div>';
      }
    }
    return;
  }

  const k = document.getElementById('search-k').value || 5;
  if (currentSearchMode === 'address') {
    if (searchLat === null || searchLon === null) {
      const input = document.getElementById('address-input');
      const addr = input ? input.value.trim() : '';
      if (!addr) return;
      box.className = 'result-box show';
      box.innerHTML = '<div style="color:#888">Buscando direccion...</div>';
      try {
        const geo = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(addr + ', Guadalajara, Mexico')}&limit=1`);
        const results = await geo.json();
        if (!results.length) { box.innerHTML = '<div style="color:#888">No se encontro la direccion.</div>'; return; }
        searchLat = parseFloat(results[0].lat);
        searchLon = parseFloat(results[0].lon);
        map.setView([searchLat, searchLon], 15);
      } catch {
        box.innerHTML = '<div style="color:#ef4444">Error buscando direccion</div>';
        return;
      }
    }
  }

  if (currentSearchMode === 'gps') {
    const ok = await gpsLocate();
    if (!ok) return;
  }
  if ((currentSearchMode === 'gps' || currentSearchMode === 'address') && (searchLat === null || searchLon === null)) {
    box.className = 'result-box show';
    box.innerHTML = '<div style="color:#dc2626">No se pudo obtener la ubicacion.</div>';
    return;
  }
  try {
    const fetchK = Math.min(k * 10, 1000);
    const resp = await fetch(`/api/stations/nearest?lon=${searchLon}&lat=${searchLat}&k=${fetchK}&real_only=true`, { headers: API_HEADERS });
    const raw = await resp.json();
    const data = raw.filter(s => passesFilter(s) && passesActionFilter(s)).slice(0, k);
    box.className = 'result-box show';
    if (!data.length) { box.innerHTML = '<div style="color:#888">No se encontraron estaciones.</div>'; return; }
    box.innerHTML = `<div style="font-size:11px;color:#888;margin-bottom:8px">${data.length} estacion${data.length > 1 ? 'es' : ''} encontrada${data.length > 1 ? 's' : ''}</div>` +
      data.map(s => `
      <div class="result-item" style="cursor:pointer" onclick="map.setView([${s.latitude},${s.longitude}],16)">
        <div class="result-name">${s.name}</div>
        <div class="result-meta">ID: ${s.id} &middot; ${s.available_bikes}/${s.total_slots} bicis &middot; ${Math.round(s.distance_m)}m</div>
      </div>
    `).join('');
    showSearchResults(data); appendClearBtn();
  } catch (e) {
    if (e.message !== 'rate_limit') {
      box.className = 'result-box show';
      box.innerHTML = '<div style="color:#ef4444">Error de conexion</div>';
    }
  }
}
