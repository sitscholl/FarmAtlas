import type { WorkflowWarningRead } from '../types/generated/api'

export type WorkflowMessage = {
  kind: 'warning' | 'error'
  message: string
}

export function workflowWarningKey(warning: WorkflowWarningRead) {
  return `${warning.code ?? 'warning'}-${warning.message}`
}

export function formatWorkflowWarningText(warning: WorkflowWarningRead) {
  const missingCount = warning.details?.missing_count
  const count = typeof missingCount === 'number' ? missingCount : null

  switch (warning.code) {
    case 'FORECAST_CACHE_MISSING':
      return 'Die Wettervorhersage fehlt im Cache. Aktualisiere den Wetter-Cache, um den Prognosebereich der Wasserbilanz anzuzeigen.'
    case 'WATER_BALANCE_PRECIPITATION_INCOMPLETE':
      return count === null
        ? 'Niederschlagsdaten fehlen in der Wasserbilanz. Fehlende Werte werden mit 0,0 mm angesetzt.'
        : `${count} Wetterzeilen fuer Niederschlag fehlen in der Wasserbilanz. Fehlende Werte werden mit 0,0 mm angesetzt.`
    case 'WATER_BALANCE_ET_INPUTS_INCOMPLETE':
    case 'WATER_BALANCE_ET0_INCOMPLETE':
    case 'WATER_BALANCE_ET_CORRECTED_INCOMPLETE':
    case 'WATER_BALANCE_EVAPOTRANSPIRATION_INCOMPLETE':
      return count === null
        ? 'Evapotranspirationsdaten fehlen in der Wasserbilanz. Betroffene Werte werden mit 0,0 mm angesetzt.'
        : `${count} Wetterzeilen fuer Evapotranspiration fehlen in der Wasserbilanz. Betroffene Werte werden mit 0,0 mm angesetzt.`
    case 'CROP_PROTECTION_PRECIPITATION_INCOMPLETE':
      return count === null
        ? 'Niederschlagsdaten fehlen fuer diese Pflanzenschutzregel.'
        : `${count} Wetterzeilen fuer Niederschlag fehlen fuer diese Pflanzenschutzregel.`
    case 'CROP_PROTECTION_TEMPERATURE_INCOMPLETE':
      return count === null
        ? 'Temperaturdaten fehlen fuer diese Pflanzenschutzregel.'
        : `${count} Wetterzeilen fuer Temperatur fehlen fuer diese Pflanzenschutzregel.`
    default:
      return warning.message
  }
}

export function formatWorkflowWarning(warning: WorkflowWarningRead): WorkflowMessage {
  return {
    kind: 'warning',
    message: formatWorkflowWarningText(warning),
  }
}
