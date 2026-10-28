
/*
 * FMIS Economic Calendar
 * Independent module — Version 1
 * No changes to existing market scoring.
 */

(function () {
  "use strict";

  const calendar = {
    events: [],
    updatedAt: null,

    setEvents(events) {
      this.events = Array.isArray(events) ? events : [];
      this.updatedAt = new Date().toISOString();
    },

    upcoming() {
      const now = Date.now();

      return this.events
        .filter(event =>
          event.impact === "High" &&
          Number.isFinite(Date.parse(event.date)) &&
          Date.parse(event.date) >= now
        )
        .sort((a, b) =>
          Date.parse(a.date) - Date.parse(b.date)
        );
    },

    render(containerId) {
      const container = document.getElementById(containerId);
      if (!container) return;

      const events = this.upcoming();

      container.replaceChildren();

      const heading = document.createElement("h2");
      heading.textContent = "Upcoming High-Impact Events";
      container.appendChild(heading);

      if (!events.length) {
        const message = document.createElement("p");
        message.textContent =
          "No upcoming events loaded. Calendar feed pending.";
        container.appendChild(message);
        return;
      }

      events.slice(0, 5).forEach(event => {
        const row = document.createElement("div");
        row.className = "row";

        const name = document.createElement("span");
        name.textContent = event.name || "Economic event";

        const time = document.createElement("strong");
        time.textContent = new Date(event.date)
          .toLocaleString("en-GB", {
            timeZone: "Europe/London",
            dateStyle: "medium",
            timeStyle: "short"
          });

        row.append(name, time);
        container.appendChild(row);
      });
    }
  };

  window.FMISCalendar = calendar;
})();
