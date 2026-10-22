(function () {
  "use strict";

  let allDogs = [];

  function pct(confidence) {
    return Math.round(confidence * 100) + "%";
  }

  function primaryMatch(dog) {
    return dog.looks_like && dog.looks_like[0];
  }

  function matchLine(match) {
    if (!match) return "No target-breed match";
    if (match.confirmed) return "Confirmed: " + match.display;
    return "Looks like: " + match.display + " (" + pct(match.confidence) + ")";
  }

  function secondaryLine(dog) {
    const rest = (dog.looks_like || []).slice(1).filter(m => !m.confirmed);
    if (!rest.length) return "";
    return "Also possible: " + rest.map(m => m.display + " (" + pct(m.confidence) + ")").join(", ");
  }

  function populateSelect(select, values, placeholder) {
    const existing = new Set(Array.from(select.options).map(o => o.value));
    values.forEach(v => {
      if (v && !existing.has(v)) {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        select.appendChild(opt);
      }
    });
  }

  function render() {
    const breed = document.getElementById("filter-breed").value;
    const minConfidence = parseFloat(document.getElementById("filter-confidence").value);
    const sex = document.getElementById("filter-sex").value;
    const age = document.getElementById("filter-age").value;
    const size = document.getElementById("filter-size").value;

    const filtered = allDogs.filter(dog => {
      const match = primaryMatch(dog);
      if (!match) return false;
      if (breed && match.display !== breed) return false;
      if (!match.confirmed && match.confidence < minConfidence) return false;
      if (sex && dog.sex !== sex) return false;
      if (age && dog.age !== age) return false;
      if (size && dog.size !== size) return false;
      return true;
    });

    document.getElementById("result-count").textContent =
      filtered.length + (filtered.length === 1 ? " dog" : " dogs");

    const container = document.getElementById("cards");
    const template = document.getElementById("card-template");
    container.innerHTML = "";

    filtered.forEach(dog => {
      const node = template.content.cloneNode(true);
      const match = primaryMatch(dog);
      node.querySelector(".looks-like").textContent = matchLine(match);
      const secondary = secondaryLine(dog);
      const attrsParts = [dog.sex, dog.age, dog.size].filter(Boolean);
      node.querySelector(".attrs").textContent = attrsParts.join(" · ") +
        (secondary ? " — " + secondary : "");
      node.querySelector(".first-seen").textContent = dog.first_seen
        ? "First seen: " + dog.first_seen
        : "";
      node.querySelector(".ask-button").addEventListener("click", () => openAskDialog(dog.reference_code));
      container.appendChild(node);
    });
  }

  function openAskDialog(referenceCode) {
    document.getElementById("ask-ref-code").textContent = referenceCode;
    document.getElementById("ask-ref-input").value = referenceCode;
    const status = document.getElementById("ask-status");
    status.hidden = true;
    status.textContent = "";
    document.getElementById("ask-dialog").showModal();
  }

  function initFilters() {
    const breeds = new Set();
    const sexes = new Set();
    const ages = new Set();
    const sizes = new Set();
    allDogs.forEach(dog => {
      const match = primaryMatch(dog);
      if (match) breeds.add(match.display);
      if (dog.sex) sexes.add(dog.sex);
      if (dog.age) ages.add(dog.age);
      if (dog.size) sizes.add(dog.size);
    });
    populateSelect(document.getElementById("filter-breed"), Array.from(breeds).sort());
    populateSelect(document.getElementById("filter-sex"), Array.from(sexes).sort());
    populateSelect(document.getElementById("filter-age"), Array.from(ages).sort());
    populateSelect(document.getElementById("filter-size"), Array.from(sizes).sort());
  }

  function init() {
    fetch("dogs.json", { cache: "no-store" })
      .then(r => r.json())
      .then(data => {
        allDogs = data.dogs || [];
        document.getElementById("last-updated").textContent =
          data.last_updated ? "Last updated: " + new Date(data.last_updated).toLocaleString() : "";
        initFilters();
        render();
      })
      .catch(() => {
        document.getElementById("result-count").textContent =
          "Could not load dog data. Try reloading.";
      });

    document.getElementById("filters").addEventListener("change", render);
    document.getElementById("ask-cancel").addEventListener("click", () => {
      document.getElementById("ask-dialog").close();
    });

    document.getElementById("ask-form").addEventListener("submit", function (event) {
      event.preventDefault();
      const form = event.target;
      const status = document.getElementById("ask-status");
      const submitButton = form.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      status.hidden = false;
      status.textContent = "Sending...";

      fetch("ask-about-dog.php", {
        method: "POST",
        body: new FormData(form),
      })
        .then(r => r.json())
        .then(result => {
          if (result.ok) {
            status.textContent = "Sent. We'll follow up by email.";
            setTimeout(() => document.getElementById("ask-dialog").close(), 1500);
          } else {
            status.textContent = result.error || "Something went wrong. Try again.";
          }
        })
        .catch(() => {
          status.textContent = "Network error. Try again.";
        })
        .finally(() => {
          submitButton.disabled = false;
        });
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
