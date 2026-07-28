import { computed, ref, type ComputedRef, type Ref } from 'vue'
import type { Edge, Node } from '@vue-flow/core'
import api from '@/api/client'
import { consumeRunEvents } from '@/api/runEvents'
import { coerceWorkflowInputValues, createWorkflowInputValues } from '@/utils/workflowInputs'
import { buildRunOverlay, clearRunOverlay as clearGraphRunOverlay } from '@/utils/workflowRunOverlay'

interface WorkflowRunOptions {
  workspaceId: ComputedRef<string>
  workflowId: ComputedRef<string>
  startFields: ComputedRef<any[]>
  nodes: Ref<Node[]>
  selected: Ref<Node | null>
  inspectorTab: Ref<string>
  activeSection: Ref<string>
  currentEdges: () => Edge[]
  commitEdges: (edges: Edge[]) => void
  fitView: (options?: any) => Promise<boolean> | void
}

export function useWorkflowRuns(options: WorkflowRunOptions) {
  const running = ref(false)
  const result = ref<any>(null)
  const runs = ref<any[]>([])
  const showRunDialog = ref(false)
  const runInputs = ref<Record<string, any>>({})
  const runError = ref('')
  const uploadingField = ref('')
  const showRunHistory = ref(false)
  const selectedRun = ref<any>(null)
  const runTargetNodeId = ref<string | null>(null)
  const nodeResults = ref<Record<string, any>>({})
  const runtimeRunId = ref('')
  const approvals = ref<any[]>([])
  const selectedApproval = ref<any>(null)
  const showApprovals = ref(false)
  const approvalComment = ref('')
  const respondingApproval = ref(false)

  const replayMode = computed(() => Boolean(runtimeRunId.value && selectedRun.value))
  const selectedResult = computed<any>(() => options.selected.value ? nodeResults.value[options.selected.value.id] : null)
  const runTargetLabel = computed(() => options.nodes.value.find(node => node.id === runTargetNodeId.value)?.data?.label || '')
  const runNodeLabels = computed<Record<string, string>>(() => Object.fromEntries(
    options.nodes.value.map(node => [node.id, String(node.data?.label || node.id)]),
  ))
  const pendingApprovals = computed(() => approvals.value.filter(item => item.status === 'pending'))

  function openRunDialog(nodeId: string | null = null) {
    runTargetNodeId.value = nodeId
    runInputs.value = createWorkflowInputValues(options.startFields.value)
    runError.value = ''
    showRunDialog.value = true
  }

  async function uploadRunFile(field: any, event: Event) {
    const input = event.target as HTMLInputElement
    const files = Array.from(input.files || [])
    if (!files.length) return
    uploadingField.value = field.name
    runError.value = ''
    try {
      const uploaded = []
      for (const file of files) {
        const form = new FormData()
        form.append('file', file)
        uploaded.push((await api.post(`/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/files`, form)).data)
      }
      runInputs.value[field.name] = field.type === 'files' ? uploaded : uploaded[0]
    } catch (cause: any) {
      runError.value = cause.response?.data?.detail || String(cause)
    } finally {
      uploadingField.value = ''
    }
  }

  function applyRunOverlay(runRecord: any) {
    const overlay = buildRunOverlay(options.nodes.value as any[], options.currentEdges() as any[], runRecord)
    options.nodes.value = overlay.nodes as Node[]
    options.commitEdges(overlay.edges as Edge[])
    nodeResults.value = overlay.nodeResults
    runtimeRunId.value = overlay.runId
  }

  function clearRunOverlay() {
    const cleared = clearGraphRunOverlay(options.nodes.value as any[], options.currentEdges() as any[])
    options.nodes.value = cleared.nodes as Node[]
    options.commitEdges(cleared.edges as Edge[])
    nodeResults.value = {}
    runtimeRunId.value = ''
  }

  async function loadRuns() {
    runs.value = (await api.get(
      `/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/runs`,
      { params: { limit: 20, offset: 0 } },
    )).data.items
  }

  async function loadApprovals() {
    approvals.value = (await api.get(
      `/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/approvals`,
    )).data
  }

  async function openApprovals(runId = '') {
    await loadApprovals()
    selectedApproval.value = approvals.value.find(item => item.status === 'pending' && (!runId || item.run_id === runId)) || approvals.value[0] || null
    approvalComment.value = ''
    showApprovals.value = true
  }

  async function run() {
    running.value = true
    runError.value = ''
    result.value = null
    clearRunOverlay()
    try {
      const inputs = coerceWorkflowInputValues(options.startFields.value, runInputs.value)
      const path = runTargetNodeId.value
        ? `/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/nodes/${runTargetNodeId.value}/run`
        : `/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/run`
      result.value = (await api.post(path, { inputs })).data
      if (!runTargetNodeId.value && result.value.status === 'pending') {
        let streamedText = ''
        await consumeRunEvents(`/api/v1/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/runs/${result.value.id}/events`, event => {
          if (event.type === 'token') {
            streamedText += String(event.delta || '')
            result.value = { ...result.value, status: 'running', outputs: { text: streamedText } }
          } else if (event.status && ['run_started', 'run_finished'].includes(String(event.type))) {
            result.value = { ...result.value, status: event.status }
          }
        })
        result.value = (await api.get(`/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/runs/${result.value.id}`)).data
      }
      applyRunOverlay(result.value)
      options.inspectorTab.value = 'run'
      await loadRuns()
      if (result.value.status === 'waiting') await openApprovals(result.value.id)
    } catch (cause: any) {
      runError.value = cause.response?.data?.detail || String(cause)
    } finally {
      running.value = false
    }
  }

  async function respondApproval(action: any) {
    if (!selectedApproval.value || selectedApproval.value.status !== 'pending') return
    respondingApproval.value = true
    runError.value = ''
    try {
      const approval = selectedApproval.value
      const { data } = await api.post(
        `/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/runs/${approval.run_id}/approvals/${approval.id}/respond`,
        { action_id: action.id, comment: approvalComment.value, data: {} },
      )
      result.value = data
      await consumeRunEvents(`/api/v1/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/runs/${data.id}/events`, () => {})
      result.value = (await api.get(`/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/runs/${data.id}`)).data
      applyRunOverlay(result.value)
      await Promise.all([loadRuns(), loadApprovals()])
      selectedApproval.value = approvals.value.find(item => item.status === 'pending' && item.run_id === data.id) || approvals.value.find(item => item.id === approval.id) || null
      if (data.status !== 'waiting') showApprovals.value = false
    } catch (cause: any) {
      runError.value = cause.response?.data?.detail || String(cause)
    } finally {
      respondingApproval.value = false
    }
  }

  async function openRunHistory() {
    await loadRuns()
    showRunHistory.value = true
  }

  async function replayRun(runRecord: any) {
    const detail = (await api.get(
      `/workspaces/${options.workspaceId.value}/workflows/${options.workflowId.value}/runs/${runRecord.id}`,
    )).data
    selectedRun.value = detail
    result.value = detail
    applyRunOverlay(detail)
    showRunHistory.value = false
    showRunDialog.value = true
    runTargetNodeId.value = null
    options.selected.value = null
    options.activeSection.value = 'orchestration'
    setTimeout(() => options.fitView({ padding: 0.2, duration: 300 }), 0)
  }

  function exitReplayMode() {
    clearRunOverlay()
    selectedRun.value = null
    showRunDialog.value = false
  }

  return {
    approvalComment,
    approvals,
    applyRunOverlay,
    clearRunOverlay,
    exitReplayMode,
    loadApprovals,
    loadRuns,
    nodeResults,
    openApprovals,
    openRunDialog,
    openRunHistory,
    pendingApprovals,
    replayMode,
    replayRun,
    respondingApproval,
    respondApproval,
    result,
    run,
    runError,
    runInputs,
    running,
    runNodeLabels,
    runs,
    runTargetLabel,
    runTargetNodeId,
    runtimeRunId,
    selectedApproval,
    selectedResult,
    selectedRun,
    showApprovals,
    showRunDialog,
    showRunHistory,
    uploadingField,
    uploadRunFile,
  }
}
