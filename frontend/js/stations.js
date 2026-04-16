/**
 * Station rendering: markers, popups, load/reserve/return.
 */

let markers = L.layerGroup().addTo(map);
let userMarker = null;
let searchActive = false;

function markerColor(s) {
  if (!s.is_active) return '#c4c4c4';
  const ratio = s.available_bikes / s.total_slots;
  if (ratio === 0) return '#ef4444';
  if (ratio < 0.3) return '#f59e0b';
  return '#22c55e';
}

function createIcon(color, size) {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:${size}px; height:${size}px; border-radius:50%;
      background:${color};
      border: 2.5px solid rgba(255,255,255,.85);
      box-shadow: 0 1px 4px rgba(0,0,0,.3);
      transition: transform .15s;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function dotSize() {
  const z = map.getZoom();
  if (z >= 16) return 18;
  if (z >= 14) return 14;
  if (z >= 12) return 10;
  return 8;
}

function stationPopupHtml(s) {
  const color = markerColor(s);
  const ratio = s.available_bikes / s.total_slots;
  return `
    <div class="station-popup">
      <div class="popup-header">
        <div class="station-name">${s.name}</div>
        <div class="popup-actions">
          <button class="popup-action" onclick="editStation(${s.id})" title="Editar">&#9998;</button>
          <button class="popup-action" onclick="confirmDelete(${s.id}, this)" title="Eliminar">&#128465;</button>
        </div>
      </div>
      <div class="station-location">${s.location || 'Guadalajara'}</div>
      <div class="availability">
        <div class="dot" style="background:${color}"></div>
        <span class="count">${s.available_bikes}</span>
        <span class="label">/ ${s.total_slots} bicicletas</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:${ratio * 100}%;background:${color}"></div>
      </div>
      ${s.distance_m != null ? `<div class="distance">${Math.round(s.distance_m)}m de distancia</div>` : ''}
      <div class="popup-btns">
        <button class="popup-btn btn-reserve" onclick="reserveBike(${s.id}, this)"
          ${s.available_bikes === 0 ? 'disabled' : ''}>
          ${s.available_bikes === 0 ? 'Sin bicis' : 'Reservar'}
        </button>
        <button class="popup-btn btn-return" onclick="returnBike(${s.id}, this)"
          ${s.available_bikes >= s.total_slots ? 'disabled' : ''}>
          ${s.available_bikes >= s.total_slots ? 'Llena' : 'Entregar'}
        </button>
      </div>
    </div>`;
}

async function loadStations() {
  const center = map.getCenter();
  try {
    const resp = await fetch(
      `/api/stations/nearest?lon=${center.lng}&lat=${center.lat}&k=1000&real_only=true`,
      { headers: API_HEADERS }
    );
    const stations = await resp.json();
    markers.clearLayers();
    const size = dotSize();
    stations.filter(passesFilter).forEach(s => {
      const m = L.marker([s.latitude, s.longitude], { icon: createIcon(markerColor(s), size) });
      m.stationId = s.id;
      m.bindPopup(stationPopupHtml(s), { closeButton: false });
      markers.addLayer(m);
    });
  } catch (e) {
    console.error('Error cargando estaciones:', e);
  }
}

async function refreshStation(id) {
  try {
    const resp = await fetch(`/api/stations/${id}`, { headers: API_HEADERS });
    if (!resp.ok) return;
    const s = await resp.json();
    markers.eachLayer(m => {
      if (m.stationId === id) {
        m.setIcon(createIcon(markerColor(s), dotSize()));
        m.setPopupContent(stationPopupHtml(s));
      }
    });
  } catch (e) { console.error('refreshStation error:', e); }
}

async function reserveBike(id, btn) {
  btn.disabled = true;
  btn.textContent = 'Reservando...';
  try {
    const resp = await fetch(`/api/stations/${id}/reserve`, { method: 'POST', headers: API_HEADERS });
    if (resp.ok) {
      btn.textContent = 'Reservada!';
      btn.style.background = '#16a34a';
      setTimeout(() => refreshStation(id), 800);
    } else {
      const d = await resp.json();
      btn.textContent = d.detail || 'No disponible';
      btn.style.background = '#ef4444';
    }
  } catch (e) {
    if (e.message !== 'rate_limit') btn.textContent = 'Error';
  }
}

async function returnBike(id, btn) {
  btn.disabled = true;
  btn.textContent = 'Entregando...';
  try {
    const resp = await fetch(`/api/stations/${id}/return`, { method: 'POST', headers: API_HEADERS });
    if (resp.ok) {
      btn.textContent = 'Entregada!';
      btn.style.background = '#1d4ed8';
      setTimeout(() => refreshStation(id), 800);
    } else {
      const d = await resp.json();
      btn.textContent = d.detail || 'Estacion llena';
      btn.style.background = '#ef4444';
    }
  } catch (e) {
    if (e.message !== 'rate_limit') btn.textContent = 'Error';
  }
}

function showSearchResults(stations) {
  searchActive = true;
  markers.clearLayers();
  const size = dotSize();
  stations.forEach(s => {
    const m = L.marker([s.latitude, s.longitude], { icon: createIcon(markerColor(s), size) });
    m.stationId = s.id;
    m.bindPopup(stationPopupHtml(s), { closeButton: false });
    markers.addLayer(m);
  });
  if (stations.length > 1) {
    const bounds = L.latLngBounds(stations.map(s => [s.latitude, s.longitude]));
    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
  }
}

function clearSearch() {
  searchActive = false;
  document.getElementById('search-results').className = 'result-box';
  document.getElementById('search-results').innerHTML = '';
  loadStations();
}

function appendClearBtn() {
  const box = document.getElementById('search-results');
  box.innerHTML += '<div style="text-align:center;margin-top:10px"><button onclick="clearSearch()" style="border:none;background:none;color:#3b82f6;font-family:inherit;font-size:12px;font-weight:600;cursor:pointer;padding:6px 12px">Ver todas las estaciones</button></div>';
}

/* ── Geolocation ── */
function showUserLocation(lat, lon) {
  if (userMarker) {
    userMarker.setLatLng([lat, lon]);
  } else {
    userMarker = L.marker([lat, lon], {
      icon: L.divIcon({
        className: '',
        html: `<div style="
          width:16px;height:16px;border-radius:50%;
          background:#3b82f6;
          border:3px solid #fff;
          box-shadow:0 0 0 3px rgba(59,130,246,.3), 0 2px 6px rgba(0,0,0,.3);
        "></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      }),
      zIndexOffset: 1000,
    }).addTo(map).bindPopup('<div style="font-family:Inter,system-ui,sans-serif;font-size:13px;font-weight:600;color:#3b82f6;padding:4px 10px;white-space:nowrap">&#128205; Estas aqui</div>', { closeButton: false, className: 'user-popup' });
  }
  userMarker.openPopup();
}

if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(
    pos => {
      map.setView([pos.coords.latitude, pos.coords.longitude], 15);
      showUserLocation(pos.coords.latitude, pos.coords.longitude);
    },
    () => {},
    { enableHighAccuracy: true, timeout: 5000 }
  );
}

/* ── Map events ── */
map.on('moveend', function () { if (!searchActive) loadStations(); });
window.addEventListener('load', () => { map.invalidateSize(); loadStations(); });
loadStations();
