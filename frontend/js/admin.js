/**
 * Admin: create, edit, delete stations + map picker.
 */

let pickingLocation = false;
let pickMarker = null;

function startPickLocation() {
  pickingLocation = true;
  document.getElementById('pick-location-btn').textContent = '↻ Haz clic en el mapa...';
  document.getElementById('pick-location-btn').style.borderColor = '#22c55e';
  document.getElementById('pick-location-btn').style.color = '#22c55e';
  document.getElementById('map').style.cursor = 'crosshair';
}

map.on('click', function (e) {
  if (!pickingLocation) return;
  pickingLocation = false;
  const { lat, lng } = e.latlng;
  document.getElementById('create-lat').value = lat.toFixed(6);
  document.getElementById('create-lon').value = lng.toFixed(6);
  document.getElementById('pick-location-btn').textContent = '📍 Seleccionar en el mapa';
  document.getElementById('pick-location-btn').style.borderColor = '#ccc';
  document.getElementById('pick-location-btn').style.color = '#333';
  document.getElementById('pick-location-info').style.display = 'block';
  document.getElementById('pick-location-info').textContent = `✓ ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  document.getElementById('map').style.cursor = '';
  if (pickMarker) map.removeLayer(pickMarker);
  pickMarker = L.marker([lat, lng], {
    icon: L.divIcon({
      className: '',
      html: '<div style="width:20px;height:20px;border-radius:50%;background:#3b82f6;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3)"></div>',
      iconSize: [20, 20], iconAnchor: [10, 10],
    })
  }).addTo(map);
});

let editingStationId = null;

function resetManageForm() {
  editingStationId = null;
  document.getElementById('manage-title').textContent = 'Crear estacion';
  document.getElementById('manage-submit').textContent = 'Crear estacion';
  document.getElementById('create-name').value = '';
  document.getElementById('create-location').value = '';
  document.getElementById('create-lat').value = '';
  document.getElementById('create-lon').value = '';
  document.getElementById('create-slots').value = '20';
  document.getElementById('create-bikes').value = '10';
  document.getElementById('pick-location-info').style.display = 'none';
  document.getElementById('create-msg').className = 'msg';
  if (pickMarker) { map.removeLayer(pickMarker); pickMarker = null; }
}

async function editStation(id) {
  resetManageForm();
  editingStationId = id;
  document.getElementById('manage-title').textContent = 'Modificar estacion';
  document.getElementById('manage-submit').textContent = 'Guardar cambios';
  showPanel('manage');
  openSidebar();
  try {
    const resp = await fetch(`/api/stations/${id}`, { headers: API_HEADERS });
    if (!resp.ok) { showMsg('create-msg', 'Error cargando estacion', 'error'); return; }
    const s = await resp.json();
    document.getElementById('create-name').value = s.name;
    document.getElementById('create-location').value = s.location || '';
    document.getElementById('create-lat').value = s.latitude;
    document.getElementById('create-lon').value = s.longitude;
    document.getElementById('create-slots').value = s.total_slots;
    document.getElementById('create-bikes').value = s.available_bikes;
    document.getElementById('pick-location-info').style.display = 'block';
    document.getElementById('pick-location-info').textContent = `✓ ${s.latitude.toFixed(5)}, ${s.longitude.toFixed(5)}`;
    if (pickMarker) map.removeLayer(pickMarker);
    pickMarker = L.marker([s.latitude, s.longitude], {
      icon: L.divIcon({
        className: '',
        html: '<div style="width:20px;height:20px;border-radius:50%;background:#3b82f6;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3)"></div>',
        iconSize: [20, 20], iconAnchor: [10, 10],
      })
    }).addTo(map);
  } catch (e) { if (e.message !== 'rate_limit') showMsg('create-msg', 'Error de conexion', 'error'); }
}

async function submitStation() {
  const body = {
    name: document.getElementById('create-name').value,
    location: document.getElementById('create-location').value || undefined,
    latitude: parseFloat(document.getElementById('create-lat').value),
    longitude: parseFloat(document.getElementById('create-lon').value),
    total_slots: parseInt(document.getElementById('create-slots').value),
    available_bikes: parseInt(document.getElementById('create-bikes').value),
  };
  if (!body.name || isNaN(body.latitude) || isNaN(body.longitude)) {
    showMsg('create-msg', 'Completa el nombre y selecciona la posicion en el mapa.', 'error'); return;
  }
  try {
    const isEdit = editingStationId !== null;
    const url = isEdit ? `/api/stations/${editingStationId}` : '/api/stations';
    const method = isEdit ? 'PUT' : 'POST';
    const resp = await fetch(url, {
      method, headers: { ...API_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (resp.ok) {
      const s = await resp.json();
      showMsg('create-msg', isEdit ? `Estacion ${s.id} actualizada` : `Estacion creada con ID ${s.id}`, 'success');
      if (pickMarker) { map.removeLayer(pickMarker); pickMarker = null; }
      document.getElementById('pick-location-info').style.display = 'none';
      document.getElementById('create-lat').value = '';
      document.getElementById('create-lon').value = '';
      editingStationId = null;
      loadStations();
    } else {
      const d = await resp.json();
      showMsg('create-msg', d.detail || 'Error', 'error');
    }
  } catch (e) { if (e.message !== 'rate_limit') showMsg('create-msg', 'Error de conexion', 'error'); }
}

async function confirmDelete(id, btn) {
  btn.textContent = '¿Seguro?';
  btn.className = 'popup-action confirming';
  btn.onclick = function () { deleteStation(id, btn); };
}

async function deleteStation(id, btn) {
  btn.disabled = true;
  btn.textContent = '...';
  try {
    const resp = await fetch(`/api/stations/${id}`, { method: 'DELETE', headers: API_HEADERS });
    if (resp.status === 204) {
      btn.textContent = '✓';
      map.closePopup();
      setTimeout(loadStations, 400);
    } else {
      btn.textContent = 'Error';
    }
  } catch (e) { if (e.message !== 'rate_limit') btn.textContent = 'Error'; }
}
