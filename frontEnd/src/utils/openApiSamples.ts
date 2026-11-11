import type { OpenApiOperation, OpenApiSampleLang } from '@/types'

export interface SampleContext {
  baseUrl: string
  operation: OpenApiOperation
  queryValues: Record<string, string>
  bodyJson: string
  accessKey: string
  secretKey: string
}

function buildUrl(ctx: SampleContext): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(ctx.queryValues)) {
    if (value.trim()) params.set(key, value.trim())
  }
  const qs = params.toString()
  return `${ctx.baseUrl}${ctx.operation.path}${qs ? `?${qs}` : ''}`
}

function escapeJavaString(s: string): string {
  return s.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
}

function escapeCString(s: string): string {
  return s.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
}

export function generateOpenApiSample(lang: OpenApiSampleLang, ctx: SampleContext): string {
  const url = buildUrl(ctx)
  const method = ctx.operation.method.toUpperCase()
  const hasBody = method === 'PUT' || method === 'POST'
  const body = ctx.bodyJson.trim() || '{}'
  const ak = ctx.accessKey || 'YOUR_ACCESS_KEY'
  const sk = ctx.secretKey || 'YOUR_SECRET_KEY'

  switch (lang) {
    case 'python':
      return generatePython(url, method, hasBody, body, ak, sk)
    case 'java':
      return generateJava(url, method, hasBody, body, ak, sk)
    case 'curl':
      return generateCurl(url, method, hasBody, body, ak, sk)
    case 'c':
      return generateC(url, method, hasBody, body, ak, sk)
    default:
      return ''
  }
}

function generatePython(url: string, method: string, hasBody: boolean, body: string, ak: string, sk: string): string {
  const lines = [
    'import requests',
    '',
    'url = "' + url + '"',
    'headers = {',
    '    "X-Access-Key": "' + ak + '",',
    '    "X-Secret-Key": "' + sk + '",',
  ]
  if (hasBody) lines.push('    "Content-Type": "application/json",')
  lines.push('}', '')
  if (hasBody) {
    lines.push('payload = ' + body)
    lines.push('')
    lines.push(`response = requests.${method.toLowerCase()}(url, headers=headers, json=payload)`)
  } else {
    lines.push(`response = requests.${method.toLowerCase()}(url, headers=headers)`)
  }
  lines.push('print(response.status_code)')
  lines.push('print(response.json())')
  return lines.join('\n')
}

function generateJava(url: string, method: string, hasBody: boolean, body: string, ak: string, sk: string): string {
  const lines = [
    'import java.io.OutputStream;',
    'import java.net.HttpURLConnection;',
    'import java.net.URL;',
    'import java.nio.charset.StandardCharsets;',
    '',
    'public class OpenApiExample {',
    '    public static void main(String[] args) throws Exception {',
    '        URL url = new URL("' + escapeJavaString(url) + '");',
    '        HttpURLConnection conn = (HttpURLConnection) url.openConnection();',
    '        conn.setRequestMethod("' + method + '");',
    '        conn.setRequestProperty("X-Access-Key", "' + escapeJavaString(ak) + '");',
    '        conn.setRequestProperty("X-Secret-Key", "' + escapeJavaString(sk) + '");',
  ]
  if (hasBody) {
    lines.push('        conn.setRequestProperty("Content-Type", "application/json");')
    lines.push('        conn.setDoOutput(true);')
    lines.push('        byte[] body = "' + escapeJavaString(body) + '".getBytes(StandardCharsets.UTF_8);')
    lines.push('        try (OutputStream os = conn.getOutputStream()) {')
    lines.push('            os.write(body);')
    lines.push('        }')
  }
  lines.push('        int code = conn.getResponseCode();')
  lines.push('        System.out.println("HTTP " + code);')
  lines.push('        // 读取响应流 omitted for brevity')
  lines.push('    }')
  lines.push('}')
  return lines.join('\n')
}

function generateCurl(url: string, method: string, hasBody: boolean, body: string, ak: string, sk: string): string {
  const lines = [
    'curl --noproxy \'*\' \\',
    '  -X ' + method + ' \\',
    '  -H "X-Access-Key: ' + ak + '" \\',
    '  -H "X-Secret-Key: ' + sk + '" \\',
  ]
  if (hasBody) {
    lines.push('  -H "Content-Type: application/json" \\')
    lines.push("  -d '" + body.replace(/'/g, "'\\''") + "' \\")
  }
  lines.push('  "' + url + '"')
  return lines.join('\n')
}

function generateC(url: string, method: string, hasBody: boolean, body: string, ak: string, sk: string): string {
  const lines = [
    '#include <stdio.h>',
    '#include <curl/curl.h>',
    '',
    'int main(void) {',
    '    CURL *curl = curl_easy_init();',
    '    if (!curl) return 1;',
    '',
    '    struct curl_slist *headers = NULL;',
    '    headers = curl_slist_append(headers, "X-Access-Key: ' + escapeCString(ak) + '");',
    '    headers = curl_slist_append(headers, "X-Secret-Key: ' + escapeCString(sk) + '");',
  ]
  if (hasBody) {
    lines.push('    headers = curl_slist_append(headers, "Content-Type: application/json");')
  }
  lines.push('    curl_easy_setopt(curl, CURLOPT_URL, "' + escapeCString(url) + '");')
  lines.push('    curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "' + method + '");')
  lines.push('    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);')
  if (hasBody) {
    lines.push('    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, "' + escapeCString(body) + '");')
  }
  lines.push('    CURLcode res = curl_easy_perform(curl);')
  lines.push('    curl_slist_free_all(headers);')
  lines.push('    curl_easy_cleanup(curl);')
  lines.push('    return res == CURLE_OK ? 0 : 1;')
  lines.push('}')
  return lines.join('\n')
}

export function defaultQueryValues(operation: OpenApiOperation): Record<string, string> {
  const values: Record<string, string> = {}
  for (const p of operation.queryParams) {
    if (p.example) values[p.name] = p.example
  }
  return values
}

export function defaultBodyJson(operation: OpenApiOperation): string {
  if (operation.requestBodyExample) {
    return JSON.stringify(operation.requestBodyExample, null, 2)
  }
  return '{}'
}

export function resolveApiBaseUrl(): string {
  const envBase = import.meta.env.VITE_API_BASE as string | undefined
  if (envBase && envBase.startsWith('http')) return envBase.replace(/\/$/, '')
  return `${window.location.origin}${envBase || '/api'}`.replace(/\/$/, '')
}
