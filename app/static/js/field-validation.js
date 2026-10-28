(function () {
  function letterCount(value) {
    return (String(value || "").match(/[a-zA-Z]/g) || []).length;
  }

  function nameOk(value) {
    var t = String(value || "").trim();
    return t.length >= 3 && letterCount(t) >= 3;
  }

  function phoneDigits(value) {
    return String(value || "").replace(/\D/g, "");
  }

  function phoneOk(value, required) {
    var digits = phoneDigits(value);
    if (!digits) return !required;
    return digits.length === 10;
  }

  function addressOk(value, required) {
    var t = String(value || "").trim();
    if (!t) return !required;
    return t.length >= 5;
  }

  function emailOk(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
  }

  window.ClinicValidate = {
    nameOk: nameOk,
    phoneOk: phoneOk,
    addressOk: addressOk,
    emailOk: emailOk,
    nameMessage: "Name must be at least 3 letters.",
    phoneMessage: "Enter a 10-digit mobile number.",
    addressMessage: "Address must be at least 5 characters.",
    emailMessage: "Enter a valid email address, or leave it blank.",
    validatePatient: function (name, phone, address, email) {
      if (!nameOk(name)) return this.nameMessage;
      if (!phoneOk(phone, true)) return this.phoneMessage;
      if (!addressOk(address, true)) return this.addressMessage;
      if (email && !emailOk(email)) return this.emailMessage;
      return "";
    },
    validateClinic: function (name, phone, address) {
      if (!nameOk(name)) return "Clinic name must be at least 3 letters.";
      if (phone && !phoneOk(phone, false)) return this.phoneMessage;
      if (address && !addressOk(address, false)) return this.addressMessage;
      return "";
    },
    validateClinicUser: function (name, phone, email, phoneRequired) {
      if (!nameOk(name)) return this.nameMessage;
      if (!phoneOk(phone, phoneRequired !== false)) return this.phoneMessage;
      if (email && !emailOk(email)) return this.emailMessage;
      return "";
    },
    usernameOk: function (value) {
      var t = String(value || "").trim();
      if (t.length < 3 || t.length > 32) return false;
      return /^[a-zA-Z0-9._-]+$/.test(t);
    },
    usernameMessage: "Username: 3–32 characters, letters, numbers, dots, underscores or hyphens.",
    bindHints: function () {
      document.querySelectorAll("[data-validate-name]").forEach(function (el) {
        el.setAttribute("minlength", "3");
        el.setAttribute("autocomplete", el.getAttribute("autocomplete") || "name");
      });
      document.querySelectorAll("[data-validate-phone]").forEach(function (el) {
        el.setAttribute("inputmode", "numeric");
        el.setAttribute("maxlength", "14");
        el.setAttribute("autocomplete", el.getAttribute("autocomplete") || "tel");
      });
      document.querySelectorAll("[data-validate-phone-required]").forEach(function (el) {
        el.setAttribute("required", "required");
      });
      document.querySelectorAll("[data-validate-address]").forEach(function (el) {
        el.setAttribute("minlength", "5");
      });
      document.querySelectorAll("[data-validate-email]").forEach(function (el) {
        el.removeAttribute("required");
      });
    }
  };

  function showError(id, message) {
    var el = document.getElementById(id);
    if (!el) return;
    el.hidden = !message;
    el.textContent = message || "";
  }

  function bindForm(formId, errorId, validate) {
    var form = document.getElementById(formId);
    if (!form) return;
    form.addEventListener("submit", function (event) {
      var message = validate(form);
      if (message) {
        event.preventDefault();
        showError(errorId, message);
        return;
      }
      showError(errorId, "");
    });
  }

  function initForms() {
    window.ClinicValidate.bindHints();
    var V = window.ClinicValidate;
    bindForm("admin-clinic-form", "clinic-form-error", function () {
      return V.validateClinic(
        document.getElementById("c-name") && document.getElementById("c-name").value,
        document.getElementById("c-phone") && document.getElementById("c-phone").value,
        document.getElementById("c-address") && document.getElementById("c-address").value
      );
    });
    bindForm("admin-user-form", "user-form-error", function (form) {
      var msg = V.validateClinicUser(
        document.getElementById("u-name") && document.getElementById("u-name").value,
        document.getElementById("u-phone") && document.getElementById("u-phone").value,
        document.getElementById("u-email") && document.getElementById("u-email").value,
        true
      );
      if (msg) return msg;
      var user = form.querySelector('[name="username"]');
      var pass = form.querySelector('[name="password"]');
      if (!user || !V.usernameOk(user.value)) return V.usernameMessage;
      if (!pass || pass.value.length < 6) return "Password must be at least 6 characters.";
      if (!form.querySelector('[name="clinic_id"]').value) return "Choose a clinic.";
      return "";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initForms);
  } else {
    initForms();
  }
})();
