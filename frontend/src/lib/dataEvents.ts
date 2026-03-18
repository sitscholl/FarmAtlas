export const DATA_CHANGED_EVENT = 'irrigation-manager:data-changed'

export function notifyDataChanged() {
  window.dispatchEvent(new CustomEvent(DATA_CHANGED_EVENT))
}
