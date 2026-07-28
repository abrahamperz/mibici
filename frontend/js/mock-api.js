/**
 * Client-side mock of the backend API for the static Vercel demo.
 * Intercepts window.fetch for /api/ paths and serves data from STATIONS_SEED
 * held in memory. Reservations mutate in-memory state (reset on reload).
 * All other requests (map tiles, Nominatim) pass through untouched.
 */
(function () {
  const stations = new Map();
  (window.STATIONS_SEED || []).forEach(s => stations.set(s.id, { ...s }));
  let nextId = Math.max(0, ...stations.keys()) + 1;
  let reservationId = 1;
  const now = () => new Date().toISOString();

  function withDerived(s) {
    return {
      id: s.id, name: s.name, location: s.location || null,
      longitude: s.longitude, latitude: s.latitude,
      total_slots: s.total_slots, available_bikes: s.available_bikes,
      is_active: s.is_active, created_at: s.created_at || now(),
      updated_at: s.updated_at || now(),
    };
  }

  function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371000, toRad = d => (d * Math.PI) / 180;
    const dLat = toRad(lat2 - lat1), dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  const json = (body, status = 200) =>
    new Response(JSON.stringify(body), {
      status, headers: { 'Content-Type': 'application/json' },
    });

  async function handle(method, path, body) {
    const [pathname, qs] = path.split('?');
    const q = new URLSearchParams(qs || '');
    const seg = pathname.split('/').filter(Boolean); // ['stations', ...] ('/api' already stripped)

    // /stations/nearest
    if (method === 'GET' && seg[1] === 'nearest') {
      const lon = parseFloat(q.get('lon')), lat = parseFloat(q.get('lat'));
      const k = Math.min(parseInt(q.get('k') || '5', 10), 10000);
      const radius = q.get('radius_m') ? parseFloat(q.get('radius_m')) : null;
      let list = [...stations.values()].map(s => ({
        ...withDerived(s),
        distance_m: haversine(lat, lon, s.latitude, s.longitude),
      }));
      if (radius != null) list = list.filter(s => s.distance_m <= radius);
      list.sort((a, b) => a.distance_m - b.distance_m);
      return json(list.slice(0, k));
    }

    // /stations/{id}/reserve  and  /stations/{id}/return
    if (method === 'POST' && seg[0] === 'stations' && seg[2]) {
      const id = parseInt(seg[1], 10);
      const s = stations.get(id);
      if (!s) return json({ detail: 'Station not found' }, 404);
      if (seg[2] === 'reserve') {
        if (s.available_bikes <= 0) return json({ detail: 'No bikes available' }, 409);
        s.available_bikes -= 1; s.updated_at = now();
        return json({ id: reservationId++, station_id: id, reserved_at: now(), returned_at: null, status: 'active' }, 201);
      }
      if (seg[2] === 'return') {
        if (s.available_bikes >= s.total_slots) return json({ detail: 'Station is full' }, 409);
        s.available_bikes += 1; s.updated_at = now();
        return json({ id: reservationId++, station_id: id, reserved_at: now(), returned_at: now(), status: 'returned' });
      }
    }

    // /stations  (create)
    if (method === 'POST' && seg[0] === 'stations' && !seg[1]) {
      if (!body.name) return json({ detail: 'name required' }, 422);
      const s = {
        id: nextId++, name: body.name, location: body.location || '',
        longitude: body.longitude, latitude: body.latitude,
        total_slots: body.total_slots, available_bikes: body.available_bikes ?? 0,
        is_active: body.is_active ?? true, created_at: now(), updated_at: now(),
      };
      stations.set(s.id, s);
      return json(withDerived(s), 201);
    }

    if (seg[0] === 'stations' && seg[1] && !seg[2]) {
      const id = parseInt(seg[1], 10);
      const s = stations.get(id);
      // GET /stations/{id}
      if (method === 'GET') {
        if (!s) return json({ detail: 'Station not found' }, 404);
        return json(withDerived(s));
      }
      // PUT /stations/{id}
      if (method === 'PUT') {
        if (!s) return json({ detail: 'Station not found' }, 404);
        ['name', 'location', 'longitude', 'latitude', 'total_slots', 'available_bikes', 'is_active']
          .forEach(f => { if (body[f] !== undefined && body[f] !== null) s[f] = body[f]; });
        s.updated_at = now();
        return json(withDerived(s));
      }
      // DELETE /stations/{id}
      if (method === 'DELETE') {
        if (!s) return json({ detail: 'Station not found' }, 404);
        stations.delete(id);
        return new Response(null, { status: 204 });
      }
    }

    return json({ detail: 'Not found' }, 404);
  }

  const realFetch = window.fetch.bind(window);
  window.fetch = function (input, init = {}) {
    const url = typeof input === 'string' ? input : input.url;
    if (url && url.startsWith('/api/')) {
      const method = (init.method || (typeof input !== 'string' && input.method) || 'GET').toUpperCase();
      let body = {};
      try { body = init.body ? JSON.parse(init.body) : {}; } catch { body = {}; }
      return handle(method, url.slice(4), body); // strip '/api'
    }
    return realFetch(input, init);
  };
})();
