
(() => {
  "use strict";

  const panel = document.getElementById("fmis-event-indicator");
  if (!panel) return;

  const API =
    "https://www.financecalendar.com/wp-json/fc/v1/calendar" +
    "?country=US,GB&impact=high&limit=20";

  const FULL_CALENDAR = "calendar-api-test.html";
  let events = [];

  function releaseDate(event) {
    if (event.all_day === true) return null;
    const raw = event.release_at_utc;
    if (typeof raw !== "string" ||
        !/(Z|[+-]\d{2}:\d{2})$/i.test(raw)) return null;

    const date = new Date(raw);
    return Number.isFinite(date.getTime()) ? date : null;
  }

  function ukTime(date) {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/London",
      dateStyle: "medium",
      timeStyle: "short"
    }).format(date);
  }

  function markets(event) {
    const text = [
      event.country, event.title, event.name
    ].filter(Boolean).join(" ").toUpperCase();

    if (text.includes("US") ||
        text.includes("FOMC") ||
        text.includes("FEDERAL RESERVE")) {
      return "Gold | S&P 500 | Nasdaq 100";
    }

    if (text.includes("UK") ||
        text.includes("BOE") ||
        text.includes("BANK OF ENGLAND")) {
      return "FTSE 100 | Gold";
    }

    return "Multiple markets — verify impact";
  }

  function countdown(date) {
    const minutes = Math.max(
      0, Math.floor((date.getTime() - Date.now()) / 60000)
    );
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    return days + "d " + hours + "h " + (minutes % 60) + "m";
  }

  function render() {
    panel.replaceChildren();

    const upcoming = events.filter(
      e => e.date.getTime() > Date.now()
    );

    if (!upcoming.length) {
      panel.textContent =
        "No upcoming timed events in the current feed window.";
      return;
    }

    const next = upcoming[0];
    const heading = document.createElement("p");
    heading.textContent =
      "Next: " + next.name + " — " + countdown(next.date);
    heading.style.color = "#73d8a4";
    heading.style.fontWeight = "bold";
    panel.appendChild(heading);

    upcoming.slice(0, 3).forEach(event => {
      const row = document.createElement("div");
      row.style.padding = "10px 0";
      row.style.borderBottom = "1px solid #29384c";

      const name = document.createElement("strong");
      name.textContent = event.name;

      const detail = document.createElement("div");
      detail.textContent =
        ukTime(event.date) + " UK | " + event.markets;
      detail.style.fontSize = "13px";
      detail.style.marginTop = "5px";

      row.append(name, detail);
      panel.appendChild(row);
    });

    const link = document.createElement("a");
    link.href = FULL_CALENDAR;
    link.textContent = "View full economic calendar";
    link.style.display = "inline-block";
    link.style.marginTop = "12px";
    panel.appendChild(link);
  }

  async function load() {
    try {
      const response = await fetch(API, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("HTTP " + response.status);
      }

      const data = await response.json();
      if (!Array.isArray(data.events)) {
        throw new Error("Invalid calendar response");
      }

      events = data.events
        .filter(e => String(e.impact).toLowerCase() === "high")
        .map(e => ({
          name: e.title || e.name || "Economic event",
          country: e.country || "",
          date: releaseDate(e),
          markets: markets(e)
        }))
        .filter(e => e.date && e.date.getTime() > Date.now())
        .sort((a, b) => a.date - b.date);

      render();
    } catch (error) {
      if (!events.length) {
        panel.textContent =
          "Economic calendar temporarily unavailable.";
      } else {
        render();
      }
      console.warn("FMIS calendar:", error);
    }
  }

  load();
  setInterval(render, 60000);
  setInterval(load, 900000);
})();
