import request from '@/api/request'
import type { OpenApiDoc } from '@/types'

export function getOpenApiDoc() {
  return request.get<OpenApiDoc>('/api/open/doc')
}
