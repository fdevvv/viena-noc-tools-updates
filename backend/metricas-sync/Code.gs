const METRICAS_SYNC = Object.freeze({
  spreadsheetId: '1zQ4dWZppgAc3XhgDjP55p56TQNyZBHOFqLid5HqLK0M',
  sheetName: 'ESTADOS',
  timezone: 'America/Argentina/Buenos_Aires',
  headers: ['nodo','total_marcado','problema_marcado','usuario','fecha_operativa','updated_at','updated_at_ms'],
  cleanupHour: 0,
  cleanupMinute: 10,
  lockWaitMs: 10000
});

function doGet(e) {
  try {
    const op = String((e && e.parameter && e.parameter.op) || 'GET_TODAY_STATES').trim().toUpperCase();
    if (op !== 'GET_TODAY_STATES' && op !== 'HEALTH') {
      return json_({ ok:false, error:'invalid_operation' });
    }
    if (op === 'HEALTH') {
      return json_({
        ok:true,
        service:'METRICAS_SYNC',
        date:operationalDate_(),
        timezone:METRICAS_SYNC.timezone
      });
    }
    return json_({
      ok:true,
      service:'METRICAS_SYNC',
      date:operationalDate_(),
      states:getTodayStates_()
    });
  } catch (err) {
    return json_({ ok:false, error:String(err && err.message || err) });
  }
}

function doPost(e) {
  try {
    const body = parseBody_(e);
    const op = String(body.op || '').trim().toUpperCase();
    if (op === 'UPSERT_STATE') {
      return json_(upsertState_(body));
    }
    if (op === 'DELETE_STATE') {
      return json_(deleteState_(body));
    }
    if (op === 'GET_TODAY_STATES') {
      return json_({
        ok:true,
        service:'METRICAS_SYNC',
        date:operationalDate_(),
        states:getTodayStates_()
      });
    }
    return json_({ ok:false, error:'invalid_operation' });
  } catch (err) {
    return json_({ ok:false, error:String(err && err.message || err) });
  }
}

function getTodayStates_() {
  const sheet = getSheet_();
  const today = operationalDate_();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  const values = sheet.getRange(2,1,lastRow-1,METRICAS_SYNC.headers.length).getValues();
  const latest = new Map();

  values.forEach(row => {
    const node = normalizeNode_(row[0]);
    const date = String(row[4] || '').trim();
    const updatedMs = Number(row[6] || 0);
    if (!node || date !== today) return;

    const state = {
      nodo: node,
      total_marcado: toNonNegativeInt_(row[1]),
      problema_marcado: toNonNegativeInt_(row[2]),
      usuario: normalizeUser_(row[3]),
      fecha_operativa: date,
      updated_at: String(row[5] || ''),
      updated_at_ms: updatedMs
    };

    const previous = latest.get(node);
    if (!previous || updatedMs >= previous.updated_at_ms) latest.set(node, state);
  });

  return Array.from(latest.values());
}

function upsertState_(body) {
  const node = normalizeNode_(body.nodo);
  if (!node) return { ok:false, error:'invalid_node' };

  const total = toNonNegativeInt_(body.total_marcado);
  const problem = toNonNegativeInt_(body.problema_marcado);
  const user = normalizeUser_(body.usuario);
  const today = operationalDate_();
  const now = new Date();
  const nowIso = Utilities.formatDate(now, METRICAS_SYNC.timezone, "yyyy-MM-dd'T'HH:mm:ssXXX");
  const nowMs = now.getTime();

  const lock = LockService.getScriptLock();
  lock.waitLock(METRICAS_SYNC.lockWaitMs);
  try {
    const sheet = getSheet_();
    const lastRow = sheet.getLastRow();
    let targetRow = 0;

    if (lastRow >= 2) {
      const values = sheet.getRange(2,1,lastRow-1,METRICAS_SYNC.headers.length).getValues();
      for (let i = 0; i < values.length; i++) {
        const rowNode = normalizeNode_(values[i][0]);
        const rowDate = String(values[i][4] || '').trim();
        if (rowNode === node && rowDate === today) {
          targetRow = i + 2;
          break;
        }
      }
    }

    const row = [node,total,problem,user,today,nowIso,nowMs];
    if (targetRow) {
      sheet.getRange(targetRow,1,1,row.length).setValues([row]);
    } else {
      sheet.appendRow(row);
      targetRow = sheet.getLastRow();
    }

    removeDuplicateRowsForKey_(sheet,node,today,targetRow);

    return {
      ok:true,
      state:{
        nodo:node,
        total_marcado:total,
        problema_marcado:problem,
        usuario:user,
        fecha_operativa:today,
        updated_at:nowIso,
        updated_at_ms:nowMs
      }
    };
  } finally {
    lock.releaseLock();
  }
}

function deleteState_(body) {
  const node = normalizeNode_(body.nodo);
  if (!node) return { ok:false, error:'invalid_node' };

  const today = operationalDate_();
  const lock = LockService.getScriptLock();
  lock.waitLock(METRICAS_SYNC.lockWaitMs);
  try {
    const sheet = getSheet_();
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) return { ok:true, deleted:0 };

    const values = sheet.getRange(2,1,lastRow-1,METRICAS_SYNC.headers.length).getValues();
    const toDelete = [];
    values.forEach((row,i) => {
      if (normalizeNode_(row[0]) === node && String(row[4] || '').trim() === today) {
        toDelete.push(i+2);
      }
    });

    toDelete.sort((a,b)=>b-a).forEach(r => sheet.deleteRow(r));
    return { ok:true, deleted:toDelete.length };
  } finally {
    lock.releaseLock();
  }
}

function cleanupExpiredStates() {
  const lock = LockService.getScriptLock();
  lock.waitLock(METRICAS_SYNC.lockWaitMs);
  try {
    const sheet = getSheet_();
    const today = operationalDate_();
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) return { ok:true, deleted:0 };

    const values = sheet.getRange(2,1,lastRow-1,METRICAS_SYNC.headers.length).getValues();
    const toDelete = [];

    values.forEach((row,i) => {
      const date = String(row[4] || '').trim();
      if (!date || date !== today) toDelete.push(i+2);
    });

    toDelete.sort((a,b)=>b-a).forEach(r => sheet.deleteRow(r));
    return { ok:true, deleted:toDelete.length, date:today };
  } finally {
    lock.releaseLock();
  }
}

function installDailyCleanupTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'cleanupExpiredStates')
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger('cleanupExpiredStates')
    .timeBased()
    .everyDays(1)
    .atHour(METRICAS_SYNC.cleanupHour)
    .nearMinute(METRICAS_SYNC.cleanupMinute)
    .inTimezone(METRICAS_SYNC.timezone)
    .create();

  return { ok:true };
}

function getSheet_() {
  const ss = SpreadsheetApp.openById(METRICAS_SYNC.spreadsheetId);
  let sheet = ss.getSheetByName(METRICAS_SYNC.sheetName);
  if (!sheet) sheet = ss.insertSheet(METRICAS_SYNC.sheetName);

  const current = sheet.getRange(1,1,1,METRICAS_SYNC.headers.length).getValues()[0];
  const mismatch = METRICAS_SYNC.headers.some((h,i)=>String(current[i] || '').trim() !== h);
  if (mismatch) {
    sheet.getRange(1,1,1,METRICAS_SYNC.headers.length).setValues([METRICAS_SYNC.headers]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function removeDuplicateRowsForKey_(sheet,node,date,keepRow) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return;
  const values = sheet.getRange(2,1,lastRow-1,METRICAS_SYNC.headers.length).getValues();
  const duplicates = [];
  values.forEach((row,i) => {
    const rowNumber = i+2;
    if (rowNumber === keepRow) return;
    if (normalizeNode_(row[0]) === node && String(row[4] || '').trim() === date) {
      duplicates.push(rowNumber);
    }
  });
  duplicates.sort((a,b)=>b-a).forEach(r=>sheet.deleteRow(r));
}

function operationalDate_() {
  return Utilities.formatDate(new Date(), METRICAS_SYNC.timezone, 'yyyy-MM-dd');
}

function normalizeNode_(value) {
  return String(value == null ? '' : value).trim().toUpperCase();
}

function normalizeUser_(value) {
  return String(value == null ? '' : value).trim().toLowerCase().slice(0,64);
}

function toNonNegativeInt_(value) {
  const n = parseInt(value,10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

function parseBody_(e) {
  if (!e || !e.postData || !e.postData.contents) return {};
  try {
    return JSON.parse(e.postData.contents);
  } catch (_) {
    return {};
  }
}

function json_(value) {
  return ContentService
    .createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
