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
        <div style="margin-top:6px;font-size:13px">
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

      <h2 style="margin-bottom:18px">
        GOLD MARKET STRUCTURE INTELLIGENCE
      </h2>

      <div style="padding:18px;text-align:center;
                  background:#0c1525;border-radius:10px">

        <div style="color:#9daec4;font-size:13px">
          WEEKLY STRUCTURAL BIAS
        </div>

        <div style="color:${color};font-size:28px;
                    font-weight:800;margin-top:8px">
          ${goldSafe(bias)}
        </div>

      </div>

      <div style="margin-top:12px;padding:16px;
                  background:#0c1525;border-radius:10px">

        <div style="color:#9daec4;font-size:13px">
          LATEST WEEKLY BREAK OF STRUCTURE
        </div>

        <div style="color:${bosColor};font-size:22px;
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

      <div style="margin-top:12px;padding:16px;
                  background:#0c1525;border-radius:10px">
        <div style="color:#eaf1fc;font-weight:700;margin-bottom:10px">
          MONTHLY SUPPORT & RESISTANCE
        </div>
        ${zoneRows || '<div style="color:#9daec4">No confirmed monthly zones</div>'}
      </div>
      <div style="margin-top:12px;padding:16px;
                  background:#0c1525;border-radius:10px">
        <div style="color:#eaf1fc;font-weight:700;margin-bottom:10px">
          DAILY RETEST INTELLIGENCE
        </div>
        <div style="font-size:12px;color:#9daec4;margin-bottom:10px">
          Total: ${retestCount} · Confirmed: ${confirmedCount}
          (${invalidatedCount} subsequently invalidated) · Failed: ${failedCount}
        </div>
        ${retestRows || '<div style="color:#9daec4">No daily retests available</div>'}
      </div>
    </div>
  `;
}
