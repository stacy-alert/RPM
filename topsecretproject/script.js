(function () {
  "use strict";

  let allDogs = [];
  let activeBreed = "";

  function pct(confidence) {
    return Math.round(confidence * 100) + "%";
  }

  function primaryMatch(dog) {
    return dog.looks_like && dog.looks_like[0];
  }

  function matchLine(match) {
    if (!match) return "No target-breed match";
    if (match.confirmed) return "Confirmed: " + match.display;
    return "Looks like " + match.display;
  }

  function secondaryLine(dog) {
    const rest = (dog.looks_like || []).slice(1).filter(m => !m.confirmed);
    if (!rest.length) return "";
    return "Also possible: " + rest.map(m => m.display + " (" + pct(m.confidence) + ")").join(", ");
  }

  function populateSelect(select, values) {
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

  function setCardsState(html) {
    document.getElementById("cards").innerHTML = html;
  }

  function stateMessageHTML(text) {
    return (
      '<div class="state-message">' +
      '<svg viewBox="0 0 64 64" aria-hidden="true" class="state-icon">' +
      '<ellipse cx="32" cy="40" rx="15" ry="12"/><ellipse cx="14" cy="24" rx="6.5" ry="8"/>' +
      '<ellipse cx="29" cy="14" rx="6.5" ry="8.5"/><ellipse cx="46" cy="16" rx="6.5" ry="8.5"/>' +
      '<ellipse cx="54" cy="30" rx="6" ry="7.5"/></svg>' +
      "<p>" + text + "</p></div>"
    );
  }

  function render() {
    const minConfidence = parseFloat(document.getElementById("filter-confidence").value);
    const sex = document.getElementById("filter-sex").value;
    const age = document.getElementById("filter-age").value;
    const size = document.getElementById("filter-size").value;

    const filtered = allDogs.filter(dog => {
      const match = primaryMatch(dog);
      if (!match) return false;
      if (activeBreed && match.display !== activeBreed) return false;
      if (!match.confirmed && match.confidence < minConfidence) return false;
      if (sex && dog.sex !== sex) return false;
      if (age && dog.age !== age) return false;
      if (size && dog.size !== size) return false;
      return true;
    });

    document.getElementById("result-count").textContent =
      filtered.length + (filtered.length === 1 ? " dog matches" : " dogs match");

    if (!filtered.length) {
      setCardsState(stateMessageHTML("No dogs match these filters right now. Try widening your search."));
      return;
    }

    const container = document.getElementById("cards");
    const template = document.getElementById("card-template");
    container.innerHTML = "";

    filtered.forEach(dog => {
      const node = template.content.cloneNode(true);
      const match = primaryMatch(dog);

      const photoImg = node.querySelector(".photo-img");
      const photoPlaceholder = node.querySelector(".photo-placeholder");
      if (dog.photo_url) {
        photoImg.addEventListener("error", function onPhotoError() {
          photoImg.removeEventListener("error", onPhotoError);
          photoImg.hidden = true;
          photoPlaceholder.hidden = false;
        });
        photoImg.src = dog.photo_url;
        photoImg.alt = dog.name ? dog.name + "'s photo" : "";
        photoImg.hidden = false;
        photoPlaceholder.hidden = true;
      }

      node.querySelector(".card-breed-label").textContent = match.display;
      node.querySelector(".match-text").textContent = matchLine(match);

      const badge = node.querySelector(".confidence-badge");
      const fill = node.querySelector(".confidence-fill");
      if (match.confirmed) {
        badge.textContent = "Confirmed";
        badge.classList.add("confirmed");
        fill.style.width = "100%";
      } else {
        badge.textContent = pct(match.confidence);
        fill.style.width = pct(match.confidence);
      }

      const secondary = secondaryLine(dog);
      const secondaryEl = node.querySelector(".secondary");
      if (secondary) {
        secondaryEl.textContent = secondary;
      } else {
        secondaryEl.remove();
      }

      const tagsEl = node.querySelector(".tags");
      [dog.sex, dog.age, dog.size].filter(Boolean).forEach(value => {
        const tag = document.createElement("span");
        tag.className = "chip";
        tag.textContent = value;
        tagsEl.appendChild(tag);
      });

      node.querySelector(".first-seen").textContent = dog.first_seen
        ? "First seen " + dog.first_seen
        : "";

      const identity = node.querySelector(".identity");
      if (dog.name) {
        identity.textContent = dog.name + (dog.shelter_seq_id ? " · CAC #" + dog.shelter_seq_id : "");
      } else {
        identity.remove();
      }

      const link = node.querySelector(".cac-link");
      if (dog.listing_url) {
        link.href = dog.listing_url;
      } else {
        link.remove();
      }

      container.appendChild(node);
    });
  }

  function createBreedPill(value, label) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "breed-pill";
    btn.textContent = label;
    btn.dataset.breed = value;
    btn.setAttribute("aria-pressed", value === activeBreed ? "true" : "false");
    btn.addEventListener("click", () => {
      activeBreed = value;
      document.querySelectorAll(".breed-pill").forEach(p => {
        const isActive = p === btn;
        p.classList.toggle("active", isActive);
        p.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
      render();
    });
    return btn;
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

    const pillsContainer = document.getElementById("filter-breed-pills");
    pillsContainer.innerHTML = "";
    const allPill = createBreedPill("", "All breeds");
    allPill.classList.add("active");
    pillsContainer.appendChild(allPill);
    Array.from(breeds).sort().forEach(breed => {
      pillsContainer.appendChild(createBreedPill(breed, breed));
    });

    populateSelect(document.getElementById("filter-sex"), Array.from(sexes).sort());
    populateSelect(document.getElementById("filter-age"), Array.from(ages).sort());
    populateSelect(document.getElementById("filter-size"), Array.from(sizes).sort());
  }

  function init() {
    fetch("dogs.json", { cache: "no-store" })
      .then(r => r.json())
      .then(data => {
        allDogs = data.dogs || [];
        const when = [];
        if (data.list_fetched_at) when.push("Shelter list taken " + new Date(data.list_fetched_at).toLocaleString());
        if (data.last_updated) when.push("updated " + new Date(data.last_updated).toLocaleString());
        document.getElementById("last-updated").textContent = when.join(" · ");
        const dataAsOf = document.getElementById("data-as-of");
        if (data.data_as_of) {
          dataAsOf.textContent = "Data as of " + data.data_as_of + " — not live; see note below.";
          dataAsOf.hidden = false;
        }
        initFilters();
        render();
      })
      .catch(() => {
        document.getElementById("result-count").textContent = "";
        setCardsState(stateMessageHTML("Could not load dog data right now. Try reloading the page."));
      });

    document.getElementById("filters").addEventListener("change", render);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
