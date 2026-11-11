// Icon and colour tone per file extension, shared by every file list in the workspace.
const TYPES = [
  { icon: 'FileText', tone: 'word', ext: ['doc', 'docx', 'odt', 'rtf'] },
  { icon: 'Presentation', tone: 'slides', ext: ['ppt', 'pptx', 'odp', 'key'] },
  { icon: 'FileSpreadsheet', tone: 'sheet', ext: ['xls', 'xlsx', 'ods', 'csv', 'tsv'] },
  { icon: 'FileType', tone: 'pdf', ext: ['pdf'] },
  { icon: 'FileImage', tone: 'image', ext: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'avif', 'ico'] },
  { icon: 'FileJson', tone: 'code', ext: ['json', 'jsonl'] },
  { icon: 'FileCode', tone: 'code', ext: ['py', 'js', 'mjs', 'ts', 'tsx', 'jsx', 'vue', 'html', 'htm', 'css', 'sh', 'sql', 'java', 'go', 'rs', 'c', 'cpp', 'yaml', 'yml', 'toml', 'xml', 'ini'] },
  { icon: 'FileText', tone: 'text', ext: ['md', 'markdown', 'txt', 'log'] },
  { icon: 'FileArchive', tone: 'archive', ext: ['zip', 'tar', 'gz', 'tgz', '7z', 'rar'] },
  { icon: 'FileVideo', tone: 'media', ext: ['mp4', 'mov', 'webm', 'mkv', 'avi'] },
  { icon: 'FileAudio', tone: 'media', ext: ['mp3', 'wav', 'm4a', 'flac', 'ogg'] },
]
const BY_EXTENSION = new Map(TYPES.flatMap(type => type.ext.map(ext => [ext, type])))
const FALLBACK = { icon: 'FileBox', tone: 'other' }

export function fileType(path = '') {
  const name = path.split('/').pop() || ''
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : ''
  return BY_EXTENSION.get(ext) || FALLBACK
}
