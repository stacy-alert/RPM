// Loaded by the owner's "Send dogs" bookmark while they are viewing the
// shelter's adoptable-dogs page in their own browser. Reads the dog
// cards already on the page and posts them to upload.php. The token
// comes from the bookmark (window.__rpmDogToken), never from this file.
(function () {
  var UPLOAD_URL = "https://rpmhabitatconservation.org/topsecretproject/upload.php";
  var SIZE = { s: "Small", m: "Medium", l: "Large", xl: "Extra Large" };
  function cap(x) { return x ? x.charAt(0).toUpperCase() + x.slice(1).toLowerCase() : null; }
  function low(x) { return (x || "").toLowerCase(); }

  function show(text) {
    var old = document.getElementById("rpm-dog-box");
    if (old) old.remove();
    var box = document.createElement("div");
    box.id = "rpm-dog-box";
    box.style.cssText = "position:fixed;z-index:2147483647;top:10px;left:10px;right:10px;max-height:80vh;overflow:auto;background:#fff;color:#000;border:3px solid #000;padding:14px;font:14px/1.4 monospace;white-space:pre-wrap;word-break:break-all";
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.readOnly = true;
    ta.style.cssText = "width:100%;height:50vh;font:12px monospace";
    var btn = document.createElement("button");
    btn.textContent = "Close";
    btn.style.cssText = "font-size:16px;padding:6px 14px;margin-top:8px";
    btn.onclick = function () { box.remove(); };
    box.appendChild(document.createTextNode("Send dogs: found no dog cards. Copy everything in this box and send it to Claude:\n"));
    box.appendChild(ta);
    box.appendChild(btn);
    document.body.appendChild(box);
    ta.focus();
    ta.select();
  }

  var seen = {};
  var cards = [];
  var nodes = document.querySelectorAll(".pmp-search-result-container, [data-animal-name], [data-seqid]");
  for (var i = 0; i < nodes.length; i++) {
    var e = nodes[i], d = e.dataset;
    var id = d.id || d.animalId || d.animalid || d.seqid;
    if (!id || seen[id]) continue;
    if (d.species && low(d.species).indexOf("dog") < 0) continue;
    if (d.status && low(d.status) !== "available") continue;
    seen[id] = 1;
    var a = e.querySelector(".pmp-search-result-name-link") || e.querySelector("a[href*='/pmp/']") || e.querySelector("a[href]");
    var photos = [];
    ["photourl", "photourl1", "photourl2", "photourl3", "photourl4"].forEach(function (k) {
      if (d[k] && photos.indexOf(d[k]) < 0) photos.push(d[k]);
    });
    if (!photos.length) {
      var imgs = e.querySelectorAll("img");
      for (var j = 0; j < imgs.length; j++) {
        var src = imgs[j].currentSrc || imgs[j].src || imgs[j].getAttribute("data-src") || "";
        if (src.indexOf("animalsfirstprod.s3.amazonaws.com") > -1 && photos.indexOf(src) < 0) photos.push(src);
      }
    }
    cards.push({
      cac_id: String(id),
      shelter_seq_id: d.seqid || null,
      name: d.animalName || d.name || null,
      listing_url: a ? a.href : null,
      photo_urls: photos,
      sex: cap(d.gender || d.sex),
      age: cap(d.afage || d.age),
      size: SIZE[low(d.afsize)] || d.afsize || null,
      date_listed: d.intakedate || null
    });
  }

  if (!cards.length) {
    var diag = ["url: " + location.href, "nodes matched: " + nodes.length];
    ["[class*='pmp']", ".pmp-search-result-container", "[data-animal-name]", "[data-seqid]", "[data-species]", "iframe", "img[src*='animalsfirst']"].forEach(function (sel) {
      diag.push(sel + ": " + document.querySelectorAll(sel).length);
    });
    var ifr = document.querySelectorAll("iframe");
    for (var k = 0; k < ifr.length && k < 5; k++) diag.push("iframe src: " + ifr[k].src);
    var cls = {};
    var pm = document.querySelectorAll("[class*='pmp']");
    for (var m = 0; m < pm.length; m++) String(pm[m].className).split(/\s+/).forEach(function (c) { if (c.indexOf("pmp") > -1) cls[c] = (cls[c] || 0) + 1; });
    diag.push("pmp classes: " + JSON.stringify(cls).slice(0, 1500));
    var first = nodes[0] || document.querySelector("img[src*='animalsfirst']");
    if (first) {
      var el = first.tagName === "IMG" ? (first.closest("[class*='pmp']") || first.parentElement.parentElement) : first;
      diag.push("sample element: " + el.outerHTML.slice(0, 2500));
    }
    show(diag.join("\n"));
    return;
  }

  var countEl = document.querySelector(".pmp-search-profile-count");
  var mt = countEl && countEl.textContent.match(/(\d+)/);
  var f = document.createElement("form");
  f.method = "POST";
  f.action = UPLOAD_URL;
  f.target = "_blank";
  function add(n, v) { var inp = document.createElement("input"); inp.type = "hidden"; inp.name = n; inp.value = v; f.appendChild(inp); }
  add("token", window.__rpmDogToken || "");
  add("data", JSON.stringify({ claimed_total: mt ? parseInt(mt[1], 10) : null, dogs: cards }));
  document.body.appendChild(f);
  f.submit();
  f.remove();
})();
