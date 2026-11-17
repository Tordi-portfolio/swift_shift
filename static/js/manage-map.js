/* Staff map picker: click the map to fill latitude/longitude for a tracking update. */
(function () {
  var dataEl = document.getElementById("picker-data");
  var mapEl = document.getElementById("picker");
  var latInput = document.getElementById("id_latitude");
  var lngInput = document.getElementById("id_longitude");
  var countrySelect = document.getElementById("id_country");
  if (!dataEl || !mapEl || !latInput || !lngInput || typeof L === "undefined") {
    if (mapEl) { mapEl.textContent = "The map could not be loaded. You can still type coordinates below."; }
    return;
  }

  var data = JSON.parse(dataEl.textContent);
  var map = L.map("picker").setView([20, 0], 2);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  function dot(p, color, label) {
    if (!p) { return; }
    L.circleMarker([p.lat, p.lng], {
      radius: 8, color: color, weight: 3, fillColor: color, fillOpacity: 0.9
    }).bindTooltip(label + ": " + p.label).addTo(map);
  }
  dot(data.origin, "#16a34a", "Origin");
  dot(data.destination, "#dc2626", "Destination");

  var marker = null;
  function setMarker(lat, lng) {
    if (marker) { marker.setLatLng([lat, lng]); }
    else { marker = L.marker([lat, lng]).addTo(map); }
  }

  map.on("click", function (e) {
    var lat = e.latlng.lat.toFixed(5);
    var lng = e.latlng.lng.toFixed(5);
    latInput.value = lat;
    lngInput.value = lng;
    setMarker(lat, lng);
  });

  function fromInputs() {
    var lat = parseFloat(latInput.value);
    var lng = parseFloat(lngInput.value);
    if (!isNaN(lat) && !isNaN(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
      setMarker(lat, lng);
      return true;
    }
    return false;
  }
  latInput.addEventListener("change", fromInputs);
  lngInput.addEventListener("change", fromInputs);

  function goToCountry() {
    var c = data.countries[countrySelect && countrySelect.value];
    if (c && !fromInputs()) { map.setView(c, 5); }
  }
  if (countrySelect) { countrySelect.addEventListener("change", goToCountry); }

  // Initial view: existing coordinates > selected country > whole route > world.
  if (fromInputs()) {
    map.setView(marker.getLatLng(), 5);
  } else if (countrySelect && data.countries[countrySelect.value]) {
    map.setView(data.countries[countrySelect.value], 4);
  } else if (data.origin && data.destination) {
    map.fitBounds([[data.origin.lat, data.origin.lng], [data.destination.lat, data.destination.lng]], { padding: [30, 30] });
  }
})();
