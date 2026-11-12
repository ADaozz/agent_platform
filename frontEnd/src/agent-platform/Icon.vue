<script setup>
import { Sun, Moon, Languages, Pencil, Presentation, Blocks, Clock, ArrowDown } from 'lucide-vue-next'
import { FileSpreadsheet, FileImage, FileCode, FileJson, FileArchive, FileVideo, FileAudio, FileType } from 'lucide-vue-next'
import { Circle, Search, Send, History, CodeXml, Plus, Folder, Settings2, ArrowLeft, SlidersHorizontal, LoaderCircle, TriangleAlert, X, Check, MessageSquare, ChevronRight, MessagesSquare, Download, Brain, CircleAlert, CircleCheck, ChevronDown, CornerDownRight, ShieldCheck, ArrowUpRight, MessageCircleQuestion, ArrowRight, Pause, Cloud, Monitor, Files, Minimize2, ImagePlus, Wrench, BookOpen, Sparkles, Paperclip, ArrowUp, AudioLines, Compass, ListTodo, FileText, GitBranch, Copy, MessageSquarePlus, Info, Terminal, Network, FileBox, Trash2, FolderOpen } from 'lucide-vue-next'
const icons = { Circle, Search, Send, History, CodeXml, Plus, Folder, Settings2, ArrowLeft, SlidersHorizontal, LoaderCircle, TriangleAlert, X, Check, MessageSquare, ChevronRight, MessagesSquare, Download, Brain, CircleAlert, CircleCheck, ChevronDown, CornerDownRight, ShieldCheck, ArrowUpRight, MessageCircleQuestion, ArrowRight, Pause, Cloud, Monitor, Files, Minimize2, ImagePlus, Wrench, BookOpen, Sparkles, Paperclip, ArrowUp, AudioLines, Compass, ListTodo, FileText, GitBranch, Copy, MessageSquarePlus, Info, Terminal, Network, FileBox, Trash2, FolderOpen }
Object.assign(icons, { Sun, Moon, Languages, Pencil, Presentation, Blocks, Clock, ArrowDown })
Object.assign(icons, { FileSpreadsheet, FileImage, FileCode, FileJson, FileArchive, FileVideo, FileAudio, FileType })
defineProps({ name: String, size: { type: Number, default: 16 } })
</script>
<template><component :is="icons[name] || icons.Circle" :size="size" :stroke-width="1.5" aria-hidden="true" /></template>
