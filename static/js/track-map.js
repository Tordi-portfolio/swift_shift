/* Draws the shipment route on the tracking page using Leaflet + OpenStreetMap. */
(function () {
  var dataEl = document.getElementById("map-data");
  var mapEl = document.getElementById("map");
  if (!dataEl || !mapEl || typeof L === "undefined") {
    if (mapEl) { mapEl.textContent = "The map could not be loaded. Please check your internet connection."; }
    return;
  }

  var data = JSON.parse(dataEl.textContent);
  var map = L.map("map", { scrollWheelZoom: false });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  // Build popup content with textContent so admin-entered text is never treated as HTML.
  function popup(title, lines) {
    var box = document.createElement("div");
    var strong = document.createElement("strong");
    strong.textContent = title;
    box.appendChild(strong);
    lines.forEach(function (line) {
      if (!line) { return; }
      box.appendChild(document.createElement("br"));
      box.appendChild(document.createTextNode(line));
    });
    return box;
  }

  function ll(p) { return [p.lat, p.lng]; }

  var bounds = [];
  var travelled = [];

  if (data.origin) { travelled.push(ll(data.origin)); }
  data.points.forEach(function (p) { travelled.push(ll(p)); });
  if (data.delivered && data.destination) { travelled.push(ll(data.destination)); }

  // Route already travelled (solid) and what is still left (dashed).
  if (travelled.length > 1) {
    L.polyline(travelled, { color: "#f97316", weight: 4, opacity: 0.9 }).addTo(map);
  }
  if (!data.delivered && data.destination && travelled.length) {
    var last = travelled[travelled.length - 1];
    L.polyline([last, ll(data.destination)], {
      color: "#64748b", weight: 3, dashArray: "8 10", opacity: 0.8
    }).addTo(map);
  }

  // Intermediate stops.
  data.points.forEach(function (p, i) {
    var isLast = i === data.points.length - 1;
    if (isLast && !data.delivered) { return; } // drawn as the "current" marker below
    L.circleMarker(ll(p), {
      radius: 5, color: "#1d4ed8", weight: 2, fillColor: "#fff", fillOpacity: 1
    }).bindPopup(popup(p.title, [p.location, p.time])).addTo(map);
    bounds.push(ll(p));
  });

  if (data.origin) {
    L.circleMarker(ll(data.origin), {
      radius: 9, color: "#15803d", weight: 3, fillColor: "#22c55e", fillOpacity: 1
    }).bindPopup(popup("Origin", [data.origin.label])).addTo(map);
    bounds.push(ll(data.origin));
  }

  if (data.destination) {
    L.circleMarker(ll(data.destination), {
      radius: 9, color: "#b91c1c", weight: 3, fillColor: "#ef4444", fillOpacity: 1
    }).bindPopup(popup(data.delivered ? "Delivered" : "Destination", [data.destination.label])).addTo(map);
    bounds.push(ll(data.destination));
  }

  // Current position: pulsing marker at the latest update.
  if (!data.delivered && data.points.length) {
    var cur = data.points[data.points.length - 1];
    var icon = L.divIcon({
      className: "pulse-wrap",
      html: '<span class="pulse"></span>',
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });
    L.marker(ll(cur), { icon: icon, zIndexOffset: 1000 })
      .bindPopup(popup("Current location: " + cur.title, [cur.location, cur.time]))
      .addTo(map);
    bounds.push(ll(cur));
  }

  if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 6 });
  } else if (bounds.length === 1) {
    map.setView(bounds[0], 4);
  } else {
    map.setView([20, 0], 2);
  }

  // Let people scroll the page past the map; enable wheel zoom only after a click.
  map.on("click", function () { map.scrollWheelZoom.enable(); });
  map.on("mouseout", function () { map.scrollWheelZoom.disable(); });
})();
