const API_BASE_URL =
  window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : window.location.origin;

const form = document.querySelector("#ride-form");
const pickupInput = document.querySelector("#pickup");
const dropInput = document.querySelector("#drop");
const bookingTypeInput = document.querySelector("#booking-type");
const tripModeInput = document.querySelector("#trip-mode");
const hourField = document.querySelector("#hour-field");
const tripHourInput = document.querySelector("#trip-hour");
const button = document.querySelector("#analyze-button");
const statusBox = document.querySelector("#status");
const results = document.querySelector("#results");
const providerList = document.querySelector("#provider-list");
const resolvedTrip = document.querySelector("#resolved-trip");
const analyticsStatus = document.querySelector("#analytics-status");
const clearHistoryButton = document.querySelector("#clear-history-button");
const analyticsTotalRecords = document.querySelector("#analytics-total-records");
const providerChart = document.querySelector("#provider-chart");
const hourChart = document.querySelector("#hour-chart");
const recentTrips = document.querySelector("#recent-trips");
const bestValueProvider = document.querySelector("#best-value-provider");
const fastestProvider = document.querySelector("#fastest-provider");
const scenarioLabel = document.querySelector("#scenario-label");
const distanceBand = document.querySelector("#distance-band");
const recommendationSummary = document.querySelector("#recommendation-summary");

const summaryNodes = {
  cheapestProvider: document.querySelector("#cheapest-provider"),
  cheapestPrice: document.querySelector("#cheapest-price"),
  distance: document.querySelector("#distance"),
  duration: document.querySelector("#duration"),
  traffic: document.querySelector("#traffic"),
};

const fallbackPlaces = {
  delhi: [28.6139, 77.209],
  "new delhi": [28.6139, 77.209],
  noida: [28.5355, 77.391],
  gurgaon: [28.4595, 77.0266],
  gurugram: [28.4595, 77.0266],
  faridabad: [28.4089, 77.3178],
  ghaziabad: [28.6692, 77.4538],
  mumbai: [19.076, 72.8777],
  pune: [18.5204, 73.8567],
  bangalore: [12.9716, 77.5946],
  bengaluru: [12.9716, 77.5946],
  hyderabad: [17.385, 78.4867],
  chennai: [13.0827, 80.2707],
  kolkata: [22.5726, 88.3639],
};

function initializeTripHours() {
  for (let hour = 0; hour < 24; hour += 1) {
    const option = document.createElement("option");
    option.value = String(hour);
    option.textContent = `${String(hour).padStart(2, "0")}:00`;

    if (hour === new Date().getHours()) {
      option.selected = true;
    }

    tripHourInput.appendChild(option);
  }
}

function setStatus(message, isError = false) {
  if (!statusBox) return;
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
}

function setNodeText(node, value) {
  if (node) {
    node.textContent = value;
  }
}

function toggleScheduledHourField() {
  const shouldShow = bookingTypeInput.value === "Schedule for Later";
  hourField.classList.toggle("hidden", !shouldShow);
}

function formatCurrency(value) {
  return `Rs. ${value}`;
}

function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function parseCoordinates(value) {
  const parts = value.split(",").map((part) => part.trim());
  if (parts.length !== 2) return null;

  const lat = Number(parts[0]);
  const lon = Number(parts[1]);

  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;

  return { lat, lon, label: value };
}

async function geocodePlace(place) {
  const normalized = place.trim().toLowerCase().replace(/\s+/g, " ");
  if (!normalized) return null;

  const typedCoordinates = parseCoordinates(normalized);
  if (typedCoordinates) return typedCoordinates;

  if (fallbackPlaces[normalized]) {
    const [lat, lon] = fallbackPlaces[normalized];
    return { lat, lon, label: place };
  }

  const url = new URL("https://nominatim.openstreetmap.org/search");
  url.searchParams.set("q", place);
  url.searchParams.set("format", "json");
  url.searchParams.set("limit", "1");

  const response = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Location search failed for "${place}".`);
  }

  const data = await response.json();
  if (!data.length) return null;

  return {
    lat: Number(data[0].lat),
    lon: Number(data[0].lon),
    label: data[0].display_name,
  };
}

async function getRidePrice(payload) {
  const response = await fetch(`${API_BASE_URL}/get-price`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(`Backend returned ${response.status}. ${details}`);
  }

  return response.json();
}

function createProviderCard(item, cheapestProvider) {
  const card = document.createElement("article");
  const isBest = item.provider === cheapestProvider;

  card.className = `provider-card${isBest ? " best" : ""}`;
  card.innerHTML = `
    <div class="provider-main">
      <div class="provider-title-row">
        <strong>${item.provider}</strong>
        ${isBest ? '<span class="best-badge">Best Fare</span>' : ""}
      </div>
      <p class="provider-subtitle">${item.vehicle_type}</p>
      <div class="provider-meta">
        <span>ETA ${item.eta_min} min</span>
        <span>Value Score ${item.value_score}/10</span>
      </div>
    </div>
    <div class="provider-price">
      <strong>${formatCurrency(item.price)}</strong>
      <span>Estimated fare</span>
    </div>
  `;

  return card;
}

function buildChartRows(items, valueKey, labelBuilder, container, formatter) {
  container.innerHTML = "";

  if (!items.length) {
    container.innerHTML = '<p class="analytics-status">No records yet. Run a few trips to build analytics.</p>';
    return;
  }

  const maxValue = Math.max(...items.map((item) => Number(item[valueKey]) || 0), 1);

  items.forEach((item) => {
    const value = Number(item[valueKey]) || 0;
    const width = Math.max(12, (value / maxValue) * 100);
    const row = document.createElement("article");
    row.className = "chart-row";
    row.innerHTML = `
      <header>
        <span>${labelBuilder(item)}</span>
        <strong>${formatter(value, item)}</strong>
      </header>
      <div class="chart-track">
        <span class="chart-bar" style="width: ${width}%"></span>
      </div>
    `;
    container.appendChild(row);
  });
}

function renderRecentTrips(items) {
  recentTrips.innerHTML = "";

  if (!items.length) {
    recentTrips.innerHTML =
      '<p class="analytics-status">Trip history will appear here after a few comparisons.</p>';
    return;
  }

  items.forEach((trip) => {
    const card = document.createElement("article");
    card.className = "recent-trip";
    card.innerHTML = `
      <div>
        <strong>${trip.provider}</strong>
        <div class="recent-trip-meta">${trip.trip_mode} | ${trip.booking_type}</div>
      </div>
      <div>
        <strong>${formatCurrency(trip.price)}</strong>
        <div class="recent-trip-meta">${trip.inferred_traffic} traffic</div>
      </div>
      <div class="recent-trip-time">
        ${formatTimestamp(trip.timestamp)}<br />
        ${trip.distance_km} km | ${trip.duration_min} min
      </div>
    `;
    recentTrips.appendChild(card);
  });
}

function renderAnalytics(analytics) {
  setNodeText(analyticsStatus, "Analytics ready");
  setNodeText(analyticsTotalRecords, `${analytics.total_records} records`);

  buildChartRows(
    analytics.provider_stats,
    "avg_price",
    (item) => `${item.provider} (${item.trip_count})`,
    providerChart,
    (value) => formatCurrency(Math.round(value))
  );

  buildChartRows(
    analytics.hourly_stats,
    "avg_price",
    (item) => `${String(item.hour).padStart(2, "0")}:00`,
    hourChart,
    (value, item) => `${formatCurrency(Math.round(value))} | ${item.trip_count} trips`
  );

  renderRecentTrips(analytics.recent_trips);
}

function resetAnalyticsView() {
  setNodeText(analyticsStatus, "Analytics cleared.");
  setNodeText(analyticsTotalRecords, "0 records");
  if (providerChart) {
    providerChart.innerHTML =
      '<p class="analytics-status">No records yet. Run a few trips to build analytics.</p>';
  }
  if (hourChart) {
    hourChart.innerHTML =
      '<p class="analytics-status">No records yet. Run a few trips to build analytics.</p>';
  }
  if (recentTrips) {
    recentTrips.innerHTML =
      '<p class="analytics-status">Trip history will appear here after a few comparisons.</p>';
  }
}

async function loadAnalytics() {
  setNodeText(analyticsStatus, "Loading project analytics...");

  try {
    const response = await fetch(`${API_BASE_URL}/history-summary`);

    if (!response.ok) {
      throw new Error("Analytics endpoint unavailable.");
    }

    const payload = await response.json();
    renderAnalytics(payload.analytics);
  } catch (error) {
    setNodeText(analyticsStatus, "Analytics unavailable until the backend is running.");
  }
}

async function clearHistory() {
  const confirmed = window.confirm(
    "Clear all saved trip history and reset analytics?"
  );
  if (!confirmed) {
    return;
  }

  if (clearHistoryButton) {
    clearHistoryButton.disabled = true;
  }
  setNodeText(analyticsStatus, "Clearing saved history...");

  try {
    const response = await fetch(`${API_BASE_URL}/history`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error("Could not clear history.");
    }

    const payload = await response.json();
    resetAnalyticsView();
    setStatus(`History cleared. Deleted ${payload.deleted_rows} saved rows.`);
  } catch (error) {
    setNodeText(analyticsStatus, "Could not clear analytics history.");
    setStatus("Failed to clear history.", true);
  } finally {
    if (clearHistoryButton) {
      clearHistoryButton.disabled = false;
    }
  }
}

function updateRecommendation(result) {
  setNodeText(bestValueProvider, result.insights.best_value_provider);
  setNodeText(fastestProvider, result.insights.fastest_eta_provider);
  setNodeText(scenarioLabel, result.insights.scenario);
  setNodeText(distanceBand, result.insights.distance_band);
  setNodeText(recommendationSummary, result.insights.summary);
}

function renderResult(result, pickup, drop) {
  const route = result.route_summary;
  const cheapest = result.cheapest;
  const context = result.trip_context;

  setNodeText(summaryNodes.cheapestProvider, cheapest.provider);
  setNodeText(summaryNodes.cheapestPrice, formatCurrency(cheapest.price));
  setNodeText(summaryNodes.distance, `${route.distance_km} km`);
  setNodeText(summaryNodes.duration, `${route.duration_min} min`);
  setNodeText(summaryNodes.traffic, `Traffic: ${context.inferred_traffic}`);
  setNodeText(resolvedTrip, `${pickup.label} to ${drop.label}`);

  providerList.innerHTML = "";

  result.provider_prices.forEach((item) => {
    providerList.appendChild(createProviderCard(item, cheapest.provider));
  });

  updateRecommendation(result);
  results.classList.remove("hidden");
}

async function handleTripSubmit(event) {
  event.preventDefault();
  button.disabled = true;
  results.classList.add("hidden");
  setStatus("Finding pickup and drop locations...");

  try {
    const pickup = await geocodePlace(pickupInput.value);
    const drop = await geocodePlace(dropInput.value);

    if (!pickup) {
      throw new Error("Pickup location not found. Try a more complete place name.");
    }

    if (!drop) {
      throw new Error("Drop location not found. Try a more complete place name.");
    }

    setStatus("Comparing ride providers...");

    const payload = {
      pickup_lat: pickup.lat,
      pickup_lon: pickup.lon,
      drop_lat: drop.lat,
      drop_lon: drop.lon,
      trip_mode: tripModeInput.value,
      booking_type: bookingTypeInput.value,
      trip_hour:
        bookingTypeInput.value === "Schedule for Later"
          ? Number(tripHourInput.value)
          : null,
    };

    const result = await getRidePrice(payload);
    renderResult(result, pickup, drop);
    setStatus("Comparison ready.");
    await loadAnalytics();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
}

initializeTripHours();
toggleScheduledHourField();
loadAnalytics();

bookingTypeInput.addEventListener("change", toggleScheduledHourField);
form.addEventListener("submit", handleTripSubmit);
if (clearHistoryButton) {
  clearHistoryButton.addEventListener("click", clearHistory);
}
