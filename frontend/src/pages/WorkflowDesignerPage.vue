<script setup lang="ts">
import { computed, defineAsyncComponent, markRaw, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { Background } from '@vue-flow/background'
import { VueFlow, useVueFlow, type Connection, type Edge, type Node, type NodeMouseEvent } from '@vue-flow/core'
import { MiniMap } from '@vue-flow/minimap'
import { Activity, AlertTriangle, ArrowLeft, BookOpen, Bot, Braces, BrainCircuit, Check, ChevronRight, CircleStop, Clock3, Code2, Combine, Copy, FileText, GitBranch, Globe2, History, ListChecks, ListFilter, ListTree, MousePointer2, Play, Plus, RefreshCw, Repeat2, Rocket, Save, ScanText, Search, Timer, UserCheck, Workflow, X } from 'lucide-vue-next'
import api from '@/api/client'
import { messages } from '@/i18n'
import VariableField from '@/components/VariableField.vue'
import AggregateConfigPanel from '@/components/designer/AggregateConfigPanel.vue'
import AgentConfigPanel from '@/components/designer/AgentConfigPanel.vue'
import AnnotationPlacementToolbar from '@/components/designer/AnnotationPlacementToolbar.vue'
import ClassifierConfigPanel from '@/components/designer/ClassifierConfigPanel.vue'
import ConditionConfigPanel from '@/components/designer/ConditionConfigPanel.vue'
import DesignerCommandPalette from '@/components/designer/DesignerCommandPalette.vue'
import DocumentConfigPanel from '@/components/designer/DocumentConfigPanel.vue'
import ExecutionPolicyPanel from '@/components/designer/ExecutionPolicyPanel.vue'
import HttpConfigPanel from '@/components/designer/HttpConfigPanel.vue'
import HumanConfigPanel from '@/components/designer/HumanConfigPanel.vue'
import JsonEditorField from '@/components/designer/JsonEditorField.vue'
import KnowledgeConfigPanel from '@/components/designer/KnowledgeConfigPanel.vue'
import ListOperatorConfigPanel from '@/components/designer/ListOperatorConfigPanel.vue'
import LoopConfigPanel from '@/components/designer/LoopConfigPanel.vue'
import LlmConfigPanel from '@/components/designer/LlmConfigPanel.vue'
import NextStepPanel from '@/components/designer/NextStepPanel.vue'
import NodeActionMenu, { type NodeAction } from '@/components/designer/NodeActionMenu.vue'
import NodeInputPanel from '@/components/designer/NodeInputPanel.vue'
import NodeOutputPanel from '@/components/designer/NodeOutputPanel.vue'
import NodePalette from '@/components/designer/NodePalette.vue'
import ParameterExtractorConfigPanel from '@/components/designer/ParameterExtractorConfigPanel.vue'
import PublishPopover from '@/components/designer/PublishPopover.vue'
import RunDebugPanel from '@/components/designer/RunDebugPanel.vue'
import RunHistoryPopover from '@/components/designer/RunHistoryPopover.vue'
import SelectionToolbar from '@/components/designer/SelectionToolbar.vue'
import SubworkflowConfigPanel from '@/components/designer/SubworkflowConfigPanel.vue'
import TemplateConfigPanel from '@/components/designer/TemplateConfigPanel.vue'
import IterationConfigPanel from '@/components/designer/IterationConfigPanel.vue'
import VariableAssignConfigPanel from '@/components/designer/VariableAssignConfigPanel.vue'
import WorkflowCommentPin from '@/components/designer/WorkflowCommentPin.vue'
import WorkflowCommentsPanel from '@/components/designer/WorkflowCommentsPanel.vue'
import WorkflowCanvasControls from '@/components/designer/WorkflowCanvasControls.vue'
import WorkflowDesignerSidebar, { type DesignerSection } from '@/components/designer/WorkflowDesignerSidebar.vue'
import WorkflowNodeInspector, { type InspectorTab } from '@/components/designer/WorkflowNodeInspector.vue'
import WorkflowEnvironmentPanel, { type WorkflowEnvironmentVariable } from '@/components/designer/WorkflowEnvironmentPanel.vue'
import WorkflowSystemVariablesPanel from '@/components/designer/WorkflowSystemVariablesPanel.vue'
import WorkflowSaveStatus from '@/components/designer/WorkflowSaveStatus.vue'
import AlertBanner from '@/components/ui/AlertBanner.vue'
import MarkdownComposer from '@/components/ui/MarkdownComposer.vue'
import ModalShell from '@/components/ui/ModalShell.vue'
import WorkflowEdge from '@/components/WorkflowEdge.vue'
import WorkflowContainerNode from '@/components/WorkflowContainerNode.vue'
import WorkflowNode from '@/components/WorkflowNode.vue'
import WorkflowNoteNode from '@/components/WorkflowNoteNode.vue'
import { useAuthStore } from '@/stores/auth'
import { usePreferencesStore } from '@/stores/preferences'
import { useWorkspacesStore } from '@/stores/workspaces'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Textarea from '@/volt/Textarea.vue'
import { clearWorkflowEdgeSelection, findAvailableNodePosition, insertNodeOnEdge, isConnectionAllowed, layoutWorkflow, mergeWorkflowEdges, removeWorkflowEdgeById, replaceWorkflowNode, validateWorkflowGraph, type WorkflowValidationIssue } from '@/utils/workflowGraph'
import { coerceWorkflowInputValues, createWorkflowInputValues } from '@/utils/workflowInputs'
import { buildRunOverlay, clearRunOverlay as clearGraphRunOverlay, stripRuntimeData } from '@/utils/workflowRunOverlay'
import { allocateDefaultNodeName, ensureUniqueNodeNames, nextUniqueNodeName, nodeReferenceName, rewriteNodeReferences, validateNodeName, type NodeNameError, type NodeRename } from '@/utils/workflowNodeNames'
import { buildAllVariableCatalog, buildVariableCatalog, readRuntimeVariable } from '@/utils/workflowVariables'
import { normalizeWorkflowComments, type WorkflowCommentThread } from '@/types/workflowComments'
import { SYSTEM_VARIABLES } from '@/types/workflowSystemVariables'

const { t } = useI18n()
const CodeConfigPanel = defineAsyncComponent(() => import('@/components/designer/CodeConfigPanel.vue'))
const route = useRoute(); const router = useRouter()
const auth = useAuthStore(); const preferences = usePreferencesStore(); const workspaces = useWorkspacesStore()
const { addNodes, addSelectedNodes, fitView, getNodes, onConnect, removeSelectedNodes, screenToFlowCoordinate, setCenter, viewport, zoomIn, zoomOut } = useVueFlow()
const workflow = ref<any>(null); const nodes = ref<Node[]>([]); const edges = ref<Edge[]>([])
const selected = ref<Node | null>(null); const saving = ref(false); const running = ref(false); const publishing = ref(false)
const result = ref<any>(null); const inspectorTab = ref<InspectorTab>('settings'); const paletteOpen = ref(false)
const paletteSourceId = ref<string | null>(null)
const paletteSourceHandle = ref<string | null>(null)
const paletteEdgeId = ref<string | null>(null)
const paletteParentId = ref<string | null>(null)
const paletteReplaceNodeId = ref<string | null>(null)
const paletteQuery = ref(''); const configText = ref('{}'); const configError = ref('')
const paletteTab = ref<'nodes' | 'tools' | 'snippets'>('nodes')
const palettePosition = ref({ x: 64, y: 80 })
const interactionMode = ref<'pointer' | 'hand'>('pointer')
const middlePanning = ref(false)
const showCommandPalette = ref(false)
const annotationMode = ref(false); const annotationColor = ref('yellow')
const commentMode = ref(false); const showComments = ref(false); const selectedCommentId = ref<string | null>(null)
const comments = ref<WorkflowCommentThread[]>([])
const canvasHost = ref<HTMLElement | null>(null); const nodeContextMenu = ref<{ nodeId: string; x: number; y: number } | null>(null)
const loaded = ref(false); const saveError = ref(''); const saveConflict = ref(false); const lastSavedAt = ref<Date | null>(null)
const dirty = ref(false); const editRevision = ref(0)
const activeSection = ref<DesignerSection>('orchestration'); const versions = ref<any[]>([]); const runs = ref<any[]>([]); const showHistory = ref(false); const showHelp = ref(false)
const showChecklist = ref(false); const showChangeHistory = ref(false); const showPublish = ref(false); const pendingRestoreVersion = ref<any>(null); const restoringVersion = ref(false)
const showRunDialog = ref(false); const runInputs = ref<Record<string, any>>({}); const runError = ref(''); const uploadingField = ref('')
const sidebarCollapsed = ref(false); const showRunHistory = ref(false); const selectedRun = ref<any>(null)
const expandedStartFieldIndex = ref<number | null>(null)
const showVariableInspector = ref(false); const variableSearch = ref(''); const copiedVariablePath = ref('')
const runTargetNodeId = ref<string | null>(null); const nodeResults = ref<Record<string, any>>({})
const runtimeRunId = ref('')
const replayMode = computed(() => Boolean(runtimeRunId.value && selectedRun.value))
const approvals = ref<any[]>([]); const selectedApproval = ref<any>(null); const showApprovals = ref(false); const approvalComment = ref(''); const respondingApproval = ref(false)
const modelProviders = ref<any[]>([]); const scripts = ref<any[]>([]); const datasets = ref<any[]>([]); const subworkflows = ref<any[]>([])
const environmentVariables = ref<WorkflowEnvironmentVariable[]>([]); const showEnvironment = ref(false); const environmentSaving = ref(false); const environmentError = ref('')
const showSystemVariables = ref(false)
const environmentPanel = ref<{ markSaved: () => void } | null>(null)
const configBuffers = ref({ scriptInputs: '{}', values: '{}', jsonValue: '{}', httpHeaders: '{}', httpQuery: '{}', httpBody: '', llmSchema: '{}' })
const configFieldErrors = ref<Record<string, string>>({}); const configEditing = ref(false)
const nodeNameError = ref('')
type GraphState = { nodes: any[]; edges: any[]; comments?: WorkflowCommentThread[] }
const graphHistory = ref<GraphState[]>([]); const historyIndex = ref(-1); const copiedGraph = ref<GraphState | null>(null)
const historyTimes = ref<Date[]>([])
const workspaceId = computed(() => String(route.params.workspaceId)); const workflowId = computed(() => String(route.params.workflowId))
const origin = window.location.origin
const selectedType = computed(() => String(selected.value?.data?.nodeType || selected.value?.type || ''))
const environmentVariableGroup = computed(() => ({ nodeId: 'env', label: t('designer.environmentVariables'), variables: environmentVariables.value.map(variable => ({ path: `env.${variable.name}`, label: variable.description || variable.name, type: variable.value_type === 'number' ? 'Number' : 'String' })) }))
const systemVariableGroup = computed(() => ({ nodeId: 'sys', label: t('designer.systemVariables'), variables: SYSTEM_VARIABLES.map(variable => ({ path: `sys.${variable.name}`, label: t(`designer.systemVariableDescriptions.${variable.name}`), type: variable.type })) }))
const globalVariableGroups = computed(() => [systemVariableGroup.value, ...(environmentVariables.value.length ? [environmentVariableGroup.value] : [])])
const variableGroups = computed(() => selected.value ? [...globalVariableGroups.value, ...buildVariableCatalog(nodes.value as any[], currentCanvasEdges() as any[], selected.value.id)] : [])
const allVariableGroups = computed(() => [...globalVariableGroups.value, ...buildAllVariableCatalog(nodes.value as any[])])
const filteredVariableGroups = computed(() => {
  const query = variableSearch.value.trim().toLocaleLowerCase()
  if (!query) return allVariableGroups.value
  return allVariableGroups.value.map(group => ({ ...group, variables: group.variables.filter(variable => `${group.label} ${variable.label} ${variable.path} ${variable.type}`.toLocaleLowerCase().includes(query)) })).filter(group => group.variables.length)
})
const startNode = computed<any>(() => (nodes.value as any[]).find(node => String(node.data?.nodeType || node.type) === 'start'))
const startFields = computed<any[]>(() => startNode.value?.data?.config?.input_fields || [])
const selectedScript = computed<any>(() => scripts.value.find(item => item.id === selected.value?.data?.config?.script_id))
const selectedResult = computed<any>(() => selected.value ? nodeResults.value[selected.value.id] : null)
const runTargetLabel = computed(() => (nodes.value as any[]).find(node => node.id === runTargetNodeId.value)?.data?.label || '')
const runNodeLabels = computed<Record<string, string>>(() => Object.fromEntries(
  (nodes.value as any[]).map(node => [node.id, String(node.data?.label || node.id)]),
))
const pendingApprovals = computed(() => approvals.value.filter(item => item.status === 'pending'))
const nextNodes = computed<any[]>(() => {
  if (!selected.value) return []
  const targets = new Set((currentCanvasEdges() as any[]).filter(edge => edge.source === selected.value!.id).map(edge => edge.target))
  return (nodes.value as any[]).filter(node => targets.has(node.id))
})
const canUndo = computed(() => historyIndex.value > 0); const canRedo = computed(() => historyIndex.value < graphHistory.value.length - 1)
const zoomPercent = computed(() => Math.round(viewport.value.zoom * 100))
const paletteStyle = computed(() => ({ left: `${palettePosition.value.x}px`, top: `${palettePosition.value.y}px` }))
const validationIssues = computed(() => validateWorkflowGraph(nodes.value as any[], currentCanvasEdges() as any[]))
const actionableSelectionCount = computed(() => selectedCanvasNodes().length)
const visibleCommentPins = computed(() => comments.value.map((comment, index) => ({ comment, index: index + 1 })))
const contextMenuProtected = computed(() => {
  const node = nodeContextMenu.value ? (nodes.value as any[]).find(item => item.id === nodeContextMenu.value?.nodeId) : null
  return ['start', 'end'].includes(String(node?.data?.nodeType || node?.type || ''))
})
const contextMenuCanChange = computed(() => {
  const node = nodeContextMenu.value ? (nodes.value as any[]).find(item => item.id === nodeContextMenu.value?.nodeId) : null
  return !['iteration', 'loop'].includes(String(node?.data?.nodeType || node?.type || ''))
})
const saveState = computed<'idle' | 'dirty' | 'saving' | 'saved' | 'error' | 'conflict'>(() => {
  if (saving.value) return 'saving'
  if (saveError.value) return saveConflict.value ? 'conflict' : 'error'
  if (dirty.value) return 'dirty'
  return lastSavedAt.value ? 'saved' : 'idle'
})
const localHistoryEntries = computed(() => graphHistory.value.map((state, index) => ({ state, index, time: historyTimes.value[index] })).reverse())
const nodeTypes = { ...Object.fromEntries(['start', 'end', 'default', 'llm', 'agent', 'classifier', 'code', 'script', 'template', 'variable', 'json', 'aggregate', 'extract', 'list', 'knowledge', 'http', 'condition', 'human', 'delay', 'subworkflow', 'document'].map(type => [type, markRaw(WorkflowNode)])), iteration: markRaw(WorkflowContainerNode), loop: markRaw(WorkflowContainerNode), note: markRaw(WorkflowNoteNode) }
const edgeTypes = { workflow: markRaw(WorkflowEdge) }
const paletteSections = computed(() => {
  const query = paletteQuery.value.trim().toLocaleLowerCase()
  const sections = [
    { key: 'ai', items: [{ type: 'agent', icon: BrainCircuit }, { type: 'llm', icon: Bot }, { type: 'knowledge', icon: BookOpen }, { type: 'end', icon: CircleStop }, { type: 'classifier', icon: ListFilter }] },
    { key: 'data', items: [{ type: 'template', icon: FileText }, { type: 'variable', icon: ListTree }, { type: 'json', icon: Code2 }, { type: 'aggregate', icon: Combine }, { type: 'extract', icon: ScanText }, { type: 'list', icon: ListFilter }] },
    { key: 'tools', items: [{ type: 'code', icon: Code2 }, { type: 'script', icon: Braces }, { type: 'http', icon: Globe2 }, { type: 'document', icon: FileText }] },
    { key: 'logic', items: [{ type: 'condition', icon: GitBranch }, { type: 'human', icon: UserCheck }, { type: 'iteration', icon: Repeat2 }, { type: 'loop', icon: RefreshCw }, { type: 'subworkflow', icon: Workflow }, { type: 'delay', icon: Timer }] },
  ]
  return sections.map(section => ({ ...section, items: section.items.filter(item => {
    if (paletteParentId.value && ['iteration', 'loop'].includes(item.type)) return false
    return !query || `${t(`workflow.nodes.${item.type}`)} ${t(`designer.nodeDescriptions.${item.type}`)}`.toLocaleLowerCase().includes(query)
  }) })).filter(section => section.items.length)
})
const commandAddItems = computed(() => paletteSections.value.flatMap(section => section.items.map(item => ({ type: item.type, label: t(`workflow.nodes.${item.type}`), description: t(`designer.nodeDescriptions.${item.type}`) }))))
const commandActions = computed(() => [
  { id: 'run', label: t('designer.commandActions.run'), shortcut: 'Alt R' },
  { id: 'save', label: t('designer.commandActions.save'), shortcut: 'Ctrl S' },
  { id: 'publish', label: t('designer.commandActions.publish') },
  { id: 'layout', label: t('designer.commandActions.layout') },
  { id: 'history', label: t('designer.commandActions.history') },
  { id: 'variables', label: t('designer.commandActions.variables') },
])
let saveTimer: ReturnType<typeof setTimeout> | undefined
let historyTimer: ReturnType<typeof setTimeout> | undefined
let activeSave: Promise<boolean> | null = null
let restoringHistory = false
let pendingSourceConnection: { sourceId: string; sourceHandle?: string } | null = null
const executionPolicyNodeTypes = new Set(['llm', 'agent', 'code', 'script', 'template', 'variable', 'json', 'aggregate', 'extract', 'list', 'knowledge', 'http', 'iteration', 'loop', 'delay', 'subworkflow', 'document'])

function defaultNodeConfig(type: string) {
  const defaults: Record<string, any> = {
    end: { outputs: [{ name: 'result', type: 'Any', value: '' }] },
    llm: { provider_id: '', model: '', temperature: 0.7, top_p: 1, max_tokens: 1024, messages: [{ role: 'system', content: '' }, { role: 'user', content: '{{inputs.message}}' }], prompt: '', context: '', vision: { enabled: false, variable: '', detail: 'high' }, reasoning: { separate: false }, response_format: 'text', response_schema: { type: 'object', properties: {} } },
    agent: { provider_id: '', model: '', strategy: 'tool_calling', instructions: '', query: '{{inputs.message}}', tools: [], max_iterations: 5, memory: { enabled: false, window: 10 }, return_intermediate_steps: false },
    classifier: { input: '{{inputs.message}}', categories: [createClassifierCategory(), createClassifierCategory()] },
    code: { inputs: [{ name: 'message', type: 'String', value: '{{inputs.message}}' }], source: 'def main(inputs, context):\n    message = inputs.get("message", "")\n    return {"result": message}', entrypoint: 'main', outputs: [{ name: 'result', type: 'String' }], timeout_seconds: 30, memory_mb: 256, network_enabled: false },
    script: { script_id: '', version: 'latest', inputs: {} },
    template: { inputs: [{ name: 'arg1', value: '' }], template: '' },
    variable: { assignments: [] },
    json: { value: {} },
    aggregate: { variables: [''], group_enabled: false, groups: [] },
    extract: { provider_id: '', model: '', source: '{{inputs.message}}', fields: [{ name: '', type: 'String', description: '', required: false }], instruction: '', vision: { enabled: false, variable: '' } },
    list: { source: '', filter: { enabled: false, field: '', operator: 'equals', value: '' }, nth: { enabled: false, index: 1 }, limit: { enabled: false, count: 10 }, sort: { enabled: false, order: 'asc', key: '' }, unique: false },
    knowledge: { dataset_id: '', dataset_ids: [], query: '{{inputs.message}}', retrieval_mode: 'hybrid', rerank: { mode: 'weighted', semantic_weight: 0.7, model_name: '' }, top_k: 5, threshold: 0.2, score_threshold: { enabled: false, value: 0.2 }, metadata_filter: { enabled: false, logical_operator: 'and', conditions: [] } },
    http: { method: 'GET', url: '', timeout_seconds: 30, max_response_bytes: 2000000, follow_redirects: false, query: {}, headers: {}, auth: { type: 'none', token: '', username: '', password: '', key: '', value: '', location: 'header' }, body_type: 'json', body: {} },
    condition: { logical_operator: 'and', conditions: [{ variable: '', operator: 'equals', value: '' }], expression: '' },
    human: { submission_methods: ['studio'], form_content: '', actions: [{ id: 'approve', label: t('designer.approve'), value: 'approved', style: 'primary' }, { id: 'reject', label: t('designer.reject'), value: 'rejected', style: 'danger' }], timeout_minutes: 4320 },
    iteration: { source: '', item_variable: 'item', output: '', mode: 'sequential', concurrency: 1 },
    loop: { condition: '', max_iterations: 10, output: '' },
    delay: { seconds: 60 },
    subworkflow: { workflow_id: '', inputs: {} },
    document: { operation: 'extract', source: '{{inputs.file}}', extract_mode: 'text', page_range: '', ocr_fallback: true },
  }
  const value = structuredClone(defaults[type] || {})
  if (executionPolicyNodeTypes.has(type)) Object.assign(value, {
    retry: { enabled: false, max_retries: 3, interval_seconds: 0 },
    error_strategy: 'fail',
    default_output: {},
  })
  return value
}

function normalizeExecutionPolicy(type: string, config: any) {
  if (!executionPolicyNodeTypes.has(type)) return config
  return {
    ...config,
    retry: { enabled: false, max_retries: 3, interval_seconds: 0, ...(config?.retry || {}) },
    error_strategy: config?.error_strategy || 'fail',
    default_output: config?.default_output && typeof config.default_output === 'object' && !Array.isArray(config.default_output) ? config.default_output : {},
  }
}

function createClassifierCategory(category: any = {}) {
  return {
    id: category.id || crypto.randomUUID().slice(0, 12),
    name: '',
    description: '',
    keywords: [],
    ...category,
  }
}

function normalizeClassifierConfig(config: any) {
  const normalized = { ...defaultNodeConfig('classifier'), ...(config || {}) }
  const seen = new Set<string>()
  normalized.categories = (Array.isArray(config?.categories) ? config.categories : normalized.categories).map((category: any) => {
    const next = createClassifierCategory(category)
    if (!next.id || seen.has(next.id)) next.id = crypto.randomUUID().slice(0, 12)
    seen.add(next.id)
    next.keywords = Array.isArray(next.keywords) ? next.keywords : String(next.keywords || '').split(',').map((item: string) => item.trim()).filter(Boolean)
    return next
  })
  return normalized
}

function classifierBranchLabel(node: any, sourceHandle: string | null | undefined) {
  if (!String(sourceHandle || '').startsWith('category:')) return ''
  const categoryId = String(sourceHandle).slice('category:'.length)
  return node?.data?.config?.categories?.find((category: any) => category.id === categoryId)?.name || ''
}

function syncClassifierEdgeLabels() {
  const nodeById = new Map((nodes.value as any[]).map(node => [node.id, node]))
  commitEdges(currentCanvasEdges().map(edge => {
    const label = classifierBranchLabel(nodeById.get(edge.source), edge.sourceHandle)
    if (!label || edge.data?.branchLabel === label) return edge
    return { ...edge, data: { ...(edge.data || {}), branchLabel: label } }
  }) as Edge[])
}

function normalizeEndOutputs(outputs: any, inputFields: any[]) {
  if (Array.isArray(outputs)) return outputs.map(output => ({ type: 'Any', ...output }))
  if (outputs && typeof outputs === 'object') {
    return Object.entries(outputs).map(([name, value]) => ({ name, type: 'Any', value }))
  }
  if (typeof outputs === 'string' && /^\{\{\s*inputs\s*\}\}$/.test(outputs)) {
    return inputFields.map(field => ({
      name: field.name,
      type: field.type === 'number' ? 'Number' : field.type === 'file' ? 'File' : field.type === 'files' ? 'Array' : 'String',
      value: `{{inputs.${field.name}}}`,
    }))
  }
  return [{ name: 'result', type: 'Any', value: outputs ?? '' }]
}

function normalizeStartField(field: any) {
  return {
    name: '', label: '', type: 'text', required: false, placeholder: '', default_value: '',
    max_length: null, min: null, max: null, options: [], ...field,
  }
}

function normalizeConditionConfig(config: any) {
  const normalized = { ...defaultNodeConfig('condition'), ...(config || {}) }
  if (Array.isArray(config?.conditions)) normalized.conditions = config.conditions
  else if (String(config?.expression || '').trim()) normalized.conditions = []
  return normalized
}

function normalizeLlmConfig(config: any) {
  const normalized = { ...defaultNodeConfig('llm'), ...(config || {}) }
  normalized.vision = { enabled: false, variable: '', detail: 'high', ...(config?.vision || {}) }
  normalized.reasoning = { separate: false, ...(config?.reasoning || {}) }
  if (Array.isArray(config?.messages) && config.messages.length) normalized.messages = config.messages
  else if (String(config?.prompt || '').trim()) normalized.messages = [{ role: 'user', content: config.prompt }]
  return normalized
}

function normalizeHumanConfig(config: any) {
  const normalized = { ...defaultNodeConfig('human'), ...(config || {}) }
  normalized.form_content = config?.form_content || config?.instructions || ''
  normalized.submission_methods = Array.isArray(config?.submission_methods) && config.submission_methods.length ? config.submission_methods : ['studio']
  normalized.actions = Array.isArray(config?.actions) && config.actions.length ? config.actions : defaultNodeConfig('human').actions
  return normalized
}

function renameNodesAndReferences(currentNodes: any[], renames: NodeRename[]) {
  if (!renames.length) return currentNodes
  const references = renames.filter(rename => rename.from && currentNodes.filter(node => nodeReferenceName(node) === rename.from).length === 1)
  return currentNodes.map(node => {
    const rename = renames.find(item => item.id === node.id)
    return {
      ...node,
      data: {
        ...node.data,
        ...(rename ? { label: rename.to } : {}),
        config: rewriteNodeReferences(node.data?.config || {}, references),
      },
    }
  })
}

function replaceReferences(currentNodes: any[], renames: Array<Pick<NodeRename, 'from' | 'to'>>) {
  return currentNodes.map(node => ({
    ...node,
    data: { ...node.data, config: rewriteNodeReferences(node.data?.config || {}, renames) },
  }))
}

function startReferenceName(currentNodes: any[] = nodes.value as any[]) {
  const start = currentNodes.find(node => String(node.data?.nodeType || node.type) === 'start')
  return start ? nodeReferenceName(start) : t('workflow.nodes.start')
}

function withNamedStartReferences<T>(value: T, currentNodes: any[] = nodes.value as any[]): T {
  return rewriteNodeReferences(value, [{ from: 'inputs', to: startReferenceName(currentNodes) }])
}

function nodeNameErrorText(error: NodeNameError) {
  return t(`designer.nodeNameErrors.${error}`)
}

function updateSelectedNodeLabel(value: string) {
  if (!selected.value) return
  const name = value.trim()
  const error = validateNodeName(nodes.value as any[], selected.value.id, name)
  if (error) {
    nodeNameError.value = nodeNameErrorText(error)
    return
  }
  const oldName = nodeReferenceName(selected.value as any)
  nodeNameError.value = ''
  if (oldName === name) return
  const renamed = renameNodesAndReferences(nodes.value as any[], [{ id: selected.value.id, from: oldName, to: name }])
  nodes.value = renamed as Node[]
  selected.value = (renamed.find(node => node.id === selected.value!.id) || null) as Node | null
  syncConfigEditor()
}

function currentCanvasEdges() {
  return edges.value as Edge[]
}

function graphSnapshot() {
  const persisted = {
    nodes: (nodes.value as any[]).map(node => ({
      id: node.id,
      type: node.type,
      position: node.position,
      parentNode: node.parentNode,
      extent: node.extent,
      expandParent: node.expandParent,
      style: node.style,
      data: stripRuntimeData(node.data),
    })),
    edges: currentCanvasEdges().map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edge.type,
      sourceHandle: edge.sourceHandle,
      targetHandle: edge.targetHandle,
      data: stripRuntimeData(edge.data),
    })),
    comments: comments.value.filter(comment => comment.messages.length).map(comment => structuredClone(comment)),
  }
  return JSON.parse(JSON.stringify(persisted)) as GraphState
}
function pushHistory() {
  if (!loaded.value || restoringHistory) return
  const snapshot = graphSnapshot(); const serialized = JSON.stringify(snapshot)
  if (JSON.stringify(graphHistory.value[historyIndex.value]) === serialized) return
  graphHistory.value = [...graphHistory.value.slice(0, historyIndex.value + 1), snapshot].slice(-60)
  historyTimes.value = [...historyTimes.value.slice(0, historyIndex.value + 1), new Date()].slice(-60)
  historyIndex.value = graphHistory.value.length - 1
}
function resetHistory() { graphHistory.value = [graphSnapshot()]; historyTimes.value = [new Date()]; historyIndex.value = 0 }
function restoreHistory(index: number) {
  const snapshot = graphHistory.value[index]
  if (!snapshot) return
  restoringHistory = true
  nodes.value = JSON.parse(JSON.stringify(snapshot.nodes)); commitEdges(JSON.parse(JSON.stringify(snapshot.edges))); comments.value = normalizeWorkflowComments(snapshot.comments); historyIndex.value = index; selected.value = null; selectedCommentId.value = null
  setTimeout(() => { restoringHistory = false }, 0)
}
function undo() { clearTimeout(historyTimer); pushHistory(); if (canUndo.value) restoreHistory(historyIndex.value - 1) }
function redo() { clearTimeout(historyTimer); if (canRedo.value) restoreHistory(historyIndex.value + 1) }

async function load() {
  loaded.value = false
  const { data } = await api.get(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}`)
  workflow.value = data
  const draftStart = data.draft_graph.nodes.find((node: any) => String(node.data?.nodeType || node.type) === 'start')
  const draftInputFields = draftStart?.data?.config?.input_fields || []
  const localizedRenames: NodeRename[] = []
  let loadedNodes = data.draft_graph.nodes.map((node: Node) => {
    const nodeType = String(node.data?.nodeType || node.type)
    const defaults: Record<string, string[]> = { start: ['Start', '开始'], end: ['End', '结束'] }
    const baseConfig = nodeType === 'start' ? {
      triggers: [node.data?.config?.triggers?.[0] || 'form'],
      input_fields: (node.data?.config?.input_fields || [{ name: 'message', label: t('designer.defaultMessage'), type: 'text', required: false, placeholder: '' }]).map(normalizeStartField),
      schedule: { cron: '0 9 * * *', timezone: 'UTC', enabled: false, inputs_json: '{}', ...(node.data?.config?.schedule || {}) },
    } : nodeType === 'end' ? {
      ...defaultNodeConfig(nodeType),
      ...(node.data?.config || {}),
      outputs: normalizeEndOutputs(node.data?.config?.outputs, draftInputFields),
    } : nodeType === 'condition' ? normalizeConditionConfig(node.data?.config) : nodeType === 'classifier' ? normalizeClassifierConfig(node.data?.config) : nodeType === 'llm' ? normalizeLlmConfig(node.data?.config) : nodeType === 'human' ? normalizeHumanConfig(node.data?.config) : { ...defaultNodeConfig(nodeType), ...(node.data?.config || {}) }
    const config = normalizeExecutionPolicy(nodeType, baseConfig)
    const label = defaults[nodeType]?.includes(String(node.data?.label)) ? t(`workflow.nodes.${nodeType}`) : node.data?.label
    if (String(node.data?.label || '').trim() && String(node.data?.label).trim() !== String(label || '').trim()) localizedRenames.push({ id: node.id, from: String(node.data?.label).trim(), to: String(label || '').trim() })
    return {
      id: node.id,
      type: node.type,
      position: node.position,
      parentNode: (node as any).parentNode,
      extent: (node as any).extent,
      expandParent: (node as any).expandParent,
      style: (node as any).style,
      data: { ...node.data, config, nodeType, label },
    }
  })
  loadedNodes = replaceReferences(loadedNodes, localizedRenames)
  const uniqueNames = ensureUniqueNodeNames(loadedNodes, (node: any) => t(`workflow.nodes.${String(node.data?.nodeType || node.type || 'default')}`))
  loadedNodes = uniqueNames.nodes
  const beforeReferenceMigration = JSON.stringify(loadedNodes.map((node: any) => node.data?.config || {}))
  loadedNodes = replaceReferences(loadedNodes, [{ from: 'inputs', to: startReferenceName(loadedNodes) }])
  const migrated = Boolean(localizedRenames.length || uniqueNames.renames.length || beforeReferenceMigration !== JSON.stringify(loadedNodes.map((node: any) => node.data?.config || {})))
  nodes.value = loadedNodes as Node[]
  const loadedEdges = data.draft_graph.edges.map((edge: Edge) => ({ ...edge, type: 'workflow' }))
  commitEdges(loadedEdges)
  comments.value = normalizeWorkflowComments(data.draft_graph.comments)
  syncClassifierEdgeLabels()
  runtimeRunId.value = ''; nodeResults.value = {}
  resetHistory()
  await nextTick()
  editRevision.value = 0; dirty.value = false; saveError.value = ''; saveConflict.value = false
  loaded.value = true; lastSavedAt.value = new Date()
  if (migrated) { dirty.value = true; scheduleSave() }
  setTimeout(() => fitView({ padding: 0.2 }), 80)
}
async function loadResources() {
  const [modelsResponse, scriptsResponse, datasetsResponse, workflowsResponse] = await Promise.allSettled([
    api.get(`/workspaces/${workspaceId.value}/models`),
    api.get(`/workspaces/${workspaceId.value}/scripts`),
    api.get(`/workspaces/${workspaceId.value}/knowledge`),
    api.get(`/workspaces/${workspaceId.value}/workflows`),
  ])
  modelProviders.value = modelsResponse.status === 'fulfilled' ? modelsResponse.value.data : []
  scripts.value = scriptsResponse.status === 'fulfilled' ? scriptsResponse.value.data : []
  datasets.value = datasetsResponse.status === 'fulfilled' ? datasetsResponse.value.data : []
  subworkflows.value = workflowsResponse.status === 'fulfilled' ? workflowsResponse.value.data.filter((item: any) => item.id !== workflowId.value) : []
}
async function loadEnvironmentVariables() {
  environmentVariables.value = (await api.get(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/environment-variables`)).data
}
async function createEnvironmentVariable(payload: { name: string; value_type: string; value: string; description: string }) {
  environmentSaving.value = true; environmentError.value = ''
  try { await api.post(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/environment-variables`, payload); await loadEnvironmentVariables(); environmentPanel.value?.markSaved() }
  catch (cause: any) { environmentError.value = cause.response?.data?.detail || String(cause) }
  finally { environmentSaving.value = false }
}
async function updateEnvironmentVariable(payload: { id: string; name: string; value_type: string; value?: string; description: string }) {
  environmentSaving.value = true; environmentError.value = ''
  const { id, ...body } = payload
  try { await api.put(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/environment-variables/${id}`, body); await loadEnvironmentVariables(); environmentPanel.value?.markSaved() }
  catch (cause: any) { environmentError.value = cause.response?.data?.detail || String(cause) }
  finally { environmentSaving.value = false }
}
async function deleteEnvironmentVariable(variableId: string) {
  environmentError.value = ''
  try { await api.delete(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/environment-variables/${variableId}`); await loadEnvironmentVariables() }
  catch (cause: any) { environmentError.value = cause.response?.data?.detail || String(cause) }
}
async function performSave() {
  const revisionAtStart = editRevision.value
  const snapshot = graphSnapshot()
  saving.value = true; saveError.value = ''; saveConflict.value = false
  try {
    const { data } = await api.put(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}`, {
      name: workflow.value.name,
      graph: { schema_version: 1, ...snapshot },
      expected_version: workflow.value.draft_version,
    })
    workflow.value = data; lastSavedAt.value = new Date()
    dirty.value = editRevision.value !== revisionAtStart
    if (dirty.value) scheduleSave()
    return true
  } catch (cause: any) {
    saveConflict.value = cause.response?.status === 409
    saveError.value = cause.response?.data?.detail || String(cause)
    dirty.value = true
    return false
  }
  finally { saving.value = false }
}
async function save(): Promise<boolean> {
  if (!loaded.value) return false
  while (activeSave) {
    if (!await activeSave) return false
  }
  if (!dirty.value) return true
  const attempt = performSave()
  activeSave = attempt
  try {
    if (!await attempt) return false
  } finally {
    if (activeSave === attempt) activeSave = null
  }
  return dirty.value ? save() : true
}
function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(() => { void save() }, 1000) }
async function reloadDraftAfterConflict() {
  if (!window.confirm(t('designer.reloadConflictConfirm'))) return
  clearTimeout(saveTimer)
  await load()
}
function handleBeforeUnload(event: BeforeUnloadEvent) {
  if (!dirty.value && !saving.value) return
  event.preventDefault()
  event.returnValue = ''
}
async function publish(payload: { change_note: string; access: 'public' | 'protected' } = { change_note: 'Published from designer', access: 'public' }) {
  if (validationIssues.value.length) { showChecklist.value = true; return }
  publishing.value = true
  try {
    if (!await save()) return
    const { data } = await api.post(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/publish`, payload)
    workflow.value.published_version_id = data.id
    workflow.value.published_access = payload.access
    await loadVersions()
  } catch (cause: any) { saveError.value = cause.response?.data?.detail || String(cause) }
  finally { publishing.value = false }
}
function openRunDialog(nodeId: string | null = null) {
  runTargetNodeId.value = nodeId
  runInputs.value = createWorkflowInputValues(startFields.value)
  runError.value = ''; showRunDialog.value = true
}
async function uploadRunFile(field: any, event: Event) {
  const input = event.target as HTMLInputElement; const files = Array.from(input.files || [])
  if (!files.length) return
  uploadingField.value = field.name; runError.value = ''
  try {
    const uploaded = []
    for (const file of files) {
      const form = new FormData(); form.append('file', file)
      uploaded.push((await api.post(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/files`, form)).data)
    }
    runInputs.value[field.name] = field.type === 'files' ? uploaded : uploaded[0]
  } catch (cause: any) { runError.value = cause.response?.data?.detail || String(cause) }
  finally { uploadingField.value = '' }
}
async function run() {
  running.value = true; runError.value = ''; result.value = null
  clearRunOverlay()
  try {
    const inputs = coerceWorkflowInputValues(startFields.value, runInputs.value)
    const path = runTargetNodeId.value
      ? `/workspaces/${workspaceId.value}/workflows/${workflowId.value}/nodes/${runTargetNodeId.value}/run`
      : `/workspaces/${workspaceId.value}/workflows/${workflowId.value}/run`
    result.value = (await api.post(path, { inputs })).data
    applyRunOverlay(result.value)
    inspectorTab.value = 'run'; await loadRuns()
    if (result.value.status === 'waiting') await openApprovals(result.value.id)
  } catch (cause: any) { runError.value = cause.response?.data?.detail || String(cause) }
  finally { running.value = false }
}
async function loadRuns() { runs.value = (await api.get(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/runs`)).data }
async function loadApprovals() { approvals.value = (await api.get(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/approvals`)).data }
async function openApprovals(runId = '') {
  await loadApprovals()
  selectedApproval.value = approvals.value.find(item => item.status === 'pending' && (!runId || item.run_id === runId)) || approvals.value[0] || null
  approvalComment.value = ''
  showApprovals.value = true
}
async function respondApproval(action: any) {
  if (!selectedApproval.value || selectedApproval.value.status !== 'pending') return
  respondingApproval.value = true; runError.value = ''
  try {
    const approval = selectedApproval.value
    const { data } = await api.post(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/runs/${approval.run_id}/approvals/${approval.id}/respond`, { action_id: action.id, comment: approvalComment.value, data: {} })
    result.value = data; applyRunOverlay(data); await Promise.all([loadRuns(), loadApprovals()])
    selectedApproval.value = approvals.value.find(item => item.status === 'pending' && item.run_id === data.id) || approvals.value.find(item => item.id === approval.id) || null
    if (data.status !== 'waiting') showApprovals.value = false
  } catch (cause: any) { runError.value = cause.response?.data?.detail || String(cause) }
  finally { respondingApproval.value = false }
}
async function openRunHistory() {
  await loadRuns()
  showRunHistory.value = true
}
function applyRunOverlay(runRecord: any) {
  const overlay = buildRunOverlay(nodes.value as any[], currentCanvasEdges() as any[], runRecord)
  nodes.value = overlay.nodes as Node[]
  commitEdges(overlay.edges as Edge[])
  nodeResults.value = overlay.nodeResults
  runtimeRunId.value = overlay.runId
}
function clearRunOverlay() {
  const cleared = clearGraphRunOverlay(nodes.value as any[], currentCanvasEdges() as any[])
  nodes.value = cleared.nodes as Node[]
  commitEdges(cleared.edges as Edge[])
  nodeResults.value = {}
  runtimeRunId.value = ''
}
function replayRun(runRecord: any) {
  selectedRun.value = runRecord
  result.value = runRecord
  applyRunOverlay(runRecord)
  showRunHistory.value = false
  showRunDialog.value = true
  runTargetNodeId.value = null
  selected.value = null
  activeSection.value = 'orchestration'
  setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 0)
}
function exitReplayMode() {
  clearRunOverlay()
  selectedRun.value = null
  showRunDialog.value = false
}
async function loadVersions() { versions.value = (await api.get(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/versions`)).data }
async function openPublish() {
  if (!showPublish.value) await loadVersions()
  showChecklist.value = false; showEnvironment.value = false; showSystemVariables.value = false
  showPublish.value = !showPublish.value
}
function toggleEnvironment() { environmentError.value = ''; showChecklist.value = false; showPublish.value = false; showSystemVariables.value = false; showEnvironment.value = !showEnvironment.value }
function toggleSystemVariables() { showChecklist.value = false; showPublish.value = false; showEnvironment.value = false; showSystemVariables.value = !showSystemVariables.value }
function openPublishedApp() { window.open(`${origin}/apps/${workflow.value.slug}`, '_blank', 'noopener,noreferrer') }
function openApiFromPublish() { showPublish.value = false; showSection('api') }
async function openVersionHistoryFromPublish() { showPublish.value = false; await openHistory() }
async function showSection(section: typeof activeSection.value) { activeSection.value = section; if (section === 'logs' || section === 'monitoring') await loadRuns() }
async function openHistory() { await loadVersions(); showHistory.value = true }
function openChangeHistory() { pushHistory(); showChangeHistory.value = true }
function restoreLocalSnapshot(index: number) { restoreHistory(index); showChangeHistory.value = false }
function versionDiff(item: any) {
  const current = graphSnapshot(); const version = item.graph || { nodes: [], edges: [] }
  const currentNodes = new Map(current.nodes.map(node => [node.id, node])); const versionNodes = new Map((version.nodes || []).map((node: any) => [node.id, node]))
  const added = [...currentNodes.keys()].filter(id => !versionNodes.has(id)).length
  const removed = [...versionNodes.keys()].filter(id => !currentNodes.has(id)).length
  const changed = [...currentNodes.keys()].filter(id => versionNodes.has(id) && JSON.stringify(currentNodes.get(id)?.data) !== JSON.stringify((versionNodes.get(id) as any)?.data)).length
  return { added, removed, changed, currentEdges: current.edges.length, versionEdges: (version.edges || []).length }
}
async function restorePublishedVersion() {
  if (!pendingRestoreVersion.value) return
  restoringVersion.value = true
  try {
    await api.post(`/workspaces/${workspaceId.value}/workflows/${workflowId.value}/versions/${pendingRestoreVersion.value.id}/restore`)
    pendingRestoreVersion.value = null; showHistory.value = false; selected.value = null
    await load()
  } catch (cause: any) { saveError.value = cause.response?.data?.detail || String(cause) }
  finally { restoringVersion.value = false }
}
function addInputField() { if (!selected.value) return; const fields = selected.value.data.inputFields || []; selected.value.data.inputFields = [...fields, `field_${fields.length + 1}`] }
function hasStartTrigger(trigger: string) { return selected.value?.data?.config?.triggers?.includes(trigger) }
function toggleStartTrigger(trigger: string) { if (selected.value) selected.value.data.config.triggers = [trigger] }
function addStartInput() {
  if (!selected.value) return
  const fields = selected.value.data.config.input_fields || []
  selected.value.data.config.input_fields = [...fields, normalizeStartField({ name: `field_${fields.length + 1}`, label: t('designer.newField') })]
  expandedStartFieldIndex.value = fields.length
}
function removeStartInput(index: string | number) {
  selected.value?.data?.config?.input_fields.splice(Number(index), 1)
  expandedStartFieldIndex.value = null
}
function toggleStartField(index: string | number) { expandedStartFieldIndex.value = expandedStartFieldIndex.value === Number(index) ? null : Number(index) }
function addStartFieldOption(field: any) { field.options = [...(field.options || []), `${t('designer.option')} ${(field.options || []).length + 1}`] }
function removeStartFieldOption(field: any, index: string | number) { field.options.splice(Number(index), 1) }
function addConditionClause() { selected.value?.data?.config?.conditions.push({ variable: '', operator: 'equals', value: '' }) }
function removeConditionClause(index: string | number) { selected.value?.data?.config?.conditions.splice(Number(index), 1) }
function addEndOutput() { if (selected.value) selected.value.data.config.outputs.push({ name: `output_${selected.value.data.config.outputs.length + 1}`, type: 'String', value: '' }) }
function removeEndOutput(index: string | number) { selected.value?.data?.config?.outputs.splice(Number(index), 1) }
function addClassifierCategory() { if (selected.value) selected.value.data.config.categories = [...(selected.value.data.config.categories || []), createClassifierCategory()] }
function removeClassifierCategory(index: number) {
  const category = selected.value?.data?.config?.categories?.[index]
  if (!selected.value || !category) return
  const handle = `category:${category.id}`
  commitEdges(currentCanvasEdges().filter(edge => !(edge.source === selected.value!.id && edge.sourceHandle === handle)))
  selected.value.data.config.categories.splice(index, 1)
}
function removeHumanAction(actionId: string) {
  if (!selected.value) return
  const handle = `action:${actionId}`
  commitEdges(currentCanvasEdges().filter(edge => !(edge.source === selected.value!.id && edge.sourceHandle === handle)))
  selected.value.data.config.actions = (selected.value.data.config.actions || []).filter((action: any) => action.id !== actionId)
}
function updateClassifierKeywords(category: any, value: string) { category.keywords = value.split(/[,，]/).map(item => item.trim()).filter(Boolean) }
function selectedCanvasNodes() {
  const canvasNodes = getNodes.value as any[]
  const selectedIds = new Set(canvasNodes.filter(node => node.selected).map(node => String(node.id)))
  if (selected.value) selectedIds.add(selected.value.id)
  let expanded = true
  while (expanded) {
    expanded = false
    for (const node of canvasNodes) if (node.parentNode && selectedIds.has(node.parentNode) && !selectedIds.has(node.id)) { selectedIds.add(node.id); expanded = true }
  }
  return canvasNodes.filter(node => selectedIds.has(node.id) && !['start', 'end'].includes(String(node.data?.nodeType || node.type)))
}
function selectedCanvasEdges() { return (currentCanvasEdges() as any[]).filter(edge => edge.selected) }
function clearSelectedCanvasEdges() {
  if (!(currentCanvasEdges() as any[]).some(edge => edge.selected)) return
  commitEdges(clearWorkflowEdgeSelection(currentCanvasEdges()) as Edge[])
}
function copySelection() {
  const selectedNodes = selectedCanvasNodes()
  if (!selectedNodes.length) return
  const ids = new Set(selectedNodes.map(node => node.id))
  const selectedEdges = (currentCanvasEdges() as any[]).filter(edge => ids.has(edge.source) && ids.has(edge.target))
  copiedGraph.value = JSON.parse(JSON.stringify({ nodes: selectedNodes, edges: selectedEdges })) as GraphState
}
function pasteSelection() {
  if (!copiedGraph.value?.nodes.length) return
  const idMap = new Map(copiedGraph.value.nodes.map(node => [node.id, `${String(node.type || 'node')}-${crypto.randomUUID().slice(0, 8)}`]))
  let existingNodes = (nodes.value as any[]).map(node => ({ ...node, selected: false }))
  const pastedNodes: any[] = []
  const referenceRenames: Array<Pick<NodeRename, 'from' | 'to'>> = []
  for (const copied of copiedGraph.value.nodes as any[]) {
    const type = String(copied.data?.nodeType || copied.type || 'default')
    const baseName = t(`workflow.nodes.${type}`)
    const preferred = nodeReferenceName(copied) || baseName
    const reservedNodes = [...existingNodes, ...pastedNodes]
    let name = nextUniqueNodeName(reservedNodes, preferred)
    if (preferred === baseName) {
      const allocation = allocateDefaultNodeName(reservedNodes, type, baseName)
      if (allocation.renames.length) {
        existingNodes = renameNodesAndReferences(existingNodes, allocation.renames)
        const renamedPasted = renameNodesAndReferences(pastedNodes, allocation.renames)
        pastedNodes.splice(0, pastedNodes.length, ...renamedPasted)
      }
      name = allocation.name
    }
    referenceRenames.push({ from: preferred, to: name })
    pastedNodes.push({
      ...copied,
      id: idMap.get(copied.id)!,
      parentNode: copied.parentNode ? (idMap.get(copied.parentNode) || copied.parentNode) : undefined,
      selected: true,
      position: copied.parentNode ? { x: copied.position.x + 24, y: copied.position.y + 24 } : { x: copied.position.x + 42, y: copied.position.y + 42 },
      data: { ...copied.data, label: name },
    })
  }
  const rewrittenPastedNodes = pastedNodes.map(node => ({
    ...node,
    data: { ...node.data, config: rewriteNodeReferences(node.data?.config || {}, referenceRenames) },
  }))
  const nextNodes = [
    ...existingNodes,
    ...rewrittenPastedNodes,
  ]
  nodes.value = nextNodes as Node[]
  commitEdges([...currentCanvasEdges(), ...copiedGraph.value.edges.map(edge => ({ ...edge, id: crypto.randomUUID(), source: idMap.get(edge.source)!, target: idMap.get(edge.target)! }))] as Edge[])
  selected.value = nextNodes.find(node => node.id === idMap.get(copiedGraph.value!.nodes[0].id)) || null
}
function duplicateSelection() { copySelection(); pasteSelection() }
function removeSelection() {
  const ids = new Set(selectedCanvasNodes().map(node => node.id))
  const edgeIds = new Set(selectedCanvasEdges().map(edge => edge.id))
  if (!ids.size && !edgeIds.size) return
  nodes.value = (nodes.value as any[]).filter(node => !ids.has(node.id)) as Node[]
  commitEdges(currentCanvasEdges().filter(edge => !edgeIds.has(edge.id) && !ids.has(edge.source) && !ids.has(edge.target)))
  selected.value = null
}
function clearSelection() {
  const selectedNodes = (getNodes.value as any[]).filter(node => node.selected)
  if (selectedNodes.length) removeSelectedNodes(selectedNodes)
  clearSelectedCanvasEdges()
  selected.value = null
  nodeNameError.value = ''
  nodeContextMenu.value = null
}
function clearNodeSelection() {
  const selectedNodes = (getNodes.value as any[]).filter(node => node.selected)
  if (selectedNodes.length) removeSelectedNodes(selectedNodes)
  selected.value = null
  nodeNameError.value = ''
  nodeContextMenu.value = null
}
function selectAllEditableNodes() {
  const editableNodes = (getNodes.value as any[]).filter(node => !['start', 'end'].includes(String(node.data?.nodeType || node.type)))
  if (!editableNodes.length) return
  addSelectedNodes(editableNodes)
  selected.value = editableNodes[0]
}
function selectOnlyCanvasNode(nodeId: string) {
  const target = (getNodes.value as any[]).find(node => node.id === nodeId) || (nodes.value as any[]).find(node => node.id === nodeId)
  if (!target) return null
  addSelectedNodes([target])
  selected.value = target
  nodeNameError.value = ''
  return target
}
function runNodeAction(nodeId: string, action: NodeAction) {
  const node = selectOnlyCanvasNode(nodeId)
  if (!node) return
  nodeContextMenu.value = null
  if (action === 'run') openRunDialog(nodeId)
  else if (action === 'change') openPaletteForReplacement(nodeId)
  else if (action === 'copy') copySelection()
  else if (action === 'duplicate') duplicateSelection()
  else if (action === 'delete') removeSelection()
}
function handleNodeAction(event: Event) {
  const detail = (event as CustomEvent<{ nodeId?: string; action?: NodeAction }>).detail
  if (detail?.nodeId && detail.action) runNodeAction(detail.nodeId, detail.action)
}
function openNodeContextMenu(payload: { event: MouseEvent | TouchEvent; node: Node }) {
  if (replayMode.value || !canvasHost.value) return
  payload.event.preventDefault()
  if (!('clientX' in payload.event)) return
  const rect = canvasHost.value.getBoundingClientRect()
  nodeContextMenu.value = {
    nodeId: payload.node.id,
    x: Math.max(8, Math.min(payload.event.clientX - rect.left, rect.width - 188)),
    y: Math.max(8, Math.min(payload.event.clientY - rect.top, rect.height - 188)),
  }
  selectOnlyCanvasNode(payload.node.id)
}
function autoLayout() {
  const topLevel = (nodes.value as any[]).filter(node => !node.parentNode)
  const topIds = new Set(topLevel.map(node => node.id))
  const laidOut = layoutWorkflow(topLevel, (currentCanvasEdges() as any[]).filter(edge => topIds.has(edge.source) && topIds.has(edge.target)))
  const positions = new Map(laidOut.map(node => [node.id, node.position]))
  nodes.value = (nodes.value as any[]).map(node => node.parentNode ? node : { ...node, position: positions.get(node.id) || node.position }) as Node[]
  setTimeout(() => fitView({ padding: 0.2 }), 50)
}
function validConnection(connection: Connection) { return isConnectionAllowed(nodes.value as any[], currentCanvasEdges() as any[], connection) }
function commitEdges(nextEdges: Edge[]) {
  const committed = mergeWorkflowEdges(nextEdges).map(edge => ({ ...edge, type: edge.type || 'workflow' })) as Edge[]
  edges.value = committed
}
async function appendEdge(edge: Edge) {
  commitEdges([...currentCanvasEdges(), edge])
  editRevision.value += 1
  dirty.value = true
  saveError.value = ''
  saveConflict.value = false
  scheduleSave()
}
function replacementText(current: unknown, oldType: string, newType: string, section: 'nodes' | 'nodeDescriptions') {
  const knownDefaults = Object.values(messages).map(locale => section === 'nodes'
    ? (locale as any).workflow?.nodes?.[oldType]
    : (locale as any).designer?.nodeDescriptions?.[oldType]).filter(Boolean)
  const value = String(current || '').trim()
  const usesDefault = knownDefaults.some(defaultValue => value === defaultValue || (value.startsWith(String(defaultValue)) && /^\d+$/u.test(value.slice(String(defaultValue).length))))
  if (value && !usesDefault) return value
  return t(section === 'nodes' ? `workflow.nodes.${newType}` : `designer.nodeDescriptions.${newType}`)
}
async function add(type: string, configOverride: Record<string, any> = {}) {
  if (paletteReplaceNodeId.value) {
    const oldNode = (nodes.value as any[]).find(node => node.id === paletteReplaceNodeId.value)
    if (!oldNode) return null
    const isContainer = ['iteration', 'loop'].includes(type)
    const oldType = String(oldNode.data?.nodeType || oldNode.type || '')
    const oldName = nodeReferenceName(oldNode)
    const baseName = t(`workflow.nodes.${type}`)
    const requestedName = replacementText(oldNode.data?.label, oldType, type, 'nodes')
    let replacementName = nextUniqueNodeName(nodes.value as any[], requestedName, [oldNode.id])
    if (requestedName === baseName) {
      const allocation = allocateDefaultNodeName((nodes.value as any[]).filter(node => node.id !== oldNode.id), type, baseName)
      if (allocation.renames.length) nodes.value = renameNodesAndReferences(nodes.value as any[], allocation.renames) as Node[]
      replacementName = allocation.name
    }
    const replacement: any = {
      id: oldNode.id,
      type,
      position: oldNode.position,
      ...(oldNode.parentNode ? { parentNode: oldNode.parentNode, extent: oldNode.extent || 'parent', expandParent: oldNode.expandParent ?? true } : {}),
      ...(isContainer ? { style: { width: '520px', height: '260px' } } : {}),
      selected: true,
      data: {
        label: replacementName,
        nodeType: type,
        description: replacementText(oldNode.data?.description, oldType, type, 'nodeDescriptions'),
        config: withNamedStartReferences({ ...defaultNodeConfig(type), ...configOverride }),
      },
    }
    const replaced = replaceWorkflowNode(nodes.value as any[], currentCanvasEdges() as any[], oldNode.id, replacement)
    nodes.value = (oldName && oldName !== replacementName ? replaceReferences(replaced.nodes as any[], [{ from: oldName, to: replacementName }]) : replaced.nodes) as Node[]
    commitEdges(replaced.edges as Edge[])
    selectOnlyCanvasNode(replacement.id)
    paletteOpen.value = false
    paletteReplaceNodeId.value = null
    await nextTick()
    setTimeout(focusSelected, 120)
    return replacement
  }
  const baseName = t(`workflow.nodes.${type}`)
  const allocation = allocateDefaultNodeName(nodes.value as any[], type, baseName)
  if (allocation.renames.length) nodes.value = renameNodesAndReferences(nodes.value as any[], allocation.renames) as Node[]
  const id = `${type}-${crypto.randomUUID().slice(0, 8)}`
  const sourceId = pendingSourceConnection?.sourceId || paletteSourceId.value
  const sourceHandle = pendingSourceConnection?.sourceHandle || paletteSourceHandle.value || undefined
  const source = sourceId ? (nodes.value as any[]).find(node => node.id === sourceId) : null
  const insertionEdge = paletteEdgeId.value ? (currentCanvasEdges() as any[]).find(edge => edge.id === paletteEdgeId.value) : null
  const edgeSource = insertionEdge ? (nodes.value as any[]).find(node => node.id === insertionEdge.source) : null
  const edgeTarget = insertionEdge ? (nodes.value as any[]).find(node => node.id === insertionEdge.target) : null
  const parentId = paletteParentId.value || source?.parentNode || (edgeSource?.parentNode && edgeSource.parentNode === edgeTarget?.parentNode ? edgeSource.parentNode : null)
  const siblingCount = parentId ? (nodes.value as any[]).filter(item => item.parentNode === parentId).length : 0
  const requestedPosition = parentId
    ? { x: 230, y: 84 + siblingCount * 112 }
    : insertionEdge && edgeSource && edgeTarget
    ? { x: (edgeSource.position.x + edgeTarget.position.x) / 2, y: (edgeSource.position.y + edgeTarget.position.y) / 2 }
    : source ? { x: source.position.x + (['iteration', 'loop'].includes(String(source.data?.nodeType || source.type)) ? 580 : 270), y: source.position.y } : { x: 300 + Math.random() * 180, y: 140 + Math.random() * 240 }
  const position = insertionEdge
    ? requestedPosition
    : findAvailableNodePosition(nodes.value as any[], requestedPosition, { parentNode: parentId, ignoreIds: source ? [source.id] : [] })
  const isContainer = ['iteration', 'loop'].includes(type)
  const node = {
    id,
    type,
    position,
    ...(parentId ? { parentNode: parentId, extent: 'parent' as const, expandParent: true } : {}),
    ...(isContainer ? { style: { width: '520px', height: '260px' } } : {}),
    data: { label: allocation.name, nodeType: type, description: t(`designer.nodeDescriptions.${type}`), config: withNamedStartReferences({ ...defaultNodeConfig(type), ...configOverride }) },
  }
  if (insertionEdge) {
    const next = insertNodeOnEdge(nodes.value as any[], currentCanvasEdges() as any[], insertionEdge.id, node)
    nodes.value = next.nodes as Node[]
    addNodes(node as Node)
    await nextTick()
    commitEdges(next.edges as Edge[])
  } else {
    nodes.value = [...(nodes.value as any[]), node] as Node[]
    addNodes(node as Node)
    await nextTick()
    if (source) await appendEdge({ id: crypto.randomUUID(), source: source.id, sourceHandle, target: id, type: 'workflow', data: { branchLabel: classifierBranchLabel(source, sourceHandle) } } as Edge)
  }
  selectOnlyCanvasNode(node.id)
  paletteOpen.value = false
  paletteSourceId.value = null
  paletteSourceHandle.value = null
  paletteEdgeId.value = null
  paletteParentId.value = null
  paletteReplaceNodeId.value = null
  pendingSourceConnection = null
  await nextTick()
  setTimeout(focusSelected, 120)
  return node
}
async function addScriptSnippet(script: any) {
  const added = await add('script', { script_id: script.id, script_name: script.name, version: 'latest' })
  if (!added) return
  updateSelectedNodeLabel(nextUniqueNodeName(nodes.value as any[], script.name, [added.id]))
}
function addNoteAt(position?: { x: number; y: number }) {
  const name = allocateDefaultNodeName(nodes.value as any[], 'note', t('designer.noteTitleDefault'))
  if (name.renames.length) nodes.value = renameNodesAndReferences(nodes.value as any[], name.renames) as Node[]
  const note = { id: `note-${crypto.randomUUID().slice(0, 8)}`, type: 'note', position: position || { x: 260, y: 140 }, data: { label: name.name, description: '', nodeType: 'note', color: annotationColor.value } }
  nodes.value = [...(nodes.value as any[]), note] as Node[]; selectOnlyCanvasNode(note.id); paletteOpen.value = false; paletteEdgeId.value = null
  annotationMode.value = false
}
function toggleAnnotationMode() {
  annotationMode.value = !annotationMode.value
  if (annotationMode.value) { commentMode.value = false; showComments.value = false; interactionMode.value = 'pointer'; paletteOpen.value = false; nodeContextMenu.value = null; selected.value = null }
}
function handlePaneClick(event: MouseEvent) {
  nodeContextMenu.value = null
  const point = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
  if (annotationMode.value) { addNoteAt({ x: point.x - 110, y: point.y - 63 }); return }
  if (commentMode.value) { createCommentAt(point); return }
  paletteOpen.value = false
  clearSelection()
}
function handleCanvasBackgroundClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (!target?.classList.contains('vue-flow__pane') || annotationMode.value || commentMode.value) return
  paletteOpen.value = false
  clearSelection()
}
function handleCanvasMouseDown(event: MouseEvent) {
  if (event.button !== 1) return
  middlePanning.value = true
  paletteOpen.value = false
  nodeContextMenu.value = null
}
function stopMiddlePanning() { middlePanning.value = false }
function handleCanvasAuxClick(event: MouseEvent) { if (event.button === 1) event.preventDefault() }
function currentCommentAuthor() { return { author_id: auth.user?.id || '', author_name: auth.user?.display_name || auth.user?.email || t('designer.user') } }
function toggleCommentMode() {
  commentMode.value = !commentMode.value
  showComments.value = true
  annotationMode.value = false
  selected.value = null
  selectedCommentId.value = null
  interactionMode.value = 'pointer'
  paletteOpen.value = false; nodeContextMenu.value = null
}
function createCommentAt(position: { x: number; y: number }) {
  const now = new Date().toISOString()
  const thread: WorkflowCommentThread = { id: `comment-${crypto.randomUUID().slice(0, 12)}`, position, resolved: false, messages: [], created_at: now, updated_at: now }
  comments.value = [...comments.value.filter(item => item.messages.length), thread]
  selectedCommentId.value = thread.id
  showComments.value = true
  commentMode.value = false
}
function submitComment(payload: { threadId: string; content: string }) {
  const thread = comments.value.find(item => item.id === payload.threadId)
  if (!thread || !payload.content.trim()) return
  const now = new Date().toISOString(); const author = currentCommentAuthor()
  thread.messages.push({ id: `message-${crypto.randomUUID().slice(0, 12)}`, ...author, content: payload.content.trim(), created_at: now })
  thread.updated_at = now
}
function toggleCommentResolved(threadId: string) {
  const thread = comments.value.find(item => item.id === threadId)
  if (!thread) return
  thread.resolved = !thread.resolved; thread.updated_at = new Date().toISOString()
}
function deleteCommentThread(threadId: string) {
  comments.value = comments.value.filter(item => item.id !== threadId)
  if (selectedCommentId.value === threadId) selectedCommentId.value = null
}
function selectComment(threadId: string | null) { selectedCommentId.value = threadId; showComments.value = true; selected.value = null }
function closeComments() {
  comments.value = comments.value.filter(item => item.messages.length)
  selectedCommentId.value = null; showComments.value = false; commentMode.value = false
}
function commentPinStyle(comment: WorkflowCommentThread) {
  return { left: `${comment.position.x * viewport.value.zoom + viewport.value.x}px`, top: `${comment.position.y * viewport.value.zoom + viewport.value.y}px` }
}
function clampPalettePosition(x: number, y: number) {
  const host = canvasHost.value
  if (!host) return { x: Math.max(8, x), y: Math.max(8, y) }
  const rect = host.getBoundingClientRect()
  return { x: Math.max(8, Math.min(x, rect.width - 296)), y: Math.max(8, Math.min(y, rect.height - 568)) }
}
function positionPaletteAtClient(clientX?: number, clientY?: number, sourceId?: string) {
  const host = canvasHost.value
  if (!host) return
  const hostRect = host.getBoundingClientRect()
  if (Number.isFinite(clientX) && Number.isFinite(clientY)) {
    const openLeft = Number(clientX) - hostRect.left + 12
    const x = openLeft + 288 > hostRect.width ? Number(clientX) - hostRect.left - 300 : openLeft
    palettePosition.value = clampPalettePosition(x, Number(clientY) - hostRect.top - 36)
    return
  }
  const element = sourceId ? host.querySelector<HTMLElement>(`.vue-flow__node[data-id="${CSS.escape(sourceId)}"]`) : null
  if (element) {
    const rect = element.getBoundingClientRect()
    const openLeft = rect.right - hostRect.left + 12
    const x = openLeft + 288 > hostRect.width ? rect.left - hostRect.left - 300 : openLeft
    palettePosition.value = clampPalettePosition(x, rect.top - hostRect.top)
    return
  }
  palettePosition.value = clampPalettePosition(64, hostRect.height / 2 - 280)
}
function openPalette() {
  pendingSourceConnection = null
  paletteSourceId.value = null; paletteSourceHandle.value = null; paletteEdgeId.value = null; paletteParentId.value = null; paletteReplaceNodeId.value = null; paletteQuery.value = ''; paletteTab.value = 'nodes'
  if (!paletteOpen.value) positionPaletteAtClient()
  paletteOpen.value = !paletteOpen.value
}
function handleQuickAdd(event: Event) {
  const detail = (event as CustomEvent<{ sourceId?: string; sourceHandle?: string; clientX?: number; clientY?: number }>).detail
  const sourceId = detail?.sourceId
  if (!sourceId) return
  openPaletteForSource(sourceId, detail?.sourceHandle, detail.clientX, detail.clientY)
}
function openPaletteForSource(sourceId: string, sourceHandle?: string, clientX?: number, clientY?: number) { pendingSourceConnection = { sourceId, sourceHandle }; paletteSourceId.value = sourceId; paletteSourceHandle.value = sourceHandle || null; paletteEdgeId.value = null; paletteParentId.value = null; paletteReplaceNodeId.value = null; paletteQuery.value = ''; paletteTab.value = 'nodes'; positionPaletteAtClient(clientX, clientY, sourceId); paletteOpen.value = true }
function openPaletteForReplacement(nodeId: string) {
  pendingSourceConnection = null
  paletteSourceId.value = null; paletteSourceHandle.value = null; paletteEdgeId.value = null; paletteParentId.value = null; paletteReplaceNodeId.value = nodeId; paletteQuery.value = ''; paletteTab.value = 'nodes'
  positionPaletteAtClient(undefined, undefined, nodeId)
  paletteOpen.value = true
}
function handleContainerAdd(event: Event) {
  const detail = (event as CustomEvent<{ parentId?: string; clientX?: number; clientY?: number }>).detail
  const parentId = detail?.parentId
  if (!parentId) return
  pendingSourceConnection = null; paletteParentId.value = parentId; paletteSourceId.value = null; paletteSourceHandle.value = null; paletteEdgeId.value = null; paletteReplaceNodeId.value = null; paletteQuery.value = ''; paletteTab.value = 'nodes'; positionPaletteAtClient(detail.clientX, detail.clientY, parentId); paletteOpen.value = true
}
function handleContainerDelete(event: Event) {
  const parentId = (event as CustomEvent<{ parentId?: string }>).detail?.parentId
  if (!parentId) return
  const ids = new Set([parentId, ...(nodes.value as any[]).filter(node => node.parentNode === parentId).map(node => node.id)])
  nodes.value = (nodes.value as any[]).filter(node => !ids.has(node.id)) as Node[]
  commitEdges(currentCanvasEdges().filter(edge => !ids.has(edge.source) && !ids.has(edge.target)))
  selected.value = null
}
function handleEdgeDelete(event: Event) {
  const edgeId = (event as CustomEvent<{ edgeId?: string }>).detail?.edgeId
  if (!edgeId) return
  commitEdges(removeWorkflowEdgeById(currentCanvasEdges(), edgeId))
}
function focusSelected() {
  if (!selected.value) return
  const width = Number((selected.value as any).dimensions?.width || 206)
  const height = Number((selected.value as any).dimensions?.height || 90)
  setCenter(selected.value.position.x + width / 2, selected.value.position.y + height / 2, {
    zoom: Math.min(1.1, Math.max(0.8, viewport.value.zoom)),
    duration: 300,
  })
}
function focusCommandNode(nodeId: string) {
  const node = (nodes.value as any[]).find(item => item.id === nodeId)
  if (!node) return
  selectOnlyCanvasNode(nodeId)
  inspectorTab.value = 'settings'
  nextTick(() => setTimeout(focusSelected, 50))
}
function focusTraceNode(nodeId: string) {
  focusCommandNode(nodeId)
}
function addCommandNode(type: string) {
  paletteSourceId.value = null; paletteSourceHandle.value = null; paletteEdgeId.value = null; paletteParentId.value = null; paletteReplaceNodeId.value = null
  add(type)
}
function executeCommand(id: string) {
  if (id === 'run') openRunDialog()
  else if (id === 'save') save()
  else if (id === 'publish') openPublish()
  else if (id === 'layout') autoLayout()
  else if (id === 'history') openHistory()
  else if (id === 'variables') { activeSection.value = 'orchestration'; showVariableInspector.value = true }
}
function syncConfigEditor() {
  configError.value = ''
  const config = selected.value?.data?.config || {}
  configText.value = JSON.stringify(config, null, 2)
  configBuffers.value = {
    scriptInputs: JSON.stringify(config.inputs || {}, null, 2),
    values: JSON.stringify(config.values || {}, null, 2),
    jsonValue: JSON.stringify(config.value || {}, null, 2),
    httpHeaders: JSON.stringify(config.headers || {}, null, 2),
    httpQuery: JSON.stringify(config.query || {}, null, 2),
    httpBody: config.body == null ? '' : JSON.stringify(config.body, null, 2),
    llmSchema: JSON.stringify(config.response_schema || { type: 'object', properties: {} }, null, 2),
  }
  configFieldErrors.value = {}
}
function updateSelectedConfig() {
  if (!selected.value) return
  try { selected.value.data.config = JSON.parse(configText.value || '{}'); configError.value = '' }
  catch { configError.value = t('designer.invalidJson') }
}
function updateStructuredField(field: string, buffer: keyof typeof configBuffers.value) {
  if (!selected.value) return
  const value = configBuffers.value[buffer]
  try {
    selected.value.data.config[field] = value.trim() ? JSON.parse(value) : (field === 'body' ? null : {})
    const errors = { ...configFieldErrors.value }; delete errors[buffer]; configFieldErrors.value = errors
  } catch { configFieldErrors.value = { ...configFieldErrors.value, [buffer]: t('designer.invalidJson') } }
}
function selectModelProvider() {
  if (!selected.value) return
  const provider = modelProviders.value.find(item => item.id === selected.value!.data.config.provider_id)
  if (provider) { selected.value.data.config.provider_name = provider.name; selected.value.data.config.model = provider.default_model }
}
function selectScript() {
  if (!selected.value) return
  const script = scripts.value.find(item => item.id === selected.value!.data.config.script_id)
  if (script) { selected.value.data.config.script_name = script.name; selected.value.data.config.version = 'latest' }
}
function selectSubworkflow() {
  if (!selected.value) return
  const target = subworkflows.value.find(item => item.id === selected.value!.data.config.workflow_id)
  if (target) selected.value.data.config.workflow_name = target.name
}
function selectNode(event: NodeMouseEvent) {
  closeComments()
  selectOnlyCanvasNode(event.node.id)
  inspectorTab.value = 'settings'
  nextTick(() => setTimeout(focusSelected, 120))
}
function issueText(issue: WorkflowValidationIssue) { return t(`designer.validation.${issue.code}`, issue.params || {}) }
function syncValidationOverlay() {
  const messages = new Map<string, string[]>()
  for (const issue of validationIssues.value) {
    if (!issue.nodeId) continue
    messages.set(issue.nodeId, [...(messages.get(issue.nodeId) || []), issueText(issue)])
  }
  for (const node of nodes.value as any[]) {
    const next = messages.get(node.id) || []
    const current = Array.isArray(node.data?.validationMessages) ? node.data.validationMessages : []
    if (JSON.stringify(current) === JSON.stringify(next)) continue
    if (next.length) node.data.validationMessages = next
    else delete node.data.validationMessages
  }
}
function jumpToIssue(issue: WorkflowValidationIssue) {
  showChecklist.value = false
  if (!issue.nodeId) return
  const node = selectOnlyCanvasNode(issue.nodeId)
  if (!node) return
  inspectorTab.value = 'settings'
  nextTick(() => setTimeout(focusSelected, 120))
}
function handleNodeValidation(event: Event) {
  const nodeId = (event as CustomEvent<{ nodeId?: string }>).detail?.nodeId
  const issue = validationIssues.value.find(item => item.nodeId === nodeId)
  if (issue) jumpToIssue(issue)
}
function toggleLocale() { preferences.setLocale(preferences.locale === 'zh' ? 'en' : 'zh') }
function toggleTheme() { preferences.setTheme(preferences.isDark ? 'light' : 'dark') }
function toggleSidebar() { sidebarCollapsed.value = !sidebarCollapsed.value }
async function copyVariableReference(path: string) {
  const value = `{{${path}}}`
  try { await navigator.clipboard.writeText(value) }
  catch {
    const input = document.createElement('textarea'); input.value = value; input.style.position = 'fixed'; input.style.opacity = '0'; document.body.appendChild(input); input.select(); document.execCommand('copy'); input.remove()
  }
  copiedVariablePath.value = path
  window.setTimeout(() => { if (copiedVariablePath.value === path) copiedVariablePath.value = '' }, 1600)
}
function runtimeVariableValue(path: string) {
  if (path.startsWith('env.')) return environmentVariables.value.find(variable => variable.name === path.slice(4))?.value
  if (path.startsWith('sys.')) {
    const key = path.slice(4)
    const values: Record<string, any> = { user_id: auth.user?.id, app_id: workflowId.value, workflow_id: workflowId.value, workflow_run_id: runtimeRunId.value || undefined, timestamp: selectedRun.value?.created_at ? Math.floor(new Date(selectedRun.value.created_at).getTime() / 1000) : undefined }
    return values[key]
  }
  return readRuntimeVariable(path, nodeResults.value, nodes.value as any[])
}
function variableReference(path: string) { return `{{${path}}}` }
function formatRuntimeValue(value: any) {
  if (value === undefined) return t('designer.notRunYet')
  if (typeof value === 'string') return value
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}
function handleKeydown(event: KeyboardEvent) {
  const command = event.ctrlKey || event.metaKey; const key = event.key.toLowerCase()
  if (command && key === 'k') { event.preventDefault(); showCommandPalette.value = !showCommandPalette.value; return }
  if (event.key === 'Escape' && showCommandPalette.value) { showCommandPalette.value = false; return }
  if (event.key === 'Escape' && paletteOpen.value) { paletteOpen.value = false; paletteReplaceNodeId.value = null; return }
  if (event.key === 'Escape' && (annotationMode.value || commentMode.value)) { annotationMode.value = false; commentMode.value = false; return }
  const target = event.target as HTMLElement | null
  if (target?.matches('input, textarea, select, [contenteditable="true"]')) return
  if (event.altKey && key === 'r') { event.preventDefault(); openRunDialog() }
  else if (command && key === 's') { event.preventDefault(); save() }
  else if (command && key === 'z') { event.preventDefault(); event.shiftKey ? redo() : undo() }
  else if (command && key === 'y') { event.preventDefault(); redo() }
  else if (command && key === 'a') { event.preventDefault(); selectAllEditableNodes() }
  else if (command && key === 'c') { event.preventDefault(); copySelection() }
  else if (command && key === 'v') { event.preventDefault(); pasteSelection() }
  else if (command && key === 'd') { event.preventDefault(); duplicateSelection() }
  else if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); removeSelection() }
}
onConnect(connection => {
  if (!validConnection(connection)) return
  void appendEdge({ ...connection, id: crypto.randomUUID(), type: 'workflow' } as Edge)
})
watch(() => JSON.stringify(graphSnapshot()), () => {
  if (!loaded.value) return
  editRevision.value += 1
  dirty.value = true
  saveError.value = ''
  saveConflict.value = false
  scheduleSave()
  if (!restoringHistory) { clearTimeout(historyTimer); historyTimer = setTimeout(pushHistory, 250) }
}, { deep: true })
watch(() => selected.value?.id, syncConfigEditor)
watch(() => (nodes.value as any[]).map(node => node.id).join(','), () => {
  if (selected.value && !(nodes.value as any[]).some(node => node.id === selected.value!.id)) selected.value = null
})
watch(() => JSON.stringify(selected.value?.data?.config || {}), () => { if (!configEditing.value) syncConfigEditor(); if (selectedType.value === 'classifier') syncClassifierEdgeLabels() })
watch(() => validationIssues.value.map(issue => `${issue.nodeId || ''}|${issue.code}|${issueText(issue)}`).join('\n'), syncValidationOverlay, { immediate: true })
onBeforeRouteLeave(() => (!dirty.value && !saving.value) || window.confirm(t('designer.unsavedLeaveConfirm')))
onMounted(async () => { window.addEventListener('keydown', handleKeydown); window.addEventListener('mouseup', stopMiddlePanning); window.addEventListener('blur', stopMiddlePanning); window.addEventListener('beforeunload', handleBeforeUnload); window.addEventListener('workflow-quick-add', handleQuickAdd); window.addEventListener('workflow-node-action', handleNodeAction); window.addEventListener('workflow-node-validation', handleNodeValidation); window.addEventListener('workflow-container-add', handleContainerAdd); window.addEventListener('workflow-container-delete', handleContainerDelete); window.addEventListener('workflow-edge-delete', handleEdgeDelete); await workspaces.load(); await Promise.all([load(), loadResources(), loadApprovals(), loadEnvironmentVariables()]) })
onUnmounted(() => { clearTimeout(saveTimer); clearTimeout(historyTimer); window.removeEventListener('keydown', handleKeydown); window.removeEventListener('mouseup', stopMiddlePanning); window.removeEventListener('blur', stopMiddlePanning); window.removeEventListener('beforeunload', handleBeforeUnload); window.removeEventListener('workflow-quick-add', handleQuickAdd); window.removeEventListener('workflow-node-action', handleNodeAction); window.removeEventListener('workflow-node-validation', handleNodeValidation); window.removeEventListener('workflow-container-add', handleContainerAdd); window.removeEventListener('workflow-container-delete', handleContainerDelete); window.removeEventListener('workflow-edge-delete', handleEdgeDelete) })
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-[var(--app-bg)]">
    <WorkflowDesignerSidebar
      :collapsed="sidebarCollapsed"
      :workflow-name="workflow?.name"
      :user-name="auth.user?.display_name"
      :active-section="activeSection"
      :dark="preferences.isDark"
      @back="router.push(`/w/${workspaceId}/studio`)"
      @toggle-collapsed="toggleSidebar"
      @search="showCommandPalette = true"
      @select-section="showSection"
      @toggle-locale="toggleLocale"
      @toggle-theme="toggleTheme"
      @help="showHelp = true"
    />

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-12 shrink-0 items-center border-b border-[var(--border)] bg-[var(--panel)] px-4 transition-[padding]" :class="replayMode && 'pr-[446px]'">
        <template v-if="replayMode">
          <div class="flex items-center gap-2 text-xs"><Activity :size="14" class="text-[var(--primary)]" /><span class="font-semibold">{{ t(`designer.triggerShort.${selectedRun?.triggered_by || 'studio'}`) }} ({{ selectedRun ? new Date(selectedRun.created_at).toLocaleTimeString() : '' }})</span><span class="muted">·</span><span class="rounded bg-[var(--panel-subtle)] px-2 py-1 text-[10px] font-medium">{{ t('designer.readOnly') }}</span></div>
          <div class="ml-auto flex items-center gap-2"><div class="relative"><button class="icon-button surface" :title="t('designer.runHistory')" :aria-label="t('designer.runHistory')" @click="showRunHistory ? showRunHistory = false : openRunHistory()"><Activity :size="16" /></button><RunHistoryPopover :open="showRunHistory" :runs="runs" @close="showRunHistory = false" @refresh="loadRuns" @replay="replayRun" /></div><Button variant="secondary" @click="exitReplayMode"><ArrowLeft :size="14" />{{ t('designer.returnToEdit') }}</Button></div>
        </template>
        <template v-else>
          <div class="flex min-w-0 items-center gap-1.5">
            <WorkflowSaveStatus :state="saveState" :saved-at="lastSavedAt" :error="saveError" @retry="save" @reload="reloadDraftAfterConflict" />
            <span v-if="workflow?.published_version_id" class="muted whitespace-nowrap text-xs">· {{ t('studio.published') }}</span>
          </div>
          <button v-if="runtimeRunId" class="ml-3 flex h-7 items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 text-[10px] font-semibold text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-300" :title="t('designer.clearRunOverlay')" @click="clearRunOverlay"><Activity :size="12" />{{ t('designer.runOverlay') }} · {{ runtimeRunId.slice(0, 8) }}<X :size="11" /></button>
          <div class="ml-auto flex items-center gap-2">
            <Button variant="secondary" :loading="running && !runTargetNodeId" @click="openRunDialog()"><Play :size="14" />{{ t('workflow.run') }}<kbd class="ml-1 rounded border border-[var(--border)] bg-[var(--panel-subtle)] px-1 py-0.5 text-[9px] font-normal text-[var(--muted)]">Alt R</kbd></Button>
            <div class="relative"><button class="icon-button surface" :title="t('designer.runHistory')" :aria-label="t('designer.runHistory')" @click="showRunHistory ? showRunHistory = false : openRunHistory()"><Activity :size="16" /></button><RunHistoryPopover :open="showRunHistory" :runs="runs" @close="showRunHistory = false" @refresh="loadRuns" @replay="replayRun" /></div>
          <button class="icon-button surface relative" :title="t('designer.pendingApprovals')" :aria-label="t('designer.pendingApprovals')" @click="openApprovals()"><UserCheck :size="16" /><span v-if="pendingApprovals.length" class="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-500 px-1 text-[8px] font-bold text-white">{{ pendingApprovals.length }}</span></button>
          <button class="icon-button surface" :title="t('designer.history')" @click="openHistory"><History :size="16" /></button>
          <div class="relative">
            <button class="icon-button surface relative" :class="{ 'text-amber-600': validationIssues.length }" :aria-label="`${t('designer.checklist')} (${validationIssues.length})`" :title="t('designer.checklist')" @click="showEnvironment = false; showSystemVariables = false; showChecklist = !showChecklist">
              <ListChecks :size="16" /><span v-if="validationIssues.length" class="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-500 px-1 text-[9px] font-bold text-white">{{ validationIssues.length }}</span>
            </button>
            <div v-if="showChecklist" class="surface absolute right-0 top-10 z-50 w-80 overflow-hidden rounded-lg shadow-xl">
              <div class="flex items-center gap-2 border-b border-[var(--border)] px-4 py-3"><ListChecks :size="16" /><span class="text-sm font-semibold">{{ t('designer.checklist') }}</span><span class="muted ml-auto text-xs">{{ validationIssues.length ? t('designer.issueCount', { count: validationIssues.length }) : t('designer.readyToPublish') }}</span></div>
              <div v-if="validationIssues.length" class="max-h-80 overflow-y-auto p-2"><button v-for="(issue, index) in validationIssues" :key="`${issue.code}-${issue.nodeId || index}`" class="flex w-full items-start gap-2 rounded-md px-2.5 py-2 text-left text-xs hover:bg-[var(--panel-subtle)]" @click="jumpToIssue(issue)"><AlertTriangle :size="14" class="mt-0.5 shrink-0 text-amber-600" /><span class="leading-5">{{ issueText(issue) }}</span><ChevronRight v-if="issue.nodeId" :size="13" class="muted ml-auto mt-1 shrink-0" /></button></div>
              <div v-else class="px-4 py-8 text-center"><span class="mx-auto flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40"><Check :size="18" /></span><p class="mt-2 text-sm font-medium">{{ t('designer.readyToPublish') }}</p><p class="muted mt-1 text-xs">{{ t('designer.noValidationIssues') }}</p></div>
            </div>
          </div>
          <div class="relative">
            <button class="surface flex h-8 items-center justify-center rounded-lg px-2 font-mono text-[9px] font-bold" :class="showEnvironment && 'border-[var(--primary)] text-[var(--primary)]'" :title="t('designer.environmentVariables')" :aria-label="t('designer.environmentVariables')" @click="toggleEnvironment">ENV</button>
            <WorkflowEnvironmentPanel v-if="showEnvironment" ref="environmentPanel" :variables="environmentVariables" :saving="environmentSaving" :error="environmentError" @close="showEnvironment = false" @create="createEnvironmentVariable" @update="updateEnvironmentVariable" @delete="deleteEnvironmentVariable" />
          </div>
          <div class="relative">
            <button class="icon-button surface" :class="showSystemVariables && 'text-[var(--primary)]'" :title="t('designer.systemVariables')" :aria-label="t('designer.systemVariables')" @click="toggleSystemVariables"><Braces :size="15" /></button>
            <WorkflowSystemVariablesPanel v-if="showSystemVariables" @close="showSystemVariables = false" />
          </div>
          <button class="icon-button surface" :title="t('common.save')" @click="save"><Save :size="16" /></button>
          <div class="relative">
            <Button :loading="publishing" @click="openPublish"><Rocket :size="15" />{{ t('workflow.publish') }}</Button>
            <PublishPopover :open="showPublish" :workflow="workflow" :versions="versions" :publishing="publishing" @close="showPublish = false" @publish="publish" @history="openVersionHistoryFromPublish" @api="openApiFromPublish" @run="openPublishedApp" />
          </div>
          </div>
        </template>
      </header>

      <div v-if="activeSection === 'orchestration'" class="flex min-h-0 flex-1">
        <section ref="canvasHost" class="relative min-w-0 flex-1" @click.capture="handleCanvasBackgroundClick" @mousedown="handleCanvasMouseDown" @auxclick="handleCanvasAuxClick">
          <VueFlow v-if="loaded" v-model:nodes="nodes" v-model:edges="edges" :node-types="nodeTypes" :edge-types="edgeTypes" :default-edge-options="{ type: 'workflow' }" :is-valid-connection="validConnection" :pan-on-drag="interactionMode === 'hand' || replayMode ? [0, 1] : [1]" :selection-on-drag="interactionMode === 'pointer' && !replayMode && !annotationMode && !commentMode" :nodes-draggable="interactionMode === 'pointer' && !replayMode && !annotationMode && !commentMode" :nodes-connectable="interactionMode === 'pointer' && !replayMode && !annotationMode && !commentMode" :elements-selectable="interactionMode === 'pointer' && !replayMode && !annotationMode && !commentMode" fit-view-on-init class="workflow-canvas" :class="{ 'replay-mode': replayMode, 'annotation-mode': annotationMode || commentMode, 'middle-panning': middlePanning }" @node-click="event => { nodeContextMenu = null; if (!replayMode && !annotationMode && !commentMode) selectNode(event) }" @node-context-menu="openNodeContextMenu" @edge-click="clearNodeSelection" @pane-click="handlePaneClick">
            <Background :gap="18" :size="1" pattern-color="var(--border)" />
            <MiniMap pannable zoomable position="bottom-right" />
          </VueFlow>
          <div v-for="entry in visibleCommentPins" :key="entry.comment.id" class="absolute z-[16] -translate-x-1/2 -translate-y-1/2" :style="commentPinStyle(entry.comment)">
            <WorkflowCommentPin :index="entry.index" :selected="selectedCommentId === entry.comment.id" :resolved="entry.comment.resolved" :label="t('designer.commentPinLabel', { index: entry.index })" @select="selectComment(entry.comment.id)" />
          </div>
          <div v-if="nodeContextMenu" class="absolute z-30" :style="{ left: `${nodeContextMenu.x}px`, top: `${nodeContextMenu.y}px` }" @click.stop>
            <NodeActionMenu :protected-node="contextMenuProtected" :can-change="contextMenuCanChange" @action="runNodeAction(nodeContextMenu.nodeId, $event)" />
          </div>
          <AnnotationPlacementToolbar v-if="annotationMode && !replayMode" v-model:color="annotationColor" class="absolute left-1/2 top-3 z-20 -translate-x-1/2" @cancel="annotationMode = false" />
          <SelectionToolbar v-else-if="actionableSelectionCount > 1 && !replayMode" class="absolute left-1/2 top-3 z-20 -translate-x-1/2" :count="actionableSelectionCount" @copy="copySelection" @duplicate="duplicateSelection" @delete="removeSelection" @clear="clearSelection" />
          <button v-else-if="selected && !replayMode" class="surface absolute left-1/2 top-3 z-10 flex h-7 -translate-x-1/2 items-center gap-1.5 rounded-md px-3 text-[11px] shadow-sm hover:bg-[var(--panel-subtle)]" @click="focusSelected"><MousePointer2 :size="12" />{{ t('designer.focusSelected') }}</button>
          <WorkflowCanvasControls
            v-if="!replayMode"
            v-model:interaction-mode="interactionMode"
            :annotation-active="annotationMode"
            :comments-active="commentMode || showComments"
            :can-copy="Boolean(selectedCanvasNodes().length)"
            :can-paste="Boolean(copiedGraph)"
            :can-delete="Boolean(selectedCanvasNodes().length || selectedCanvasEdges().length)"
            :can-undo="canUndo"
            :can-redo="canRedo"
            :zoom-percent="zoomPercent"
            @add-node="openPalette"
            @toggle-annotation="toggleAnnotationMode"
            @fit-view="fitView({ padding: 0.2 })"
            @toggle-comments="toggleCommentMode"
            @auto-layout="autoLayout"
            @copy="copySelection"
            @paste="pasteSelection"
            @delete="removeSelection"
            @undo="undo"
            @redo="redo"
            @history="openChangeHistory"
            @zoom-out="zoomOut()"
            @zoom-in="zoomIn()"
          />
          <NodePalette v-if="paletteOpen && !replayMode" v-model:query="paletteQuery" v-model:active-tab="paletteTab" class="absolute z-30" :style="paletteStyle" :sections="paletteSections" :scripts="scripts" :data-source-id="paletteSourceId || ''" :data-source-found="Boolean(paletteSourceId && nodes.some(node => node.id === paletteSourceId))" @add="add" @add-script="addScriptSnippet" @close="paletteOpen = false; paletteReplaceNodeId = null" />
          <div v-if="!replayMode" class="absolute bottom-4 left-1/2 z-20 -translate-x-1/2">
            <button class="surface flex h-8 items-center gap-1.5 rounded-lg px-3 text-[11px] font-semibold shadow-lg hover:bg-[var(--panel-subtle)]" :class="showVariableInspector && 'text-[var(--primary)]'" @click="showVariableInspector = !showVariableInspector"><ListTree :size="13" />{{ t('designer.variableInspector') }}<span class="muted">{{ allVariableGroups.reduce((total, group) => total + group.variables.length, 0) }}</span></button>
            <div v-if="showVariableInspector" class="surface absolute bottom-11 left-1/2 flex max-h-[440px] w-[min(720px,calc(100vw-96px))] -translate-x-1/2 flex-col overflow-hidden rounded-xl shadow-2xl">
              <div class="flex items-center gap-3 border-b border-[var(--border)] px-4 py-3"><span class="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><ListTree :size="16" /></span><div><h3 class="text-sm font-semibold">{{ t('designer.variableInspector') }}</h3><p class="muted mt-0.5 text-[10px]">{{ t('designer.variableInspectorHint') }}</p></div><button class="icon-button ml-auto" :aria-label="t('common.close')" @click="showVariableInspector = false"><X :size="15" /></button></div>
              <div class="border-b border-[var(--border)] p-3"><label class="flex h-8 items-center gap-2 rounded-md bg-[var(--panel-subtle)] px-2"><Search :size="13" class="muted" /><input v-model="variableSearch" class="min-w-0 flex-1 bg-transparent text-xs outline-none" :placeholder="t('designer.searchVariables')" autofocus /></label></div>
              <div class="min-h-0 flex-1 overflow-y-auto p-3"><div v-for="group in filteredVariableGroups" :key="group.nodeId" class="mb-3 overflow-hidden rounded-lg border border-[var(--border)] last:mb-0"><div class="flex items-center gap-2 bg-[var(--panel-subtle)] px-3 py-2"><span class="text-xs font-semibold">{{ group.label }}</span><code class="muted truncate text-[9px]">{{ group.nodeId }}</code><span class="muted ml-auto text-[9px]">{{ group.variables.length }}</span></div><button v-for="variable in group.variables" :key="variable.path" class="grid w-full grid-cols-[minmax(0,1fr)_88px_minmax(120px,0.8fr)_24px] items-center gap-2 border-t border-[var(--border)] px-3 py-2 text-left hover:bg-[var(--panel-subtle)]" :title="t('designer.copyVariable')" @click="copyVariableReference(variable.path)"><span class="min-w-0"><span class="block truncate text-[11px] font-medium">{{ variable.label }}</span><code class="muted mt-0.5 block truncate text-[9px]">{{ variableReference(variable.path) }}</code></span><span class="rounded bg-[var(--primary-soft)] px-1.5 py-1 text-center text-[9px] text-[var(--primary)]">{{ variable.type }}</span><pre class="max-h-14 overflow-hidden whitespace-pre-wrap break-all text-[9px] leading-4" :class="runtimeVariableValue(variable.path) === undefined ? 'text-[var(--muted)]' : 'text-[var(--text)]'">{{ formatRuntimeValue(runtimeVariableValue(variable.path)) }}</pre><Check v-if="copiedVariablePath === variable.path" :size="13" class="text-emerald-600" /><Copy v-else :size="12" class="muted" /></button></div><div v-if="!filteredVariableGroups.length" class="muted py-12 text-center text-xs">{{ t('designer.noVariableResults') }}</div></div>
            </div>
          </div>
        </section>

        <WorkflowCommentsPanel v-if="showComments" :comments="comments" :selected-id="selectedCommentId" :placement-active="commentMode" @close="closeComments" @select="selectComment" @place="toggleCommentMode" @submit="submitComment" @toggle-resolved="toggleCommentResolved" @delete="deleteCommentThread" />

        <WorkflowNodeInspector v-else-if="selected" v-model:tab="inspectorTab" :node="selected" :node-type="selectedType" :running="running" :result="selectedResult" :name-error="nodeNameError" @update:label="updateSelectedNodeLabel" @update:description="selected.data.description = $event" @run="openRunDialog(selected.id)" @help="showHelp = true" @close="clearNodeSelection">
          <template #settings>
              <label v-if="selectedType === 'note'" class="field-label">{{ t('designer.noteContent') }}<MarkdownComposer v-model="selected.data.description" class="mt-1.5" :placeholder="t('designer.noteEmpty')" :rows="6" /></label>
              <template v-if="selectedType === 'note'">
                <div class="mt-5"><h3 class="text-xs font-semibold">{{ t('designer.noteColor') }}</h3><div class="mt-2 flex gap-2"><button v-for="color in ['yellow','blue','green','rose']" :key="color" class="note-color-swatch" :class="[`swatch-${color}`, { active: selected.data.color === color }]" :aria-label="t(`designer.noteColors.${color}`)" @click="selected.data.color = color"><Check v-if="selected.data.color === color" :size="12" /></button></div></div>
              </template>
              <template v-else-if="selectedType === 'start'">
                <div class="mt-5"><h3 class="text-xs font-semibold">{{ t('designer.triggerMethods') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.triggerMethodHint') }}</p><div class="mt-2 grid grid-cols-2 gap-2" role="radiogroup"><button v-for="trigger in ['form','api','webhook','schedule']" :key="trigger" type="button" role="radio" :aria-checked="hasStartTrigger(trigger)" class="flex h-10 items-center gap-2 rounded-lg border px-3 text-left text-xs" :class="hasStartTrigger(trigger) ? 'border-[var(--primary)] bg-[var(--primary-soft)] text-[var(--primary)]' : 'border-[var(--border)]'" @click="toggleStartTrigger(trigger)"><span class="flex h-4 w-4 items-center justify-center rounded-full border" :class="hasStartTrigger(trigger) ? 'border-[var(--primary)]' : 'border-[var(--border)]'"><span v-if="hasStartTrigger(trigger)" class="h-2 w-2 rounded-full bg-[var(--primary)]"></span></span>{{ t(`designer.triggers.${trigger}`) }}</button></div></div>
                <div class="mt-5 flex items-center justify-between"><div><h3 class="text-xs font-semibold">{{ t('designer.userInputs') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.userInputsHint') }}</p></div><button class="icon-button" :title="t('designer.addInputField')" :aria-label="t('designer.addInputField')" @click="addStartInput"><Plus :size="14" /></button></div>
                <div class="mt-3 space-y-2">
                  <div v-for="(field, index) in selected.data.config.input_fields" :key="index" class="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]">
                    <div class="flex items-center gap-1 p-2">
                      <button type="button" class="flex min-w-0 flex-1 items-center gap-2 rounded-md px-1 py-1 text-left hover:bg-[var(--panel)]" @click="toggleStartField(index)">
                        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[var(--primary-soft)] text-[10px] font-semibold text-[var(--primary)]">{{ field.type === 'files' ? '[]' : field.type === 'file' ? 'F' : field.type === 'number' ? '#' : field.type === 'select' ? '⌄' : 'T' }}</span>
                        <span class="min-w-0 flex-1"><span class="block truncate font-mono text-xs font-semibold">{{ field.name || t('designer.unnamedField') }}</span><span class="muted mt-0.5 block truncate text-[10px]">{{ field.label || t('designer.fieldLabel') }} · {{ t(`designer.fieldTypes.${field.type}`) }}</span></span>
                        <span v-if="field.required" class="rounded bg-red-50 px-1.5 py-0.5 text-[9px] text-red-600 dark:bg-red-950/30">{{ t('designer.required') }}</span>
                        <ChevronRight :size="14" class="muted transition-transform" :class="expandedStartFieldIndex === Number(index) && 'rotate-90'" />
                      </button>
                      <button class="icon-button text-red-600" :aria-label="t('designer.removeInputField')" @click="removeStartInput(index)"><Trash2 :size="13" /></button>
                    </div>
                    <div v-if="expandedStartFieldIndex === Number(index)" class="border-t border-[var(--border)] bg-[var(--panel)] p-3">
                      <label class="field-label">{{ t('designer.fieldLabel') }}<InputText v-model="field.label" class="mt-1.5 !h-8" /></label>
                      <div class="mt-3 grid grid-cols-[minmax(0,1fr)_125px] gap-2"><label class="field-label">{{ t('designer.variableName') }}<InputText v-model="field.name" class="mt-1.5 !h-8 font-mono" placeholder="field_name" /></label><label class="field-label">{{ t('designer.fieldType') }}<Select v-model="field.type" class="mt-1.5 !h-8 !text-xs"><option v-for="kind in ['text','textarea','number','select','file','files']" :key="kind" :value="kind">{{ t(`designer.fieldTypes.${kind}`) }}</option></Select></label></div>
                      <template v-if="['text','textarea','select'].includes(field.type)">
                        <label class="field-label mt-3">{{ t('designer.placeholder') }}<InputText v-model="field.placeholder" class="mt-1.5 !h-8" /></label>
                        <label class="field-label mt-3">{{ t('designer.defaultValue') }}<InputText v-model="field.default_value" class="mt-1.5 !h-8" /></label>
                        <label v-if="field.type !== 'select'" class="field-label mt-3">{{ t('designer.maxLength') }}<InputText v-model.number="field.max_length" type="number" min="1" max="100000" class="mt-1.5 !h-8" /></label>
                      </template>
                      <template v-if="field.type === 'number'"><div class="mt-3 grid grid-cols-3 gap-2"><label class="field-label">{{ t('designer.defaultValue') }}<InputText v-model.number="field.default_value" type="number" class="mt-1.5 !h-8" /></label><label class="field-label">{{ t('designer.minimum') }}<InputText v-model.number="field.min" type="number" class="mt-1.5 !h-8" /></label><label class="field-label">{{ t('designer.maximum') }}<InputText v-model.number="field.max" type="number" class="mt-1.5 !h-8" /></label></div></template>
                      <div v-if="field.type === 'select'" class="mt-3"><div class="flex items-center"><h4 class="text-[11px] font-semibold">{{ t('designer.options') }}</h4><button class="icon-button ml-auto" :aria-label="t('designer.addOption')" @click="addStartFieldOption(field)"><Plus :size="13" /></button></div><div class="mt-2 space-y-2"><div v-for="(_, optionIndex) in field.options" :key="optionIndex" class="flex gap-2"><InputText v-model="field.options[optionIndex]" class="!h-8" /><button class="icon-button text-red-600" :aria-label="t('designer.removeOption')" @click="removeStartFieldOption(field, optionIndex)"><X :size="13" /></button></div><button v-if="!field.options.length" class="w-full rounded-md border border-dashed border-[var(--border)] py-3 text-[11px] text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addStartFieldOption(field)"><Plus class="mr-1 inline" :size="12" />{{ t('designer.addOption') }}</button></div></div>
                      <label class="mt-3 flex items-center gap-2 text-xs"><input v-model="field.required" type="checkbox">{{ t('designer.required') }}</label>
                    </div>
                  </div>
                </div>
                <div v-if="hasStartTrigger('schedule')" class="mt-5 rounded-lg border border-[var(--border)] p-3"><div class="flex items-center justify-between"><h3 class="text-xs font-semibold">{{ t('designer.schedule') }}</h3><label class="flex items-center gap-2 text-xs"><input v-model="selected.data.config.schedule.enabled" type="checkbox">{{ t('designer.enabled') }}</label></div><label class="field-label mt-3">Cron<InputText v-model="selected.data.config.schedule.cron" class="mt-1.5 font-mono" placeholder="0 9 * * *" /></label><label class="field-label mt-3">{{ t('settings.timezone') }}<InputText v-model="selected.data.config.schedule.timezone" class="mt-1.5" placeholder="Asia/Singapore" /></label><label class="field-label mt-3">{{ t('designer.scheduleInputs') }}<Textarea v-model="selected.data.config.schedule.inputs_json" class="mt-1.5 h-24 font-mono !text-xs" placeholder='{"message":"Daily report"}' /></label></div>
                <div v-if="hasStartTrigger('api') || hasStartTrigger('webhook')" class="mt-5 rounded-lg bg-[var(--panel-subtle)] p-3 text-[11px]"><div class="font-semibold">{{ t('designer.endpointAfterPublish') }}</div><code v-if="hasStartTrigger('api')" class="muted mt-2 block break-all">POST {{ origin }}/v1/apps/{{ workflow?.slug }}/run</code><code v-if="hasStartTrigger('webhook')" class="muted mt-2 block break-all">POST {{ origin }}/v1/apps/{{ workflow?.slug }}/webhook</code><code class="muted mt-2 block break-all">POST {{ origin }}/v1/apps/{{ workflow?.slug }}/files</code></div>
              </template>
              <template v-else-if="selectedType === 'end'">
                <div class="mt-5 flex items-center justify-between">
                  <div><h3 class="text-xs font-semibold">{{ t('designer.outputFields') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.outputFieldsHint') }}</p></div>
                  <button class="icon-button" :title="t('designer.addOutputField')" @click="addEndOutput"><Plus :size="14" /></button>
                </div>
                <div class="mt-3 space-y-3">
                  <div v-for="(output, index) in selected.data.config.outputs" :key="index" class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
                    <div class="grid grid-cols-[minmax(0,1fr)_105px_30px] gap-2">
                      <InputText v-model="output.name" class="!h-8 font-mono" :placeholder="t('designer.outputName')" />
                      <Select v-model="output.type" class="!h-8 !w-28 !text-xs">
                        <option v-for="kind in ['String','Number','Boolean','Object','Array','File','Any']" :key="kind" :value="kind">{{ kind }}</option>
                      </Select>
                      <button class="icon-button !h-8 !w-8 text-red-600" :aria-label="t('designer.removeOutputField')" @click="removeEndOutput(index)"><X :size="14" /></button>
                    </div>
                    <label class="field-label mt-3">{{ t('designer.outputValue') }}<VariableField v-model="output.value" class="mt-1.5 font-mono" :groups="variableGroups" :placeholder="t('designer.selectUpstreamOutput')" /></label>
                  </div>
                  <button v-if="!selected.data.config.outputs.length" class="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] py-5 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addEndOutput"><Plus :size="14" />{{ t('designer.addOutputField') }}</button>
                </div>
              </template>
              <template v-else>
                <LlmConfigPanel v-if="selectedType === 'llm'" :config="selected.data.config" :providers="modelProviders" :variable-groups="variableGroups" :buffers="configBuffers" :errors="configFieldErrors" @structured="updateStructuredField($event.field, $event.buffer as any)" @editing="configEditing = $event" />
                <AgentConfigPanel v-else-if="selectedType === 'agent'" :config="selected.data.config" :providers="modelProviders" :scripts="scripts" :datasets="datasets" :variable-groups="variableGroups" @provider-change="selectModelProvider" />
                <ClassifierConfigPanel v-else-if="selectedType === 'classifier'" :config="selected.data.config" :variable-groups="variableGroups" @add="addClassifierCategory" @remove="removeClassifierCategory" @connect="openPaletteForSource(selected.id, $event)" @update-keywords="updateClassifierKeywords" />
                <CodeConfigPanel v-else-if="selectedType === 'code'" :key="selected.id" :config="selected.data.config" :variable-groups="variableGroups" @editing="configEditing = $event" />
                <section v-else-if="selectedType === 'script'" class="mt-5 space-y-4">
                  <label class="field-label">{{ t('designer.workspaceScript') }}<Select v-model="selected.data.config.script_id" class="mt-1.5 !h-9 !text-xs" @change="selectScript"><option value="">{{ t('designer.selectScript') }}</option><option v-for="script in scripts" :key="script.id" :value="script.id">{{ script.name }} · v{{ script.latest_version }}</option></Select></label>
                  <p v-if="!scripts.length" class="resource-empty">{{ t('designer.noScripts') }}</p>
                  <label class="field-label">{{ t('designer.scriptVersion') }}<Select v-model="selected.data.config.version" class="mt-1.5 !h-9 !text-xs"><option value="latest">{{ t('designer.followLatest') }}</option><option v-if="selectedScript" :value="selectedScript.latest_version">v{{ selectedScript.latest_version }}</option></Select></label>
                  <JsonEditorField v-model="configBuffers.scriptInputs" :label="t('designer.scriptInputs')" :error="configFieldErrors.scriptInputs" :groups="variableGroups" @input="updateStructuredField('inputs', 'scriptInputs')" />
                </section>
                <KnowledgeConfigPanel v-else-if="selectedType === 'knowledge'" :config="selected.data.config" :datasets="datasets" :variable-groups="variableGroups" />
                <HttpConfigPanel v-else-if="selectedType === 'http'" :config="selected.data.config" :variable-groups="variableGroups" :buffers="configBuffers" :errors="configFieldErrors" @structured="updateStructuredField" />
                <TemplateConfigPanel v-else-if="selectedType === 'template'" :config="selected.data.config" :variable-groups="variableGroups" />
                <VariableAssignConfigPanel v-else-if="selectedType === 'variable'" :key="selected.id" :config="selected.data.config" :variable-groups="variableGroups" />
                <JsonEditorField v-else-if="selectedType === 'json'" v-model="configBuffers.jsonValue" class="mt-5" :label="t('designer.jsonValue')" :error="configFieldErrors.jsonValue" :groups="variableGroups" height-class="h-52" @input="updateStructuredField('value', 'jsonValue')" />
                <AggregateConfigPanel v-else-if="selectedType === 'aggregate'" :config="selected.data.config" :variable-groups="variableGroups" />
                <ParameterExtractorConfigPanel v-else-if="selectedType === 'extract'" :key="selected.id" :config="selected.data.config" :providers="modelProviders" :variable-groups="variableGroups" />
                <ListOperatorConfigPanel v-else-if="selectedType === 'list'" :key="selected.id" :config="selected.data.config" :variable-groups="variableGroups" />
                <ConditionConfigPanel v-else-if="selectedType === 'condition'" :config="selected.data.config" :variable-groups="variableGroups" @add="addConditionClause" @remove="removeConditionClause" @connect="openPaletteForSource(selected.id, $event)" />
                <HumanConfigPanel v-else-if="selectedType === 'human'" :config="selected.data.config" :variable-groups="variableGroups" @remove="removeHumanAction" @connect="openPaletteForSource(selected.id, $event)" />
                <IterationConfigPanel v-else-if="selectedType === 'iteration'" :config="selected.data.config" :variable-groups="variableGroups" />
                <LoopConfigPanel v-else-if="selectedType === 'loop'" :config="selected.data.config" :variable-groups="variableGroups" />
                <SubworkflowConfigPanel v-else-if="selectedType === 'subworkflow'" :config="selected.data.config" :workflows="subworkflows" :variable-groups="variableGroups" @select="selectSubworkflow" />
                <section v-else-if="selectedType === 'delay'" class="mt-5"><label class="field-label">{{ t('designer.delaySeconds') }}<InputText v-model.number="selected.data.config.seconds" class="mt-1.5" type="number" min="1" max="86400" /></label></section>
                <DocumentConfigPanel v-else-if="selectedType === 'document'" :config="selected.data.config" :variable-groups="variableGroups" />
                <NodeOutputPanel :node="selected" :copied-path="copiedVariablePath" @copy="copyVariableReference" />
                <ExecutionPolicyPanel v-if="executionPolicyNodeTypes.has(selectedType)" :config="selected.data.config" @connect-error="openPaletteForSource(selected.id, 'error')" />
                <details class="mt-5 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3" open @toggle="syncConfigEditor"><summary class="cursor-pointer text-xs font-semibold">{{ t('designer.advancedConfig') }}</summary><JsonEditorField v-model="configText" class="mt-3" :label="t('workflow.configuration')" :error="configError" :groups="variableGroups" height-class="h-48" @focus="configEditing = true" @blur="configEditing = false; syncConfigEditor()" @input="updateSelectedConfig" /></details>
              </template>
            <NextStepPanel v-if="!['end','note','condition','classifier','human'].includes(selectedType)" :nodes="nextNodes" @add="openPaletteForSource(selected.id)" @parallel="openPaletteForSource(selected.id)" />
          </template>
        </WorkflowNodeInspector>
      </div>
      <section v-else-if="activeSection === 'api'" class="min-h-0 flex-1 overflow-auto p-7"><div class="mx-auto max-w-4xl"><h2 class="text-xl font-semibold">{{ t('designer.apiTitle') }}</h2><p class="muted mt-1 text-sm">{{ t('designer.apiHint') }}</p><div class="surface mt-5 rounded-lg p-5"><div class="text-xs font-semibold">{{ t('designer.endpoints') }}</div><div class="mt-2 space-y-2"><code v-if="startNode?.data?.config?.triggers?.includes('form')" class="block rounded-md bg-slate-950 p-3 text-xs text-slate-100">GET {{ origin }}/apps/{{ workflow?.slug }}</code><code v-if="startNode?.data?.config?.triggers?.includes('api')" class="block rounded-md bg-slate-950 p-3 text-xs text-slate-100">POST {{ origin }}/v1/apps/{{ workflow?.slug }}/run</code><code v-if="startNode?.data?.config?.triggers?.includes('webhook')" class="block rounded-md bg-slate-950 p-3 text-xs text-slate-100">POST {{ origin }}/v1/apps/{{ workflow?.slug }}/webhook</code><code class="block rounded-md bg-slate-950 p-3 text-xs text-slate-100">POST {{ origin }}/v1/apps/{{ workflow?.slug }}/files</code></div><div class="mt-5 text-xs font-semibold">cURL</div><pre class="mt-2 overflow-auto rounded-md bg-slate-950 p-4 text-xs text-slate-100">curl -X POST '{{ origin }}/v1/apps/{{ workflow?.slug }}/run' \
  -H 'Content-Type: application/json' \
  -d '{"inputs":{"message":"Hello"}}'</pre></div></div></section>
      <section v-else-if="activeSection === 'logs'" class="min-h-0 flex-1 overflow-auto p-7"><div class="mx-auto max-w-5xl"><div class="flex items-center"><div><h2 class="text-xl font-semibold">{{ t('designer.runLogs') }}</h2><p class="muted mt-1 text-sm">{{ t('designer.logsHint') }}</p></div><Button class="ml-auto" variant="secondary" @click="loadRuns"><Activity :size="15" />{{ t('common.refresh') }}</Button></div><div class="surface mt-5 overflow-hidden rounded-lg"><div v-for="item in runs" :key="item.id" class="grid grid-cols-[160px_110px_120px_minmax(0,1fr)] border-b border-[var(--border)] px-4 py-3 text-sm last:border-0"><span>{{ new Date(item.created_at).toLocaleString() }}</span><span>{{ t(`designer.triggerShort.${item.triggered_by || 'studio'}`) }}</span><span :class="item.status === 'succeeded' ? 'text-emerald-600' : 'text-red-600'">{{ item.status }}</span><span class="truncate font-mono text-xs">{{ item.id }}</span></div><div v-if="!runs.length" class="muted py-16 text-center text-sm">{{ t('designer.noRun') }}</div></div></div></section>
      <section v-else class="min-h-0 flex-1 overflow-auto p-7"><div class="mx-auto max-w-5xl"><h2 class="text-xl font-semibold">{{ t('designer.monitoring') }}</h2><p class="muted mt-1 text-sm">{{ t('designer.monitorHint') }}</p><div class="mt-5 grid grid-cols-3 gap-4"><div class="surface rounded-lg p-5"><div class="muted text-xs">{{ t('designer.totalRuns') }}</div><div class="mt-2 text-3xl font-semibold">{{ runs.length }}</div></div><div class="surface rounded-lg p-5"><div class="muted text-xs">{{ t('designer.successRuns') }}</div><div class="mt-2 text-3xl font-semibold text-emerald-600">{{ runs.filter(r => r.status === 'succeeded').length }}</div></div><div class="surface rounded-lg p-5"><div class="muted text-xs">{{ t('designer.failedRuns') }}</div><div class="mt-2 text-3xl font-semibold text-red-600">{{ runs.filter(r => r.status === 'failed').length }}</div></div></div></div></section>
    </div>
    <ModalShell v-model="showChangeHistory" :title="t('designer.changeHistory')" :description="t('designer.localHistoryHint')" body-class="max-h-[430px] p-2"><button v-for="entry in localHistoryEntries" :key="entry.index" class="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left hover:bg-[var(--panel-subtle)]" :class="{ 'bg-[var(--primary-soft)]': entry.index === historyIndex }" @click="restoreLocalSnapshot(entry.index)"><span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full" :class="entry.index === historyIndex ? 'bg-[var(--primary)] text-white' : 'bg-[var(--panel-subtle)] text-[var(--muted)]'"><History :size="14" /></span><span class="min-w-0 flex-1"><span class="block text-xs font-semibold">{{ entry.index === historyIndex ? t('designer.currentState') : t('designer.changeSnapshot', { index: entry.index + 1 }) }}</span><span class="muted mt-1 block text-[10px]">{{ t('designer.historyEntry', { nodes: entry.state.nodes.length, edges: entry.state.edges.length }) }}</span></span><span class="muted text-[10px]">{{ entry.time?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }}</span></button></ModalShell>
    <ModalShell v-model="showHistory" :title="t('designer.history')" :description="t('designer.versionHistoryHint')" max-width="max-w-2xl" body-class="max-h-[520px] space-y-2 p-4"><div v-for="item in versions" :key="item.id" class="rounded-lg border border-[var(--border)] p-4"><div class="flex items-start gap-3"><span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-xs font-bold text-[var(--primary)]">v{{ item.version }}</span><div class="min-w-0 flex-1"><div class="flex items-center gap-2 text-sm font-semibold">{{ item.change_note }}<span v-if="item.id === workflow?.published_version_id" class="rounded bg-emerald-50 px-1.5 py-0.5 text-[9px] text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">{{ t('designer.currentPublished') }}</span></div><div class="muted mt-1 text-[10px]">{{ new Date(item.created_at).toLocaleString() }}</div><div class="mt-2 flex flex-wrap gap-1.5 text-[10px]"><span class="rounded bg-emerald-50 px-2 py-1 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">+{{ versionDiff(item).added }} {{ t('designer.nodesShort') }}</span><span class="rounded bg-red-50 px-2 py-1 text-red-700 dark:bg-red-950/30 dark:text-red-300">-{{ versionDiff(item).removed }} {{ t('designer.nodesShort') }}</span><span class="rounded bg-amber-50 px-2 py-1 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">~{{ versionDiff(item).changed }} {{ t('designer.nodesShort') }}</span><span class="rounded bg-[var(--panel-subtle)] px-2 py-1 text-[var(--muted)]">{{ versionDiff(item).versionEdges }} → {{ versionDiff(item).currentEdges }} {{ t('designer.edgesShort') }}</span></div></div><Button variant="secondary" @click="pendingRestoreVersion = item">{{ t('designer.restoreDraft') }}</Button></div></div><div v-if="!versions.length" class="muted py-12 text-center text-sm">{{ t('common.empty') }}</div></ModalShell>
    <ModalShell :model-value="Boolean(pendingRestoreVersion)" :title="t('designer.restoreConfirmTitle', { version: pendingRestoreVersion?.version })" max-width="max-w-md" @update:model-value="pendingRestoreVersion = null"><div class="flex h-10 w-10 items-center justify-center rounded-full bg-amber-50 text-amber-600 dark:bg-amber-950/40"><AlertTriangle :size="20" /></div><p class="muted mt-4 text-sm leading-6">{{ t('designer.restoreConfirmText') }}</p><template #footer><Button variant="secondary" :disabled="restoringVersion" @click="pendingRestoreVersion = null">{{ t('common.cancel') }}</Button><Button :loading="restoringVersion" @click="restorePublishedVersion">{{ t('designer.restoreDraft') }}</Button></template></ModalShell>
    <RunDebugPanel :open="showRunDialog" :title="replayMode ? `${t(`designer.triggerShort.${selectedRun?.triggered_by || 'studio'}`)} (${selectedRun ? new Date(selectedRun.created_at).toLocaleTimeString() : ''})` : runTargetNodeId ? t('designer.runNodeTitle', { name: runTargetLabel }) : t('workflow.run')" :fields="startFields" :inputs="runInputs" :uploading-field="uploadingField" :result="result" :error="runError" :running="running" :node-run="Boolean(runTargetNodeId)" :readonly="replayMode" :node-labels="runNodeLabels" @close="replayMode ? exitReplayMode() : showRunDialog = false" @run="run" @file-change="uploadRunFile" @focus-node="focusTraceNode" />
    <ModalShell v-model="showApprovals" :title="t('designer.pendingApprovals')" :description="t('designer.pendingApprovalsHint')" max-width="max-w-3xl">
      <div class="grid min-h-96 grid-cols-[220px_minmax(0,1fr)] overflow-hidden rounded-lg border border-[var(--border)]">
        <aside class="border-r border-[var(--border)] bg-[var(--panel-subtle)] p-2"><button v-for="item in approvals" :key="item.id" class="mb-1 w-full rounded-md px-3 py-2.5 text-left" :class="selectedApproval?.id === item.id ? 'bg-[var(--primary-soft)] text-[var(--primary)]' : 'hover:bg-[var(--panel)]'" @click="selectedApproval = item; approvalComment = ''"><div class="truncate text-xs font-semibold">{{ item.request?.title || item.node_id }}</div><div class="mt-1 flex items-center gap-2 text-[9px]"><span :class="item.status === 'pending' ? 'text-amber-600' : 'text-emerald-600'">{{ t(`designer.approvalStatus.${item.status}`) }}</span><span class="muted">{{ new Date(item.created_at).toLocaleString() }}</span></div></button><div v-if="!approvals.length" class="muted py-16 text-center text-xs">{{ t('designer.noApprovals') }}</div></aside>
        <section v-if="selectedApproval" class="p-5"><div class="flex items-start gap-3"><span class="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-amber-600 dark:bg-amber-950/40"><UserCheck :size="18" /></span><div><h3 class="text-sm font-semibold">{{ selectedApproval.request?.title }}</h3><p class="muted mt-1 text-[10px]">{{ t('designer.approvalExpires', { time: selectedApproval.expires_at ? new Date(selectedApproval.expires_at).toLocaleString() : '-' }) }}</p></div></div><pre class="mt-5 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-4 text-xs leading-6">{{ selectedApproval.request?.form_content }}</pre><label v-if="selectedApproval.status === 'pending'" class="field-label mt-5">{{ t('designer.approvalComment') }}<Textarea v-model="approvalComment" class="mt-1.5 h-24" :placeholder="t('designer.approvalCommentPlaceholder')" /></label><div v-if="selectedApproval.status === 'pending'" class="mt-5 flex flex-wrap justify-end gap-2"><Button v-for="action in selectedApproval.request?.actions || []" :key="action.id" :variant="action.style === 'primary' ? 'primary' : action.style === 'danger' ? 'danger' : 'secondary'" :loading="respondingApproval" @click="respondApproval(action)">{{ action.label }}</Button></div><div v-else class="mt-5 rounded-lg bg-[var(--panel-subtle)] p-3 text-xs"><span class="font-semibold">{{ t('designer.approvalResponse') }}</span><pre class="mt-2 whitespace-pre-wrap">{{ JSON.stringify(selectedApproval.response, null, 2) }}</pre></div><AlertBanner class="mt-4" :message="runError" tone="error" /></section>
        <section v-else class="muted flex items-center justify-center text-xs">{{ t('designer.selectApproval') }}</section>
      </div>
    </ModalShell>
    <ModalShell v-model="showHelp" :title="t('designer.help')"><p class="muted text-sm leading-6">{{ t('designer.helpText') }}</p></ModalShell>
    <DesignerCommandPalette :open="showCommandPalette" :nodes="nodes" :add-items="commandAddItems" :actions="commandActions" @close="showCommandPalette = false" @focus="focusCommandNode" @add="addCommandNode" @action="executeCommand" />
  </div>
</template>

<style>
.workflow-canvas .vue-flow__minimap { right: 14px !important; bottom: 58px !important; width: 170px !important; height: 105px !important; }
.workflow-canvas.replay-mode .vue-flow__node { pointer-events: none; }
.workflow-canvas.annotation-mode .vue-flow__pane { cursor: crosshair; }
.workflow-canvas.middle-panning .vue-flow__pane, .workflow-canvas.middle-panning .vue-flow__node { cursor: grabbing !important; }
.designer-sidebar { letter-spacing: 0; }.icon-button { display: inline-flex; width: 30px; height: 30px; flex: none; align-items: center; justify-content: center; border-radius: 7px; color: var(--muted); }.icon-button:hover { background: var(--panel-subtle); color: var(--text); }.side-nav { display: flex; width: 100%; height: 36px; align-items: center; gap: 10px; border-radius: 7px; padding: 0 10px; color: var(--muted); font-size: 13px; }.side-nav:hover { background: var(--panel-subtle); color: var(--text); }.side-nav.active { background: var(--primary-soft); color: var(--primary); font-weight: 600; }.workflow-canvas { background: var(--app-bg); }.workflow-canvas .vue-flow__node { border: 0; background: transparent; padding: 0; box-shadow: none; }.workflow-canvas .vue-flow__handle { width: 9px; height: 9px; border: 2px solid var(--panel); background: var(--primary); }.workflow-canvas .vue-flow__handle.quick-add-handle { width: 20px; height: 20px; border: 0; background: transparent; }.workflow-canvas .vue-flow__edge-path { stroke: #98a2b3; stroke-width: 1.5; }.canvas-mode-button { display: flex; width: 36px; height: 36px; align-items: center; justify-content: center; color: var(--muted); }.canvas-mode-button:hover { background: var(--panel-subtle); color: var(--text); }.canvas-mode-button.active { background: var(--primary-soft); color: var(--primary); }.canvas-action-row { display: flex; width: 100%; height: 32px; align-items: center; gap: 8px; border-radius: 6px; padding: 0 9px; font-size: 12px; }.canvas-action-row:hover:not(:disabled) { background: var(--panel-subtle); }.canvas-action-row:disabled { cursor: not-allowed; opacity: .4; }.inspector-tab { height: 40px; border-bottom: 2px solid transparent; padding: 0 12px; color: var(--muted); font-size: 12px; }.inspector-tab.active { border-color: var(--primary); color: var(--primary); font-weight: 600; }.field-label { display: block; color: var(--text); font-size: 12px; font-weight: 600; }.vue-flow__minimap { overflow: hidden; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); }
.resource-empty { border: 1px dashed var(--border); border-radius: 7px; background: var(--panel-subtle); padding: 10px; color: var(--muted); font-size: 11px; }.field-error { margin-top: 6px; color: #d92d20; font-size: 11px; }
.canvas-history-button { display: flex; width: 34px; height: 34px; align-items: center; justify-content: center; color: var(--muted); }.canvas-history-button:hover:not(:disabled) { background: var(--panel-subtle); color: var(--primary); }.canvas-history-button:disabled { cursor: not-allowed; opacity: .35; }
.run-detail-heading { color: var(--muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }.run-detail-code { margin-top: 8px; max-height: 260px; overflow: auto; white-space: pre-wrap; border: 1px solid var(--border); border-radius: 8px; background: var(--panel-subtle); padding: 12px; font-size: 11px; line-height: 1.6; }
.note-color-swatch { display: flex; width: 30px; height: 30px; align-items: center; justify-content: center; border: 2px solid transparent; border-radius: 7px; color: #344054; }.note-color-swatch.active { border-color: var(--primary); box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 82%); }.swatch-yellow { background: #fde68a; }.swatch-blue { background: #bfdbfe; }.swatch-green { background: #bbf7d0; }.swatch-rose { background: #fecdd3; }
</style>
