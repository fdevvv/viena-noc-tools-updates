# METRICAS_SYNC

Backend de sincronización diaria para referencias manuales de Métricas.

Spreadsheet: METRICAS_SYNC
Spreadsheet ID: 1zQ4dWZppgAc3XhgDjP55p56TQNyZBHOFqLid5HqLK0M
Hoja: ESTADOS
Timezone: America/Argentina/Buenos_Aires

Operaciones:
- GET/POST GET_TODAY_STATES
- POST UPSERT_STATE
- POST DELETE_STATE
- HEALTH
- cleanupExpiredStates
- installDailyCleanupTrigger

El estado se guarda por nodo y contiene conjuntamente total_marcado y problema_marcado.
