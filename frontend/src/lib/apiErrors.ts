import { isAxiosError } from 'axios'

type ValidationDetailItem = {
  loc?: Array<string | number>
  msg?: string
}

type BulkMutationResult = {
  errors_by_field_id?: Record<string, string> | Record<number, string>
  skipped_field_ids?: number[]
  created_count?: number
  updated_count?: number
  unchanged_count?: number
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function formatValidationDetail(detail: ValidationDetailItem[]) {
  const messages = detail
    .map((item) => {
      if (!item.msg) {
        return null
      }

      const location = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : ''
      return location ? `${location}: ${item.msg}` : item.msg
    })
    .filter((message): message is string => Boolean(message))

  return messages.length > 0 ? messages.join(' | ') : null
}

export function getApiErrorMessage(error: unknown, fallback: string) {
  if (isAxiosError(error)) {
    const data = error.response?.data

    if (typeof data === 'string' && data.trim() !== '') {
      return data
    }

    if (isRecord(data)) {
      if (typeof data.detail === 'string' && data.detail.trim() !== '') {
        return data.detail
      }

      if (Array.isArray(data.detail)) {
        const validationMessage = formatValidationDetail(data.detail as ValidationDetailItem[])
        if (validationMessage) {
          return validationMessage
        }
      }
    }

    if (typeof error.message === 'string' && error.message.trim() !== '') {
      return error.message
    }
  }

  if (error instanceof Error && error.message.trim() !== '') {
    return error.message
  }

  return fallback
}

export function getBulkMutationMessage(data: unknown): string | null {
  if (!isRecord(data) || !isRecord(data.errors_by_field_id)) {
    return null
  }

  const entries = Object.entries(data.errors_by_field_id)
  if (entries.length === 0) {
    return null
  }

  const summary = data as BulkMutationResult
  const successCount =
    (summary.created_count ?? 0) +
    (summary.updated_count ?? 0) +
    (summary.unchanged_count ?? 0)

  const details = entries
    .map(([fieldId, message]) => `Anlage ${fieldId}: ${message}`)
    .join(' | ')

  return successCount > 0 ? `Teilweise gespeichert. ${details}` : details
}
