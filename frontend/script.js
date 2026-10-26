(() => {
  const form = document.querySelector("#recommendation-form");
  const submitButton = form.querySelector(".submit-button");
  const formError = document.querySelector("#form-error");
  const resultCard = document.querySelector("#result-card");
  const emptyState = document.querySelector("#result-empty");
  const loadingState = document.querySelector("#result-loading");
  const successState = document.querySelector("#result-success");
  const cropName = document.querySelector("#crop-name");
  const inputSummary = document.querySelector("#input-summary");
  const featureOrder = ["Nitrogen", "Phosphorus", "Potassium", "Temperature", "Humidity", "pH_Value", "Rainfall"];
  const displayNames = {
    Nitrogen: "Nitrogen", Phosphorus: "Phosphorus", Potassium: "Potassium",
    Temperature: "Temperature", Humidity: "Humidity", pH_Value: "Soil pH", Rainfall: "Rainfall"
  };
  const units = { Nitrogen: "dataset units", Phosphorus: "dataset units", Potassium: "dataset units", Temperature: "°C", Humidity: "%", pH_Value: "pH", Rainfall: "dataset units" };
  const cropLabels = {
    apple: "Apple", banana: "Banana", blackgram: "Black gram", chickpea: "Chickpea", coconut: "Coconut",
    coffee: "Coffee", cotton: "Cotton", grapes: "Grapes", jute: "Jute", kidneybeans: "Kidney beans",
    lentil: "Lentil", maize: "Maize", mango: "Mango", mothbeans: "Moth beans", mungbean: "Mung bean",
    muskmelon: "Muskmelon", orange: "Orange", papaya: "Papaya", pigeonpeas: "Pigeon peas",
    pomegranate: "Pomegranate", rice: "Rice", watermelon: "Watermelon"
  };

  document.querySelector("#year").textContent = new Date().getFullYear();

  function clearFieldError(input) {
    input.removeAttribute("aria-invalid");
    input.closest(".field").querySelector(".field-error").textContent = "";
  }

  function setFieldError(input, message) {
    input.setAttribute("aria-invalid", "true");
    input.closest(".field").querySelector(".field-error").textContent = message;
  }

  function validateAndRead() {
    let firstInvalid = null;
    const values = {};

    for (const name of featureOrder) {
      const input = form.elements.namedItem(name);
      clearFieldError(input);
      const raw = input.value.trim();
      const value = Number(raw);
      let message = "";

      if (!raw) message = "Enter a value to continue.";
      else if (!Number.isFinite(value)) message = "Enter a valid number.";
      else if (["Nitrogen", "Phosphorus", "Potassium", "Rainfall"].includes(name) && value < 0) message = "Enter zero or a positive value.";
      else if (name === "Humidity" && (value < 0 || value > 100)) message = "Humidity must be between 0 and 100%.";
      else if (name === "pH_Value" && (value < 0 || value > 14)) message = "Soil pH must be between 0 and 14.";

      if (message) {
        setFieldError(input, message);
        firstInvalid ??= input;
      } else {
        values[name] = value;
      }
    }

    if (firstInvalid) {
      firstInvalid.focus();
      return null;
    }
    return values;
  }

  function displayError(message) {
    formError.textContent = message;
    formError.hidden = false;
  }

  function setState(state) {
    resultCard.classList.toggle("is-loading", state === "loading");
    resultCard.classList.toggle("has-result", state === "success");
    emptyState.hidden = state !== "empty";
    loadingState.hidden = state !== "loading";
    successState.hidden = state !== "success";
  }

  function formatCrop(crop) {
    const key = String(crop || "").trim().toLowerCase().replace(/[\s_-]+/g, "");
    return cropLabels[key] || String(crop || "").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function renderSummary(values) {
    inputSummary.replaceChildren();
    for (const name of featureOrder) {
      const item = document.createElement("div");
      item.className = "summary-item";
      const label = document.createElement("span");
      label.textContent = displayNames[name];
      const value = document.createElement("strong");
      value.textContent = `${Number(values[name]).toLocaleString(undefined, { maximumFractionDigits: 2 })} ${units[name]}`;
      item.append(label, value);
      inputSummary.append(item);
    }
  }

  async function requestPrediction(values) {
    const baseUrl = window.AGRIBORA_CONFIG?.apiBaseUrl?.replace(/\/$/, "");
    if (!baseUrl) throw new Error("The prediction service URL has not been configured yet.");

    let response;
    try {
      response = await fetch(`${baseUrl}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values)
      });
    } catch {
      throw new Error("We couldn’t reach the prediction service. Check that the API is running and its URL is configured.");
    }

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(body.detail) ? "Please check the measurements and try again." : body.detail;
      throw new Error(detail || `The prediction service returned an error (${response.status}).`);
    }
    if (!body.crop) throw new Error("The prediction service returned an unexpected response.");
    return body.crop;
  }

  form.addEventListener("input", (event) => {
    if (event.target.matches("input")) clearFieldError(event.target);
    formError.hidden = true;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    const values = validateAndRead();
    if (!values) return;

    submitButton.disabled = true;
    submitButton.querySelector(".button-label").textContent = "Checking conditions…";
    setState("loading");
    document.querySelector(".result-card").scrollIntoView({ behavior: "smooth", block: "nearest" });

    try {
      const crop = await requestPrediction(values);
      cropName.textContent = formatCrop(crop);
      renderSummary(values);
      setState("success");
    } catch (error) {
      setState("empty");
      displayError(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    } finally {
      submitButton.disabled = false;
      submitButton.querySelector(".button-label").textContent = "Recommend a crop";
    }
  });

  document.querySelector("#reset-button").addEventListener("click", () => {
    form.reset();
    form.querySelectorAll("input").forEach(clearFieldError);
    formError.hidden = true;
    setState("empty");
    form.elements.namedItem("Nitrogen").focus();
  });
})();
