(function () {
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var SETUP_MESSAGE = "The contact form is being set up. Check back soon.";

  function digitsOnly(value) {
    var i;
    for (i = 0; i < value.length; i += 1) {
      var code = value.charCodeAt(i);
      if (code < 48 || code > 57) {
        return false;
      }
    }
    return value.length > 0;
  }

  function parseIso(iso) {
    if (typeof iso !== "string" || iso.length !== 10) {
      return null;
    }
    if (iso.charAt(4) !== "-" || iso.charAt(7) !== "-") {
      return null;
    }
    var year = iso.slice(0, 4);
    var monthText = iso.slice(5, 7);
    var dayText = iso.slice(8, 10);
    if (!digitsOnly(year) || !digitsOnly(monthText) || !digitsOnly(dayText)) {
      return null;
    }
    var month = Number(monthText);
    var day = Number(dayText);
    var yearNumber = Number(year);
    if (month < 1 || month > 12 || day < 1 || day > 31) {
      return null;
    }
    var probe = new Date(Date.UTC(yearNumber, month - 1, day));
    if (probe.getUTCFullYear() !== yearNumber || probe.getUTCMonth() !== month - 1 || probe.getUTCDate() !== day) {
      return null;
    }
    return { year: year, month: month, day: day };
  }

  function prettyDate(iso) {
    var parts = parseIso(iso);
    if (!parts) {
      return iso || "";
    }
    return MONTHS[parts.month - 1] + " " + parts.day + ", " + parts.year;
  }

  function availableFromIso(status) {
    var prefix = "Available from ";
    if (typeof status !== "string" || status.indexOf(prefix) !== 0) {
      return null;
    }
    return parseIso(status.slice(prefix.length));
  }

  function statusView(status) {
    if (status === "Available") {
      return { label: "Available", className: "badge badge-available" };
    }
    if (availableFromIso(status)) {
      return {
        label: "Available from " + prettyDate(status.slice("Available from ".length)),
        className: "badge badge-soon"
      };
    }
    if (status === "Occupied") {
      return { label: "Occupied", className: "badge badge-occupied" };
    }
    return { label: "Contact us for availability", className: "badge badge-contact" };
  }

  function isListedAvailable(status) {
    if (status === "Available") {
      return true;
    }
    return !!availableFromIso(status);
  }

  function applyFilters() {
    var cards = document.querySelectorAll("[data-unit-card]");
    if (!cards.length) {
      return;
    }
    var onlyAvailable = document.getElementById("available-only");
    var propertySelect = document.getElementById("property-filter");
    var availableOn = !!(onlyAvailable && onlyAvailable.checked);
    var property = propertySelect ? propertySelect.value : "";
    var shown = 0;
    Array.prototype.forEach.call(cards, function (card) {
      var status = card.getAttribute("data-status") || "";
      var cardProperty = card.getAttribute("data-property") || "";
      var propertyOk = !property || cardProperty === property;
      var availableOk = !availableOn || isListedAvailable(status);
      var visible = propertyOk && availableOk;
      card.hidden = !visible;
      if (visible) {
        shown += 1;
      }
    });
    var summary = document.getElementById("filter-summary");
    if (summary) {
      summary.textContent = "Showing " + shown + (shown === 1 ? " unit." : " units.");
    }
    var empty = document.getElementById("filter-empty");
    if (empty) {
      empty.hidden = shown !== 0;
    }
  }

  function writeFilterParams() {
    var params = new URLSearchParams(window.location.search);
    var onlyAvailable = document.getElementById("available-only");
    var propertySelect = document.getElementById("property-filter");
    if (onlyAvailable) {
      if (onlyAvailable.checked) {
        params.set("available", "1");
      } else {
        params.delete("available");
      }
    }
    if (propertySelect) {
      if (propertySelect.value) {
        params.set("property", propertySelect.value);
      } else {
        params.delete("property");
      }
    }
    var query = params.toString();
    var next = query ? window.location.pathname + "?" + query : window.location.pathname;
    window.history.replaceState(null, "", next);
  }

  function initFilters() {
    var onlyAvailable = document.getElementById("available-only");
    var propertySelect = document.getElementById("property-filter");
    if (!onlyAvailable && !propertySelect) {
      return;
    }
    var params = new URLSearchParams(window.location.search);
    if (onlyAvailable) {
      onlyAvailable.checked = params.get("available") === "1";
      onlyAvailable.addEventListener("change", function () {
        writeFilterParams();
        applyFilters();
      });
    }
    if (propertySelect) {
      var wanted = params.get("property");
      if (wanted) {
        Array.prototype.forEach.call(propertySelect.options, function (option) {
          if (option.value === wanted) {
            propertySelect.value = wanted;
          }
        });
      }
      propertySelect.addEventListener("change", function () {
        writeFilterParams();
        applyFilters();
      });
    }
    applyFilters();
  }

  function initGallery() {
    var mainPhoto = document.getElementById("unit-main-photo");
    var thumbs = document.querySelector(".photo-thumbs");
    if (!mainPhoto || !thumbs) {
      return;
    }
    thumbs.addEventListener("click", function (event) {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
        return;
      }
      var target = event.target;
      var link = target.closest ? target.closest("a") : null;
      if (!link || !thumbs.contains(link)) {
        return;
      }
      var thumb = link.querySelector("img");
      if (!thumb) {
        return;
      }
      event.preventDefault();
      mainPhoto.src = link.href;
      var alt = thumb.getAttribute("alt");
      if (alt) {
        mainPhoto.alt = alt;
      }
      Array.prototype.forEach.call(thumbs.querySelectorAll("a[aria-current='true']"), function (item) {
        item.removeAttribute("aria-current");
      });
      link.setAttribute("aria-current", "true");
    });
  }

  function initContactForm() {
    var form = document.getElementById("contact-form");
    if (!form) {
      return;
    }
    var select = document.getElementById("unit-interest");
    var wanted = new URLSearchParams(window.location.search).get("unit");
    if (select && wanted) {
      Array.prototype.forEach.call(select.options, function (option) {
        if (option.value === wanted) {
          select.value = wanted;
        }
      });
    }
    var action = form.getAttribute("action") || "";
    if (action.indexOf("PLACEHOLDER") === -1) {
      return;
    }
    function blockSubmit(event) {
      event.preventDefault();
      var note = document.getElementById("form-setup-note");
      if (!note) {
        note = document.createElement("p");
        note.id = "form-setup-note";
        note.className = "notice";
        note.setAttribute("role", "status");
        form.parentNode.insertBefore(note, form);
      }
      note.textContent = SETUP_MESSAGE;
      note.hidden = false;
      if (!note.hasAttribute("tabindex")) {
        note.setAttribute("tabindex", "-1");
      }
      note.focus();
    }
    form.addEventListener("submit", blockSubmit);
    var submitButton = form.querySelector("[type='submit']");
    if (submitButton) {
      submitButton.addEventListener("click", blockSubmit);
    }
  }

  function refreshAvailability() {
    var src = document.body.getAttribute("data-availability-src");
    if (!src || !window.fetch) {
      return;
    }
    window.fetch(src, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) {
          return null;
        }
        return response.json();
      })
      .then(function (data) {
        if (!data || !data.units) {
          return;
        }
        var units = data.units;
        Array.prototype.forEach.call(document.querySelectorAll("[data-unit-status]"), function (el) {
          var id = el.getAttribute("data-unit-status");
          var info = units[id];
          if (!info || !info.status) {
            return;
          }
          var view = statusView(info.status);
          el.textContent = view.label;
          el.className = view.className;
          var card = el.closest("[data-unit-card]");
          if (card && card.getAttribute("data-unit-id") === id) {
            card.setAttribute("data-status", info.status);
          }
        });
        Array.prototype.forEach.call(document.querySelectorAll("[data-unit-next-open]"), function (el) {
          var id = el.getAttribute("data-unit-next-open");
          var info = units[id];
          if (!info || !info.nextOpenDate) {
            el.hidden = true;
            el.textContent = "";
            return;
          }
          el.hidden = false;
          el.textContent = "Next open date: " + prettyDate(info.nextOpenDate);
        });
        if (data.asOf) {
          Array.prototype.forEach.call(document.querySelectorAll("[data-as-of]"), function (el) {
            el.textContent = "Availability as of " + prettyDate(data.asOf);
          });
        }
        applyFilters();
      })
      .catch(function () {
        return null;
      });
  }

  initFilters();
  initContactForm();
  initGallery();
  refreshAvailability();
})();
