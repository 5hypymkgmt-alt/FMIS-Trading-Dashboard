// FMIS Gold Market Structure Intelligence
// Display only — does not modify trading calculations.

function goldSafe(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}

function renderGoldIntelligence(structure) {
  const weekly = structure?.weekly || {};
  const biasData = weekly.bias || {};
  const bias = biasData.bias || 'Unavailable';

  const color =
    bias === 'Bullish' ? '#29dc78' :
    bias === 'Bearish' ? '#ff3447' :
    bias === 'Neutral' ? '#ffffff' : '#9daec4';

  const bosEvents = Array.isArray(weekly.bos) ? weekly.bos : [];
  const latestBos = bosEvents.length ? bosEvents[bosEvents.length - 1] : null;

  const bosDirection = latestBos?.direction || 'unavailable';
  const bosColor =
    bosDirection === 'bullish' ? '#29dc78' :
    bosDirection === 'bearish' ? '#ff3447' : '#9daec4';

  const bosLevel = latestBos?.primary_level != null &&
    Number.isFinite(Number(latestBos.primary_level))
    ? '$' + Number(latestBos.primary_level).toFixed(2)
    : 'Unavailable';

  const bosDate = latestBos?.date || 'Unavailable';

  const monthlyZones = Array.isArray(structure?.monthly?.zones)
    ? structure.monthly.zones : [];

  const daily = structure?.daily || {};
  const dailyRetests = Array.isArray(daily.retests) ? daily.retests : [];


  // Presentation only: latest two daily retests.
  const compactRetestRows = dailyRetests.slice(-2).reverse()
    .map(retest => {
      const invalidated = retest.subsequently_invalidated === true;

      const status = invalidated ? 'INVALIDATED'
        : String(retest.status || 'unavailable')
            .replace(/_/g, ' ').toUpperCase();

      const statusColor = invalidated ? '#ff3447'
        : retest.status === 'confirmed' ? '#29dc78'
        : retest.status === 'failed' ? '#ff3447'
        : '#e8c46a';

      const level = retest.level != null &&
        Number.isFinite(Number(retest.level))
        ? '$' + Number(retest.level).toFixed(2)
        : 'Unavailable';

      const direction = String(
        retest.direction || 'unavailable'
      ).toUpperCase();

      return `
        <div class="gold-compact-row">
          <span>${goldSafe(direction)} · ${level}</span>
          <span style="color:${statusColor};font-weight:700">
            ${goldSafe(status)}
          </span>
        </div>`;
    }).join('');

  const retestRows = dailyRetests.slice(-5).reverse().map(retest => {
    const invalidated = retest.subsequently_invalidated === true;
    const status = invalidated
      ? 'CONFIRMED — LATER INVALIDATED'
      : String(retest.status || 'unavailable').replace(/_/g, ' ').toUpperCase();

    const statusColor = invalidated ? '#ff3447'
      : retest.status === 'confirmed' ? '#29dc78'
      : retest.status === 'failed' ? '#ff3447'
      : '#e8c46a';

    const level = retest.level != null &&
      Number.isFinite(Number(retest.level))
      ? '$' + Number(retest.level).toFixed(2)
      : 'Unavailable';

    const direction = String(retest.direction || 'unavailable').toUpperCase();
    const type = String(retest.retest_type || 'Not detected')
      .replace(/_/g, ' ');

    return `
      <div style="padding:12px 0;border-bottom:1px solid #344761">
        <div style="display:flex;justify-content:space-between;gap:8px">
          <strong>${goldSafe(direction)} · ${level}</strong>
          <strong style="color:${statusColor}">${goldSafe(status)}</strong>
        </div>
        <div style="font-size:12px;color:#9daec4;margin-top:7px">
          Retest: ${goldSafe(type)}
        </div>
        <div style="font-size:12px;color:#9daec4;margin-top:4px">
          Detected: ${goldSafe(retest.detected_date || 'Unavailable')}
          · Resolved: ${goldSafe(retest.resolved_date || 'Unavailable')}
        </div>
        ${invalidated ? `
          <div style="font-size:12px;color:#ff3447;margin-top:4px">
            Invalidated: ${goldSafe(retest.invalidation_date || 'Unavailable')}
          </div>` : ''}
      </div>`;
  }).join('');

  const retestCount = dailyRetests.length;
  const confirmedCount = dailyRetests.filter(
    r => r.status === 'confirmed'
  ).length;
  const failedCount = dailyRetests.filter(
    r => r.status === 'failed'
  ).length;
  const invalidatedCount = dailyRetests.filter(
    r => r.subsequently_invalidated === true
  ).length;


  // Presentation only: compact summary of existing monthly zones.
  const compactZoneRows = monthlyZones.slice(-6).reverse()
    .slice(0, 3).map(zone => {
      const type = zone.type === 'support' ? 'S'
        : zone.type === 'resistance' ? 'R' : '?';

      const zoneColor = type === 'S' ? '#29dc78'
        : type === 'R' ? '#ff3447' : '#9daec4';

      const level = zone.level != null &&
        Number.isFinite(Number(zone.level))
        ? '$' + Number(zone.level).toFixed(2)
        : 'Unavailable';

      const status = String(zone.status || 'unknown').toUpperCase();

      return `
        <div class="gold-compact-row">
          <span style="color:${zoneColor};font-weight:700">
            ${type} · ${level}
          </span>
          <span>${goldSafe(status)}</span>
        </div>`;
    }).join('');

  const zoneRows = monthlyZones.slice(-6).reverse().map(zone => {
    const type = zone.type === 'support' ? 'SUPPORT'
      : zone.type === 'resistance' ? 'RESISTANCE' : 'UNKNOWN';
    const zoneColor = type === 'SUPPORT' ? '#29dc78'
      : type === 'RESISTANCE' ? '#ff3447' : '#ffffff';
    const price = value => Number.isFinite(Number(value)) && value != null
      ? '$' + Number(value).toFixed(2) : 'Unavailable';
    const status = zone.status === 'broken' ? 'BROKEN'
      : zone.status === 'unbroken' ? 'UNBROKEN' : 'UNKNOWN';

    return `
      <div style="padding:10px 0;border-bottom:1px solid #344761">
        <div style="display:flex;justify-content:space-between;gap:8px">
          <strong style="color:${zoneColor}">${type}</strong>
          <span style="color:#eaf1fc">${status}</span>
        </div>
        <div style="margin-top:6px;font-size:12px">
          Structural level: <strong>${price(zone.level)}</strong>
        </div>
        <div style="margin-top:4px;font-size:12px;color:#9daec4">
          Zone: ${price(zone.lower)} – ${price(zone.upper)}
        </div>
        <div style="color:#9daec4;font-size:12px;margin-top:4px">
          Confirmed: ${goldSafe(zone.confirmed_at || 'Unavailable')}
        </div>
      </div>`;
  }).join('');

  return `
    <div class="fmis-gold-intelligence"
         style="padding:16px;background:#101e30;
                border:1px solid #46688f;border-radius:12px">

      <h2 style="font-size:16px;margin-bottom:12px">
        GOLD MARKET STRUCTURE INTELLIGENCE
      </h2>
      <div class="gold-structure-grid">

      <div class="gold-structure-panel" style="text-align:center;
                  background:#0c1525;border-radius:10px">

        <div style="color:#9daec4;font-size:12px">
          WEEKLY STRUCTURAL BIAS
        </div>

        <div style="color:${color};font-size:22px;
                    font-weight:800;margin-top:8px">
          ${goldSafe(bias)}
        </div>

      </div>

      <div class="gold-structure-panel">

        <div style="color:#9daec4;font-size:12px">
          LATEST WEEKLY BREAK OF STRUCTURE
        </div>

        <div style="color:${bosColor};font-size:18px;
                    font-weight:800;margin:8px 0">
          ${goldSafe(bosDirection.toUpperCase())}
        </div>

        <div class="row">
          <span>Structural level</span><b>${bosLevel}</b>
        </div>

        <div class="row">
          <span>BOS date</span><b>${goldSafe(bosDate)}</b>
        </div>

      </div>

      <div class="gold-structure-panel">
        <div style="color:#eaf1fc;font-weight:700;margin-bottom:10px">
          MONTHLY SUPPORT & RESISTANCE
        </div>
        ${compactZoneRows || '<div style="color:#9daec4">No confirmed monthly zones</div>'}

        ${monthlyZones.length ? `
          <details class="gold-structure-details">
            <summary>Show all monthly levels</summary>
            ${zoneRows}
          </details>
        ` : ''}
      </div>
      <div class="gold-structure-panel">
        <div style="color:#eaf1fc;font-weight:700;margin-bottom:10px">
          DAILY RETEST INTELLIGENCE
        </div>
        <div style="font-size:12px;color:#9daec4;margin-bottom:10px">
          Total: ${retestCount} · Confirmed: ${confirmedCount}
          (${invalidatedCount} subsequently invalidated) · Failed: ${failedCount}
        </div>
        ${compactRetestRows || '<div style="color:#9daec4">No daily retests available</div>'}

        ${dailyRetests.length ? `
          <details class="gold-structure-details">
            <summary>Show retest details</summary>
            ${retestRows}
          </details>
        ` : ''}
      </div>
      </div>
    </div>
  `;
}
