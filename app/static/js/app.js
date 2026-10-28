(function () {
  function show(el, message) {
    if (!el) return;
    el.hidden = !message;
    el.textContent = message || "";
  }

  function pad2(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function formatDisplayDate(d) {
    return pad2(d.getDate()) + " / " + pad2(d.getMonth() + 1) + " / " + d.getFullYear();
  }

  function isoDate(d) {
    return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
  }

  function minutesTo12(totalMins) {
    var h24 = Math.floor(totalMins / 60);
    var m = totalMins % 60;
    var suffix = h24 < 12 ? "AM" : "PM";
    var h12 = h24 % 12 || 12;
    return h12 + ":" + pad2(m) + " " + suffix;
  }

  function minutesTo24(totalMins) {
    return pad2(Math.floor(totalMins / 60)) + ":" + pad2(totalMins % 60);
  }

  var submitOverlay = document.getElementById("submit-overlay");

  function setFormSubmitting(form, loading) {
    if (!form) return;
    var btn = form.querySelector('button[type="submit"]');
    if (btn) {
      btn.classList.toggle("is-loading", loading);
      btn.disabled = loading;
    }
    form.classList.toggle("is-submitting", loading);
    if (submitOverlay) {
      submitOverlay.hidden = !loading;
      submitOverlay.setAttribute("aria-hidden", loading ? "false" : "true");
    }
    document.body.classList.toggle("submit-busy", loading);
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || form.tagName !== "FORM") return;
    if (event.defaultPrevented) return;
    if (form.dataset.clientOnly === "true") return;
    setFormSubmitting(form, true);
  });

  function emailOk(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  function postAppointmentAction(row, action) {
    if (!row || !row.dataset.id) return;
    var form = document.createElement("form");
    form.method = "post";
    form.action = "/appointments/status";
    form.hidden = true;
    [["appointment_id", row.dataset.id], ["action", action], ["next", window.location.pathname + window.location.search]].forEach(function (pair) {
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = pair[0];
      input.value = pair[1];
      form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
  }

  function bindLogin(formId, errorId) {
    var form = document.getElementById(formId);
    if (!form) return;
    form.addEventListener("submit", function (event) {
      var username = form.querySelector('input[name="username"]');
      var password = form.querySelector('input[type="password"]');
      var error = document.getElementById(errorId);
      var message = "";
      if (!username.value.trim()) message = "Enter your mobile or username.";
      else if (!password.value) message = "Enter your password.";
      else if (password.value.length < 6) message = "Password must be at least 6 characters.";
      if (message) {
        event.preventDefault();
        show(error, message);
        (username.value.trim() ? password : username).focus();
        return;
      }
      setFormSubmitting(form, true);
    });
  }

  bindLogin("home-login", "home-login-error");
  bindLogin("login-form", "login-error");

  var menu = document.getElementById("menu-btn");
  var shell = document.getElementById("shell");
  if (menu && shell) {
    function setNav(open) {
      shell.classList.toggle("nav-open", open);
      menu.setAttribute("aria-expanded", open ? "true" : "false");
      document.body.classList.toggle("nav-lock", open);
      if (open) {
        var current = shell.querySelector('.side-nav a[aria-current="page"]') || shell.querySelector(".side-nav a");
        if (current) current.focus();
      }
    }
    menu.addEventListener("click", function () {
      setNav(!shell.classList.contains("nav-open"));
    });
    var scrim = document.getElementById("nav-scrim");
    if (scrim) scrim.addEventListener("click", function () { setNav(false); menu.focus(); });
    shell.querySelectorAll(".side-nav a").forEach(function (link) {
      link.addEventListener("click", function () { setNav(false); });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && shell.classList.contains("nav-open")) {
        setNav(false);
        menu.focus();
      }
    });
  }

  var burger = document.getElementById("nav-burger");
  var siteNav = document.getElementById("site-nav");
  if (burger && siteNav) {
    function setSiteNav(open) {
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      var header = burger.closest(".site-header");
      if (header) header.classList.toggle("is-open", open);
    }
    burger.addEventListener("click", function () {
      setSiteNav(burger.getAttribute("aria-expanded") !== "true");
    });
    siteNav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () { setSiteNav(false); });
    });
  }

  var table = document.getElementById("patient-table");
  if (table) {
    var search = document.getElementById("patient-search");
    var rows = Array.prototype.slice.call(table.querySelectorAll(".prow"));
    var filters = { status: "", doctor: "", department: "", date: "" };
    function applyPatients() {
      var q = (search.value || "").trim().toLowerCase();
      var digits = q.replace(/\D/g, "");
      var shown = 0;
      rows.forEach(function (row) {
        var blob = (row.dataset.name + " " + row.dataset.phone + " " + row.dataset.mrn).toLowerCase();
        var phoneDigits = row.dataset.phone.replace(/\D/g, "");
        var matchQ = !q || blob.indexOf(q) !== -1 || (digits && phoneDigits.indexOf(digits) !== -1);
        var match = matchQ
          && (!filters.status || row.dataset.status === filters.status)
          && (!filters.doctor || row.dataset.doctor === filters.doctor)
          && (!filters.department || row.dataset.department === filters.department)
          && (!filters.date || row.dataset.date === filters.date);
        row.hidden = !match;
        if (match) shown += 1;
      });
      var empty = document.getElementById("no-patients");
      if (empty) empty.hidden = shown !== 0;
      var count = document.getElementById("page-count");
      if (count) count.textContent = shown ? "Showing 1–" + shown + " of " + rows.length : "Showing 0 of " + rows.length;
    }
    if (search) search.addEventListener("input", applyPatients);
    table.querySelectorAll(".filter-menu button").forEach(function (button) {
      button.addEventListener("click", function () {
        filters[button.dataset.filter] = button.dataset.value;
        var menu = button.parentElement;
        menu.querySelectorAll("button").forEach(function (item) { item.setAttribute("aria-pressed", item === button ? "true" : "false"); });
        var details = menu.closest("details");
        if (details) details.open = false;
        applyPatients();
      });
    });
    document.addEventListener("click", function (event) {
      table.querySelectorAll(".filter[open]").forEach(function (details) {
        if (!details.contains(event.target)) details.open = false;
      });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      table.querySelectorAll(".filter[open]").forEach(function (details) {
        details.open = false;
      });
    });
    var exportBtn = document.getElementById("export-btn");
    if (exportBtn) {
      exportBtn.addEventListener("click", function () {
        var lines = ["Name,Phone,MRN,Doctor,Department,Status,Payment,Last visit"];
        rows.forEach(function (row) {
          if (row.hidden) return;
          lines.push([row.dataset.name, row.dataset.phone, row.dataset.mrn, row.dataset.doctor, row.dataset.department, row.dataset.status, row.dataset.payment, row.dataset.date].join(","));
        });
        var blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
        var link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "patients.csv";
        link.click();
        URL.revokeObjectURL(link.href);
      });
    }
    applyPatients();
  }

  var recordTable = document.getElementById("record-table");
  var records = [];
  if (recordTable) {
    records = Array.prototype.slice.call(document.querySelectorAll("#record-table .record-row"));
    var countLabel = document.getElementById("record-count");
    if (countLabel) countLabel.textContent = records.length ? "Showing 1–" + records.length + " of " + records.length : "Showing 0 of 0";
  }

  var recordSearch = document.getElementById("ps");
  if (recordSearch) {
    if (!records.length) records = Array.prototype.slice.call(document.querySelectorAll("#record-table .record-row"));
    recordSearch.addEventListener("input", function () {
      var q = recordSearch.value.trim().toLowerCase();
      var shown = 0;
      records.forEach(function (row) {
        var match = !q || (row.dataset.name + " " + row.dataset.phone).toLowerCase().indexOf(q) !== -1;
        row.hidden = !match;
        if (match) shown += 1;
      });
      var label = document.getElementById("record-count");
      if (label) label.textContent = shown ? "Showing 1–" + shown + " of " + records.length : "Showing 0 of " + records.length;
    });
  }

  var importBtn = document.getElementById("import-btn");
  if (importBtn) importBtn.addEventListener("click", function () { show(document.getElementById("import-note"), "Import from CSV will be added in a later release. Add patients with the form below."); });

  var patientForm = document.getElementById("patient-form");
  if (patientForm) {
    bindDobPicker();
    patientForm.addEventListener("submit", function (event) {
      if (event.defaultPrevented) return;
      var V = window.ClinicValidate;
      var dob = document.getElementById("p2-value").value.trim();
      var message = V
        ? V.validatePatient(
          document.getElementById("p1").value,
          document.getElementById("p3").value,
          document.getElementById("p5").value,
          document.getElementById("p4").value
        )
        : "";
      if (!message && !dob) message = "Choose date of birth from the calendar.";
      var error = document.getElementById("patient-error");
      if (message) {
        event.preventDefault();
        show(error, message);
        return;
      }
      show(error, "");
      setFormSubmitting(patientForm, true);
    });
  }

  var book = document.getElementById("quick-book");
  if (book) {
    bindDateTimePickers();
    book.addEventListener("submit", function (event) {
      var patient = document.getElementById("q1").value.trim();
      var date = document.getElementById("q2-value").value.trim();
      var time = document.getElementById("q3-value").value.trim();
      var doctor = document.getElementById("q4").value.trim();
      var reason = document.getElementById("q5").value.trim();
      var payment = document.getElementById("q6").value;
      var error = document.getElementById("book-error");
      var ok = document.getElementById("book-ok");
      var message = "";
      var V = window.ClinicValidate;
      if (!patient) message = "Enter the patient.";
      else if (V && !V.nameOk(patient)) message = V.nameMessage;
      else if (!date) message = "Choose a date from the calendar.";
      else if (!time) message = "Choose a time.";
      else if (!doctor) message = "Enter the doctor.";
      else if (V && !V.nameOk(doctor)) message = "Doctor name must be at least 3 letters.";
      else if (reason.length < 3) message = "Describe the problem or reason for the visit.";
      else if (!payment) message = "Select a payment status.";
      if (message) {
        event.preventDefault();
        show(ok, "");
        show(error, message);
        return;
      }
      show(error, "");
      show(ok, "");
      setFormSubmitting(book, true);
    });
  }

  function resetPicker(button, label) {
    if (!button) return;
    button.textContent = label;
    button.setAttribute("aria-label", label);
    button.classList.add("is-empty");
  }

  function bindCalendarPicker(options) {
    var dateBtn = document.getElementById(options.triggerId);
    var dateValue = document.getElementById(options.valueId);
    var datePop = document.getElementById(options.popId);
    var titleEl = document.getElementById(options.titleId);
    var gridEl = document.getElementById(options.gridId);
    if (!dateBtn || !dateValue || !datePop || !titleEl || !gridEl) return;

    var view = new Date();
    view.setDate(1);
    if (options.mode === "past") view.setFullYear(view.getFullYear() - 25);
    var selected = null;
    var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    var weekdays = options.modern
      ? ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
      : ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
    if (options.modern) gridEl.classList.add("cal-grid-modern");
    var otherPop = options.otherPop;
    var otherTrigger = options.otherTrigger;

    function pad(n) { return n < 10 ? "0" + n : String(n); }
    function formatDate(d) { return pad(d.getDate()) + " / " + pad(d.getMonth() + 1) + " / " + d.getFullYear(); }
    function close(pop, trigger) {
      if (!pop || !trigger) return;
      pop.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
    }
    function open(pop, trigger) {
      if (otherPop && otherTrigger) close(otherPop, otherTrigger);
      pop.hidden = false;
      pop.style.top = "";
      pop.style.bottom = "";
      var roomBelow = window.innerHeight - trigger.getBoundingClientRect().bottom;
      if (roomBelow < pop.offsetHeight + 16) {
        pop.style.top = "auto";
        pop.style.bottom = "calc(100% + 6px)";
      }
      trigger.setAttribute("aria-expanded", "true");
    }
    function dayDisabled(date) {
      var today = new Date();
      today.setHours(0, 0, 0, 0);
      if (options.mode === "past") return date > today;
      if (options.mode === "future") return date < today;
      return false;
    }
    function renderCal() {
      titleEl.textContent = months[view.getMonth()] + " " + view.getFullYear();
      gridEl.replaceChildren();
      weekdays.forEach(function (label) {
        var el = document.createElement("span");
        el.className = "cal-dow";
        el.textContent = label;
        gridEl.appendChild(el);
      });
      var first = new Date(view.getFullYear(), view.getMonth(), 1);
      var start = options.modern ? first.getDay() : (first.getDay() + 6) % 7;
      var days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
      var today = new Date();
      today.setHours(0, 0, 0, 0);
      for (var i = 0; i < start; i += 1) gridEl.appendChild(document.createElement("span"));
      for (var day = 1; day <= days; day += 1) {
        var date = new Date(view.getFullYear(), view.getMonth(), day);
        date.setHours(0, 0, 0, 0);
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "cal-day";
        btn.textContent = String(day);
        if (dayDisabled(date)) btn.disabled = true;
        if (date.getTime() === today.getTime()) btn.classList.add("is-today");
        if (selected && date.getTime() === selected.getTime()) btn.classList.add("is-selected");
        btn.addEventListener("click", function (chosen) {
          return function () {
            selected = chosen;
            dateValue.value = formatDate(chosen);
            dateBtn.textContent = formatDate(chosen);
            dateBtn.setAttribute("aria-label", "Date " + formatDate(chosen));
            dateBtn.classList.remove("is-empty");
            close(datePop, dateBtn);
          };
        }(date));
        gridEl.appendChild(btn);
      }
    }

    dateBtn.addEventListener("click", function () {
      if (datePop.hidden) { renderCal(); open(datePop, dateBtn); }
      else close(datePop, dateBtn);
    });
    datePop.querySelector("[data-cal='prev']").addEventListener("click", function () {
      view.setMonth(view.getMonth() - 1);
      renderCal();
    });
    datePop.querySelector("[data-cal='next']").addEventListener("click", function () {
      view.setMonth(view.getMonth() + 1);
      renderCal();
    });
    document.addEventListener("click", function (event) {
      if (!dateBtn.contains(event.target) && !datePop.contains(event.target)) close(datePop, dateBtn);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") close(datePop, dateBtn);
    });
    if (dateValue.value) {
      var parts = dateValue.value.match(/^(\d{1,2})\s*\/\s*(\d{1,2})\s*\/\s*(\d{4})$/);
      if (parts) {
        selected = new Date(parseInt(parts[3], 10), parseInt(parts[2], 10) - 1, parseInt(parts[1], 10));
        selected.setHours(0, 0, 0, 0);
        dateBtn.textContent = dateValue.value;
        dateBtn.setAttribute("aria-label", "Date " + dateValue.value);
        dateBtn.classList.remove("is-empty");
      }
    }
  }

  function bindDobPicker() {
    bindCalendarPicker({
      triggerId: "p2",
      valueId: "p2-value",
      popId: "dob-picker",
      titleId: "dob-cal-title",
      gridId: "dob-cal-grid",
      mode: "past"
    });
  }

  function bindTimePicker(options) {
    var timeBtn = document.getElementById(options.triggerId);
    var timeValue = document.getElementById(options.valueId);
    var timePop = document.getElementById(options.popId);
    var gridEl = document.getElementById(options.gridId);
    if (!timeBtn || !timeValue || !timePop || !gridEl) return;
    var datePop = options.otherPop;
    var dateBtn = options.otherTrigger;

    function closeTime() {
      timePop.hidden = true;
      timeBtn.setAttribute("aria-expanded", "false");
    }
    function openTime() {
      if (datePop && dateBtn) {
        datePop.hidden = true;
        dateBtn.setAttribute("aria-expanded", "false");
      }
      timePop.hidden = false;
      timeBtn.setAttribute("aria-expanded", "true");
    }
    function renderTimes() {
      gridEl.replaceChildren();
      for (var mins = 9 * 60; mins <= 18 * 60; mins += 30) {
        var label12 = minutesTo12(mins);
        var value24 = minutesTo24(mins);
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "time-slot";
        btn.textContent = label12;
        if (timeValue.value === value24 || timeValue.value.toUpperCase() === label12) btn.classList.add("is-selected");
        btn.addEventListener("click", function (display, stored) {
          return function () {
            timeValue.value = stored;
            timeBtn.textContent = display;
            timeBtn.setAttribute("aria-label", "Time " + display);
            timeBtn.classList.remove("is-empty");
            closeTime();
          };
        }(label12, value24));
        gridEl.appendChild(btn);
      }
    }
    timeBtn.addEventListener("click", function () {
      if (timePop.hidden) { renderTimes(); openTime(); }
      else closeTime();
    });
    document.addEventListener("click", function (event) {
      if (!timeBtn.contains(event.target) && !timePop.contains(event.target)) closeTime();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeTime();
    });
  }

  function bindDateTimePickers() {
    bindCalendarPicker({
      triggerId: "q2",
      valueId: "q2-value",
      popId: "date-picker",
      titleId: "cal-title",
      gridId: "cal-grid",
      mode: "future",
      modern: true,
      otherPop: document.getElementById("time-picker"),
      otherTrigger: document.getElementById("q3")
    });
    bindTimePicker({
      triggerId: "q3",
      valueId: "q3-value",
      popId: "time-picker",
      gridId: "time-grid",
      otherPop: document.getElementById("date-picker"),
      otherTrigger: document.getElementById("q2")
    });
  }

  function bindVisitDatePicker() {
    bindCalendarPicker({
      triggerId: "v-date-btn",
      valueId: "v-date-value",
      popId: "visit-date-picker",
      titleId: "visit-cal-title",
      gridId: "visit-cal-grid",
      mode: "past",
      modern: true
    });
  }

  function initAppointmentsCalendar() {
    var dataNode = document.getElementById("appointments-data");
    var weekView = document.getElementById("cal-week-view");
    var monthView = document.getElementById("cal-month-view");
    if (!dataNode || !weekView || !monthView) return;

    var items = [];
    try { items = JSON.parse(dataNode.textContent || "[]"); } catch (error) { items = []; }
    var byDate = {};
    items.forEach(function (item) {
      var key = item.date_iso || "";
      if (!key) return;
      if (!byDate[key]) byDate[key] = [];
      byDate[key].push(item);
    });

    var viewMode = "week";
    var anchor = new Date();
    anchor.setHours(0, 0, 0, 0);
    var monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    var dowShort = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    var titleEl = document.getElementById("cal-period-title");
    var rangeEl = document.getElementById("cal-period-range");
    var sheet = document.getElementById("day-appt-sheet");
    var sheetList = document.getElementById("day-sheet-list");
    var sheetTitle = document.getElementById("day-sheet-title");
    var sheetDate = document.getElementById("day-sheet-date");
    var monthMount = document.getElementById("month-cal-mount");
    var monthPanel = document.getElementById("month-day-panel");
    var monthPanelPlaceholder = document.getElementById("month-panel-placeholder");
    var monthPanelContent = document.getElementById("month-panel-content");
    var monthPanelDow = document.getElementById("month-panel-dow");
    var monthPanelTitle = document.getElementById("month-panel-title");
    var monthPanelCount = document.getElementById("month-panel-count");
    var monthPanelList = document.getElementById("month-panel-list");
    var selectedDayIso = "";

    function isDesktopCalendar() {
      return window.matchMedia("(min-width: 960px)").matches;
    }

    function mondayOf(d) {
      var copy = new Date(d);
      var day = copy.getDay();
      var diff = day === 0 ? -6 : 1 - day;
      copy.setDate(copy.getDate() + diff);
      return copy;
    }

    function applyApptDataset(el, item) {
      el.dataset.id = item.id;
      el.dataset.patient = item.patient;
      el.dataset.time = item.time;
      el.dataset.doctor = item.doctor;
      el.dataset.reason = item.reason;
      el.dataset.payment = item.payment;
      el.dataset.date = item.date;
      el.dataset.status = item.status;
    }

    function openApptFromItem(item, closeSheetFirst) {
      var row = document.createElement("div");
      applyApptDataset(row, item);
      if (closeSheetFirst && sheet && sheet.open) sheet.close();
      openSheet(row);
    }

    function fillMonthPanel(dateObj, list) {
      if (!monthPanelContent || !monthPanelList) return;
      var dowLong = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
      if (monthPanelPlaceholder) monthPanelPlaceholder.hidden = true;
      monthPanelContent.hidden = false;
      if (monthPanelDow) monthPanelDow.textContent = dowLong[dateObj.getDay()];
      if (monthPanelTitle) monthPanelTitle.textContent = String(dateObj.getDate());
      if (monthPanelCount) {
        monthPanelCount.textContent = list.length
          ? list.length + " appointment" + (list.length > 1 ? "s" : "")
          : "No appointments scheduled";
      }
      monthPanelList.replaceChildren();
      if (!list.length) {
        var empty = document.createElement("p");
        empty.className = "empty";
        empty.textContent = "Nothing booked for this day. Use Quick book to add one.";
        monthPanelList.appendChild(empty);
        return;
      }
      list.forEach(function (item) {
        var card = document.createElement("button");
        card.type = "button";
        card.className = "month-timeline-card appt-open";
        applyApptDataset(card, item);
        card.innerHTML = "<span class=\"month-timeline-time\">" + item.time + "</span><span class=\"month-timeline-body\"><b>" + item.patient + "</b><span>" + item.reason + " · " + item.doctor + "</span></span>";
        card.addEventListener("click", function () { openApptFromItem(item, false); });
        monthPanelList.appendChild(card);
      });
    }

    function resetMonthPanelPlaceholder() {
      if (monthPanelPlaceholder) monthPanelPlaceholder.hidden = false;
      if (monthPanelContent) monthPanelContent.hidden = true;
    }

    function openDaySheet(dateObj, list) {
      if (!sheet || !sheetList) return;
      sheetTitle.textContent = list.length ? list.length + " appointment" + (list.length > 1 ? "s" : "") : "No appointments";
      sheetDate.textContent = formatDisplayDate(dateObj);
      sheetList.replaceChildren();
      if (!list.length) {
        var empty = document.createElement("p");
        empty.className = "empty";
        empty.textContent = "No appointments on this day.";
        sheetList.appendChild(empty);
      } else {
        list.forEach(function (item) {
          var row = document.createElement("div");
          row.className = "list-row";
          applyApptDataset(row, item);
          row.innerHTML = "<div><b>" + item.time + " · " + item.patient + "</b><span>" + item.reason + " · " + item.doctor + "</span></div>";
          row.addEventListener("click", function () { openApptFromItem(item, true); });
          sheetList.appendChild(row);
        });
      }
      if (!sheet.open) sheet.showModal();
    }

    function selectMonthDay(dateObj, list, skipSheet) {
      selectedDayIso = isoDate(dateObj);
      if (isDesktopCalendar()) {
        fillMonthPanel(dateObj, list);
        if (monthMount) {
          monthMount.querySelectorAll(".month-cell.is-selected").forEach(function (cell) {
            cell.classList.remove("is-selected");
          });
          var active = monthMount.querySelector(".month-cell[data-iso=\"" + selectedDayIso + "\"]");
          if (active) active.classList.add("is-selected");
        }
      } else if (!skipSheet) {
        openDaySheet(dateObj, list);
      }
    }

    function renderWeek() {
      var start = mondayOf(anchor);
      var end = new Date(start);
      end.setDate(start.getDate() + 6);
      if (titleEl) titleEl.textContent = "Week view";
      if (rangeEl) rangeEl.textContent = formatDisplayDate(start) + " – " + formatDisplayDate(end);
      weekView.replaceChildren();
      var wrap = document.createElement("div");
      wrap.className = "week-columns";
      var today = new Date();
      today.setHours(0, 0, 0, 0);
      for (var i = 0; i < 7; i += 1) {
        var day = new Date(start);
        day.setDate(start.getDate() + i);
        var col = document.createElement("div");
        var isTodayCol = day.getTime() === today.getTime();
        col.className = "cal-week-col" + (isTodayCol ? " is-today-col" : "");
        var head = document.createElement("div");
        head.className = "cal-week-col-head" + (isTodayCol ? " is-today" : "");
        head.innerHTML = "<span>" + dowShort[day.getDay()] + "</span><b>" + day.getDate() + "</b>";
        col.appendChild(head);
        var key = isoDate(day);
        var dayItems = byDate[key] || [];
        if (!dayItems.length) {
          var hint = document.createElement("p");
          hint.className = "empty";
          hint.style.fontSize = "12px";
          hint.textContent = "—";
          col.appendChild(hint);
        } else {
          dayItems.forEach(function (item) {
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = "week-appt appt-open";
            btn.dataset.id = item.id;
            btn.dataset.patient = item.patient;
            btn.dataset.time = item.time;
            btn.dataset.doctor = item.doctor;
            btn.dataset.reason = item.reason;
            btn.dataset.payment = item.payment;
            btn.dataset.date = item.date;
            btn.dataset.status = item.status;
            btn.innerHTML = "<b>" + item.time + "</b><span>" + item.patient + "</span>";
            col.appendChild(btn);
          });
        }
        wrap.appendChild(col);
      }
      weekView.appendChild(wrap);
      var todayCol = wrap.querySelector(".is-today-col");
      if (todayCol) todayCol.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }

    function renderMonth() {
      if (!monthMount) return;
      var view = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
      if (titleEl) titleEl.textContent = monthNames[view.getMonth()] + " " + view.getFullYear();
      if (rangeEl) {
        rangeEl.textContent = isDesktopCalendar()
          ? "Select a day — schedule shows on the right"
          : "Tap a date to see appointments";
      }
      monthMount.replaceChildren();
      var board = document.createElement("div");
      board.className = "month-cal-board";
      var head = document.createElement("div");
      head.className = "month-cal-board-head";
      ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"].forEach(function (label) {
        var el = document.createElement("span");
        el.textContent = label;
        head.appendChild(el);
      });
      board.appendChild(head);
      var grid = document.createElement("div");
      grid.className = "month-cal-grid";
      var first = new Date(view.getFullYear(), view.getMonth(), 1);
      var start = first.getDay();
      var daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
      var daysInPrev = new Date(view.getFullYear(), view.getMonth(), 0).getDate();
      var today = new Date();
      today.setHours(0, 0, 0, 0);

      function addCell(dateObj, inMonth) {
        var key = isoDate(dateObj);
        var list = inMonth ? (byDate[key] || []) : [];
        var cell = document.createElement("button");
        cell.type = "button";
        cell.className = "month-cell";
        cell.dataset.iso = key;
        if (!inMonth) cell.classList.add("is-outside");
        if (list.length) cell.classList.add("has-appts");
        if (dateObj.getTime() === today.getTime()) cell.classList.add("is-today");
        if (key === selectedDayIso) cell.classList.add("is-selected");
        var num = document.createElement("span");
        num.className = "month-cell-num";
        num.textContent = String(dateObj.getDate());
        cell.appendChild(num);
        var events = document.createElement("div");
        events.className = "month-cell-events";
        var preview = list.slice(0, 2);
        preview.forEach(function (item) {
          var chip = document.createElement("button");
          chip.type = "button";
          chip.className = "month-appt-chip" + (item.status === "cancelled" ? " is-cancelled" : "");
          chip.textContent = item.time + " " + item.patient;
          chip.addEventListener("click", function (ev) {
            ev.stopPropagation();
            openApptFromItem(item, false);
          });
          events.appendChild(chip);
        });
        if (list.length > 2) {
          var more = document.createElement("span");
          more.className = "month-appt-more";
          more.textContent = "+" + (list.length - 2) + " more";
          events.appendChild(more);
        }
        cell.appendChild(events);
        cell.addEventListener("click", function (chosen, dayList) {
          return function () {
            selectMonthDay(chosen, dayList, false);
          };
        }(dateObj, list));
        grid.appendChild(cell);
      }

      for (var lead = start - 1; lead >= 0; lead -= 1) {
        var prevDate = new Date(view.getFullYear(), view.getMonth() - 1, daysInPrev - lead);
        prevDate.setHours(0, 0, 0, 0);
        addCell(prevDate, false);
      }
      for (var d = 1; d <= daysInMonth; d += 1) {
        var dateObj = new Date(view.getFullYear(), view.getMonth(), d);
        dateObj.setHours(0, 0, 0, 0);
        addCell(dateObj, true);
      }
      var totalCells = start + daysInMonth;
      var trailing = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
      for (var t = 1; t <= trailing; t += 1) {
        var nextDate = new Date(view.getFullYear(), view.getMonth() + 1, t);
        nextDate.setHours(0, 0, 0, 0);
        addCell(nextDate, false);
      }
      board.appendChild(grid);
      monthMount.appendChild(board);

      if (isDesktopCalendar()) {
        var pickIso = selectedDayIso;
        var pickDate = null;
        var pickList = [];
        if (pickIso) {
          pickList = byDate[pickIso] || [];
          var parts = pickIso.split("-");
          pickDate = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
        }
        if (!pickDate || pickDate.getMonth() !== view.getMonth() || pickDate.getFullYear() !== view.getFullYear()) {
          pickDate = new Date(today);
          if (pickDate.getMonth() !== view.getMonth() || pickDate.getFullYear() !== view.getFullYear()) {
            pickDate = new Date(view.getFullYear(), view.getMonth(), 1);
          }
          pickList = byDate[isoDate(pickDate)] || [];
        }
        selectMonthDay(pickDate, pickList, true);
      } else {
        resetMonthPanelPlaceholder();
      }
    }

    function render() {
      if (viewMode === "week") {
        weekView.hidden = false;
        monthView.hidden = true;
        renderWeek();
      } else {
        weekView.hidden = true;
        monthView.hidden = false;
        renderMonth();
      }
    }

    document.querySelectorAll("[data-cal-view]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        viewMode = tab.dataset.calView;
        document.querySelectorAll("[data-cal-view]").forEach(function (btn) {
          btn.setAttribute("aria-selected", btn === tab ? "true" : "false");
        });
        if (viewMode === "month") {
          anchor = new Date();
          anchor.setHours(0, 0, 0, 0);
          anchor.setDate(1);
          selectedDayIso = "";
        } else {
          anchor = new Date();
          anchor.setHours(0, 0, 0, 0);
          selectedDayIso = isoDate(anchor);
        }
        render();
      });
    });
    window.addEventListener("resize", function () {
      if (viewMode !== "month") return;
      if (rangeEl) {
        rangeEl.textContent = isDesktopCalendar()
          ? "Select a day — schedule shows on the right"
          : "Tap a date to see appointments";
      }
      renderMonth();
    });
    var prev = document.getElementById("cal-prev");
    var next = document.getElementById("cal-next");
    var todayBtn = document.getElementById("cal-today");
    if (prev) prev.addEventListener("click", function () {
      if (viewMode === "week") anchor.setDate(anchor.getDate() - 7);
      else anchor.setMonth(anchor.getMonth() - 1);
      render();
    });
    if (next) next.addEventListener("click", function () {
      if (viewMode === "week") anchor.setDate(anchor.getDate() + 7);
      else anchor.setMonth(anchor.getMonth() + 1);
      render();
    });
    if (todayBtn) todayBtn.addEventListener("click", function () {
      anchor = new Date();
      anchor.setHours(0, 0, 0, 0);
      render();
    });
    var closeBtn = document.getElementById("day-sheet-close");
    if (closeBtn && sheet) {
      closeBtn.addEventListener("click", function () { sheet.close(); });
      sheet.addEventListener("click", function (event) {
        if (event.target === sheet) sheet.close();
      });
    }
    render();
  }

  var tabs = document.querySelectorAll(".tabs button");
  function activateTab(tab) {
    if (!tab) return;
    tabs.forEach(function (item) {
      var selected = item === tab;
      item.setAttribute("aria-selected", selected ? "true" : "false");
      var panel = document.getElementById(item.getAttribute("aria-controls"));
      if (panel) panel.hidden = !selected;
    });
  }
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () { activateTab(tab); });
  });
  (function () {
    var params = new URLSearchParams(window.location.search);
    var saved = params.get("saved");
    var err = params.get("error");
    var tabId = null;
    if (saved === "rx" || err === "rx") tabId = "tab-rx";
    if (saved === "doc" || err === "doc") tabId = "tab-docs";
    if (tabId) activateTab(document.getElementById(tabId));
  })();

  var visitForm = document.getElementById("add-note");
  if (visitForm) {
    visitForm.addEventListener("submit", function (event) {
      var title = document.getElementById("v-title").value.trim();
      var dateEl = document.getElementById("v-date-value");
      var date = dateEl ? dateEl.value.trim() : "";
      var notes = document.getElementById("v-notes").value.trim();
      var error = document.getElementById("visit-error");
      if (!title || !date || !notes) {
        event.preventDefault();
        show(error, "Enter a title, date and note.");
        return;
      }
      show(error, "");
      setFormSubmitting(visitForm, true);
    });
  }

  var rxForm = document.getElementById("rx-form");
  if (rxForm) {
    bindCalendarPicker({
      triggerId: "rx-date-btn",
      valueId: "rx-date-value",
      popId: "rx-date-picker",
      titleId: "rx-cal-title",
      gridId: "rx-cal-grid",
      mode: "past",
      modern: true
    });
    rxForm.addEventListener("submit", function (event) {
      var med = document.getElementById("rx-med").value.trim();
      var dose = document.getElementById("rx-dose").value.trim();
      var dateEl = document.getElementById("rx-date-value");
      var date = dateEl ? dateEl.value.trim() : "";
      var error = document.getElementById("rx-error");
      if (!med || !dose || !date) {
        event.preventDefault();
        show(error, "Enter medication, dosage and date.");
        return;
      }
      show(error, "");
      setFormSubmitting(rxForm, true);
    });
  }

  var docForm = document.getElementById("doc-form");
  if (docForm) {
    docForm.addEventListener("submit", function (event) {
      var fileInput = document.getElementById("doc-file");
      var error = document.getElementById("doc-error");
      if (!fileInput || !fileInput.files || !fileInput.files.length) {
        event.preventDefault();
        show(error, "Choose a file to upload.");
        return;
      }
      if (fileInput.files[0].size > 5 * 1024 * 1024) {
        event.preventDefault();
        show(error, "File must be under 5 MB.");
        return;
      }
      show(error, "");
      setFormSubmitting(docForm, true);
    });
  }

  function bindSimple(formId, errorId, okId, okText, check) {
    var form = document.getElementById(formId);
    if (!form) return;
    form.dataset.clientOnly = "true";
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var message = check(form);
      show(document.getElementById(okId), message ? "" : okText);
      show(document.getElementById(errorId), message);
      if (!message) form.querySelectorAll('input[type="password"]').forEach(function (input) { input.value = ""; });
    });
  }

  bindSimple("profile-form", "profile-error", "profile-ok", "Profile saved.", function (form) {
    var V = window.ClinicValidate;
    if (!V) return "";
    var msg = V.validateClinicUser(
      form.querySelector("#a1").value,
      form.querySelector("#a4").value,
      form.querySelector('input[type="email"]').value
    );
    if (msg) return msg;
    if (!V.nameOk(form.querySelector("#a3").value)) return "Clinic name must be at least 3 letters.";
    return "";
  });

  bindSimple("password-form", "password-error", "password-ok", "Password updated.", function (form) {
    var next = form.querySelector("#a6").value;
    if (form.querySelector("#a5").value !== "123456") return "Enter your current password.";
    if (next.length < 8 || !/[A-Za-z]/.test(next) || !/\d/.test(next)) return "Use at least 8 characters with a letter and a number.";
    return "";
  });

  bindSimple("support-form", "support-error", "support-ok", "Message sent. We will reply during support hours.", function (form) {
    if (form.querySelector("#s1").value.trim().length < 3) return "Enter a subject.";
    if (form.querySelector("#s2").value.trim().length < 10) return "Describe the issue in a sentence or two.";
    return "";
  });

  function payClass(payment) {
    if (payment === "Pending") return "pill pill-pending";
    if (payment === "Unpaid") return "pill pill-unpaid";
    return "pill";
  }

  function actionButton(label, act) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = act === "cancel" ? "text-act danger" : "text-act";
    button.dataset.act = act;
    button.textContent = label;
    return button;
  }

  function patientDirectory() {
    var map = {};
    var node = document.getElementById("patient-directory");
    if (node) {
      try {
        JSON.parse(node.textContent || "[]").forEach(function (person) { map[person.name] = person; });
      } catch (error) { /* ignore */ }
    }
    return map;
  }

  var sheet = document.getElementById("patient-sheet");
  var sheetRow = null;

  function fact(label, value) {
    if (!value) return null;
    var row = document.createElement("div");
    row.className = "list-row";
    var block = document.createElement("div");
    var title = document.createElement("b");
    title.textContent = label;
    var detail = document.createElement("span");
    detail.textContent = value;
    block.appendChild(title);
    block.appendChild(detail);
    row.appendChild(block);
    return row;
  }

  function openSheet(row) {
    if (!sheet || !row) return;
    sheetRow = row;
    var person = patientDirectory()[row.dataset.patient] || {};
    document.getElementById("sheet-title").textContent = row.dataset.patient || "Patient";
    document.getElementById("sheet-when").textContent = [row.dataset.date, row.dataset.time, row.dataset.doctor].filter(Boolean).join(" · ");
    var facts = document.getElementById("sheet-facts");
    facts.replaceChildren();
    [fact("MRN", person.mrn), fact("Phone", person.phone), fact("Email", person.email), fact("Date of birth", person.dob), fact("Department", person.department), fact("Problem", row.dataset.reason), fact("Payment", row.dataset.payment), fact("Notes", person.notes)].forEach(function (line) {
      if (line) facts.appendChild(line);
    });
    var record = document.getElementById("sheet-record");
    record.href = "/history?patient=" + encodeURIComponent(row.dataset.patient || "");
    syncSheet(row);
    if (!sheet.open) sheet.showModal();
  }

  function syncSheet(row) {
    var done = row.dataset.status === "completed" || row.dataset.status === "cancelled";
    document.getElementById("sheet-attended").hidden = done;
    document.getElementById("sheet-cancel").hidden = done;
    var state = document.getElementById("sheet-state");
    state.hidden = !done;
    state.textContent = row.dataset.status === "cancelled" ? "This appointment is cancelled." : "Marked as attended.";
  }

  document.addEventListener("click", function (event) {
    var opener = event.target.closest(".appt-open");
    if (opener) openSheet(opener.closest("[data-patient]") || opener);
  });

  if (sheet) {
    document.getElementById("sheet-close").addEventListener("click", function () { sheet.close(); });
    document.getElementById("sheet-attended").addEventListener("click", function () { postAppointmentAction(sheetRow, "attended"); });
    document.getElementById("sheet-cancel").addEventListener("click", function () { postAppointmentAction(sheetRow, "cancel"); });
    sheet.addEventListener("click", function (event) {
      if (event.target === sheet) sheet.close();
    });
  }

  bindVisitDatePicker();
  initAppointmentsCalendar();

})();
