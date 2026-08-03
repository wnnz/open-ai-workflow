import { computed, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/api/client'
import { consumeRunEvents } from '@/api/runEvents'
import { useWorkflowRuns } from './useWorkflowRuns'

vi.mock('@/api/client', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))
vi.mock('@/api/runEvents', () => ({ consumeRunEvents: vi.fn() }))

describe('useWorkflowRuns', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads the latest 100 runs for the embedded history view', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { items: [{ id: 'run-1' }] } })
    const workflowRuns = useWorkflowRuns({
      workspaceId: computed(() => 'workspace-1'),
      workflowId: computed(() => 'workflow-1'),
      startFields: computed(() => []),
      nodes: ref<any[]>([]),
      selected: ref<any>(null),
      inspectorTab: ref('settings'),
      activeSection: ref('logs'),
      currentEdges: () => [],
      commitEdges: vi.fn(),
      fitView: vi.fn(),
    })

    await workflowRuns.loadRuns()

    expect(api.get).toHaveBeenCalledWith('/workspaces/workspace-1/workflows/workflow-1/runs', { params: { limit: 100, offset: 0 } })
    expect(workflowRuns.runs.value).toEqual([{ id: 'run-1' }])
  })

  it('opens a historical run without leaving the logs section', async () => {
    const detail = { id: 'run-1', status: 'succeeded', trace: [] }
    vi.mocked(api.get).mockResolvedValueOnce({ data: detail })
    const activeSection = ref('logs')
    const fitView = vi.fn()
    const workflowRuns = useWorkflowRuns({
      workspaceId: computed(() => 'workspace-1'),
      workflowId: computed(() => 'workflow-1'),
      startFields: computed(() => []),
      nodes: ref<any[]>([]),
      selected: ref<any>(null),
      inspectorTab: ref('settings'),
      activeSection,
      currentEdges: () => [],
      commitEdges: vi.fn(),
      fitView,
    })

    await workflowRuns.replayRun({ id: 'run-1' })

    expect(activeSection.value).toBe('logs')
    expect(workflowRuns.showRunDialog.value).toBe(true)
    expect(workflowRuns.replayMode.value).toBe(true)
    expect(fitView).not.toHaveBeenCalled()
  })

  it('loads the latest node traces without applying a replay overlay', async () => {
    const trace = { node_id: 'image', node_type: 'image', status: 'succeeded', output: { images: [] } }
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { items: [{ id: 'run-1' }] } })
      .mockResolvedValueOnce({ data: { id: 'run-1', trace: [trace] } })

    const nodes = ref<any[]>([
      { id: 'start', data: { nodeType: 'start' } },
      { id: 'image', data: { nodeType: 'image' } },
    ])
    const selected = ref<any>(nodes.value[1])
    const commitEdges = vi.fn()
    const workflowRuns = useWorkflowRuns({
      workspaceId: computed(() => 'workspace-1'),
      workflowId: computed(() => 'workflow-1'),
      startFields: computed(() => []),
      nodes,
      selected,
      inspectorTab: ref('settings'),
      activeSection: ref('orchestration'),
      currentEdges: () => [],
      commitEdges,
      fitView: vi.fn(),
    })

    await workflowRuns.loadLatestRunResults()

    expect(api.get).toHaveBeenNthCalledWith(1, '/workspaces/workspace-1/workflows/workflow-1/runs', { params: { limit: 1, offset: 0 } })
    expect(api.get).toHaveBeenNthCalledWith(2, '/workspaces/workspace-1/workflows/workflow-1/runs/run-1')
    expect(workflowRuns.selectedResult.value).toEqual(trace)
    expect(nodes.value.every(node => node.data.runtimeStatus === undefined)).toBe(true)
    expect(commitEdges).not.toHaveBeenCalled()
  })

  it('cancels the active run and refreshes history', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { id: 'run-1', status: 'cancelled', cancel_requested_at: '2026-08-03T00:00:00Z' } })
    vi.mocked(api.get).mockResolvedValueOnce({ data: { items: [{ id: 'run-1', status: 'cancelled' }] } })
    const workflowRuns = useWorkflowRuns({
      workspaceId: computed(() => 'workspace-1'),
      workflowId: computed(() => 'workflow-1'),
      startFields: computed(() => []),
      nodes: ref<any[]>([]),
      selected: ref<any>(null),
      inspectorTab: ref('settings'),
      activeSection: ref('logs'),
      currentEdges: () => [],
      commitEdges: vi.fn(),
      fitView: vi.fn(),
    })
    workflowRuns.result.value = { id: 'run-1', status: 'running' }

    await workflowRuns.cancelRun()

    expect(api.post).toHaveBeenCalledWith('/workspaces/workspace-1/workflows/workflow-1/runs/run-1/cancel')
    expect(workflowRuns.result.value.status).toBe('cancelled')
    expect(workflowRuns.runs.value[0].status).toBe('cancelled')
  })

  it('retries a historical run and follows the new run to completion', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { id: 'run-2', status: 'pending', retry_of_run_id: 'run-1' } })
    vi.mocked(consumeRunEvents).mockImplementationOnce(async (_url, onEvent) => { onEvent({ type: 'run_finished', status: 'succeeded' }) })
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { id: 'run-2', status: 'succeeded', outputs: {}, trace: [] } })
      .mockResolvedValueOnce({ data: { items: [{ id: 'run-2', status: 'succeeded' }] } })
    const workflowRuns = useWorkflowRuns({
      workspaceId: computed(() => 'workspace-1'),
      workflowId: computed(() => 'workflow-1'),
      startFields: computed(() => []),
      nodes: ref<any[]>([]),
      selected: ref<any>(null),
      inspectorTab: ref('settings'),
      activeSection: ref('logs'),
      currentEdges: () => [],
      commitEdges: vi.fn(),
      fitView: vi.fn(),
    })
    workflowRuns.result.value = { id: 'run-1', status: 'failed' }
    workflowRuns.selectedRun.value = workflowRuns.result.value

    await workflowRuns.retryRun()

    expect(api.post).toHaveBeenCalledWith('/workspaces/workspace-1/workflows/workflow-1/runs/run-1/retry')
    expect(consumeRunEvents).toHaveBeenCalledWith(
      '/api/v1/workspaces/workspace-1/workflows/workflow-1/runs/run-2/events',
      expect.any(Function),
    )
    expect(workflowRuns.result.value.status).toBe('succeeded')
    expect(workflowRuns.replayMode.value).toBe(false)
  })
})
