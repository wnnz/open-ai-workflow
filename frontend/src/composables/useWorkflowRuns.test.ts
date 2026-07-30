import { computed, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/api/client'
import { useWorkflowRuns } from './useWorkflowRuns'

vi.mock('@/api/client', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

describe('useWorkflowRuns', () => {
  beforeEach(() => vi.clearAllMocks())

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
})
