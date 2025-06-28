const countrySelect = document.getElementById("countrySelect");
const searchInput = document.getElementById("searchInput");
const lawContainer = document.getElementById("lawContainer");

let laws = [];

async function loadLaws() {
  try {
    const res = await fetch("laws/latest.json");
    if (!res.ok) throw new Error("Cannot load laws/latest.json");
    laws = await res.json();
    renderLaws();
  } catch (err) {
    lawContainer.innerHTML = `<p style="color:red;">Error loading law data.</p>`;
  }
}

function normalizeCountry(name) {
  return name.toLowerCase().replace(/\s+/g, "_");
}

function renderLaws() {
  const query = searchInput.value.toLowerCase().trim();
  const selectedCountry = countrySelect.value;
  lawContainer.innerHTML = "";

  const filtered = laws.filter(law => {
    const lawCountry = normalizeCountry(law.country);
    const matchCountry = selectedCountry === "all" || lawCountry === selectedCountry;
    const matchText =
      law.title.toLowerCase().includes(query) ||
      law.summary.toLowerCase().includes(query) ||
      law.date.toLowerCase().includes(query);
    return matchCountry && matchText;
  });

  if (filtered.length === 0) {
    lawContainer.innerHTML = `<p>No matching laws found.</p>`;
    return;
  }

  filtered.forEach(law => {
    const div = document.createElement("div");
    div.className = "law-entry";
    div.innerHTML = `
      <h3>${law.date} – ${law.country}</h3>
      <p><strong>Law:</strong> ${law.title}</p>
      <p>${law.summary}</p>
      <p><a href="${law.link}" target="_blank">View full legislation</a></p>
    `;
    lawContainer.appendChild(div);
  });
}

countrySelect.addEventListener("change", renderLaws);
searchInput.addEventListener("input", renderLaws);

loadLaws();
