export const executionPolicyNodeTypes = new Set([
  'llm', 'image', 'agent', 'code', 'script', 'template', 'variable', 'json', 'aggregate',
  'extract', 'list', 'http', 'iteration', 'loop', 'delay', 'subworkflow', 'document', 'answer_filler',
])

type Translate = (key: string) => string

export function useDesignerNodeConfig(t: Translate) {
  function createClassifierCategory(category: any = {}) {
    return {
      id: category.id || crypto.randomUUID().slice(0, 12),
      name: '',
      description: '',
      keywords: [],
      ...category,
    }
  }

  function defaultNodeConfig(type: string) {
    const defaults: Record<string, any> = {
      end: { outputs: [{ name: 'result', type: 'Any', value: '' }] },
      llm: { provider_id: '', model: '', temperature: 0.7, top_p: 1, max_tokens: 1024, messages: [{ role: 'system', content: '' }, { role: 'user', content: '{{inputs.message}}' }], prompt: '', context: '', vision: { enabled: false, variable: '', detail: 'high' }, reasoning: { separate: false }, response_format: 'text', response_schema: { type: 'object', properties: {} } },
      image: { provider_id: '', model: 'gpt-image-2', prompt: '{{inputs.prompt}}', size: '{{inputs.resolution}}', count: '{{inputs.count}}', quality: 'high', output_format: 'webp', output_compression: 80, background: 'auto', timeout_seconds: 600 },
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
      http: { method: 'GET', url: '', timeout_seconds: 30, max_response_bytes: 2000000, follow_redirects: false, query: {}, headers: {}, auth: { type: 'none', token: '', username: '', password: '', key: '', value: '', location: 'header' }, body_type: 'json', body: {} },
      condition: { logical_operator: 'and', conditions: [{ variable: '', operator: 'equals', value: '' }], expression: '' },
      human: { submission_methods: ['studio'], form_content: '', actions: [{ id: 'approve', label: t('designer.approve'), value: 'approved', style: 'primary' }, { id: 'reject', label: t('designer.reject'), value: 'rejected', style: 'danger' }], timeout_minutes: 4320 },
      iteration: { source: '', item_variable: 'item', output: '', mode: 'sequential', concurrency: 1 },
      loop: { condition: '', max_iterations: 10, output: '' },
      wait: { mode: 'all' },
      delay: { seconds: 60 },
      subworkflow: { workflow_id: '', inputs: {} },
      document: { operation: 'extract', source: '', extract_mode: 'text', page_range: '', ocr_fallback: false },
      answer_filler: { source: '', answers: '', output_name: '英语试卷_已作答.docx' },
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

  function normalizeEndOutputs(outputs: any, inputFields: any[]) {
    if (Array.isArray(outputs)) return outputs.map(output => ({ type: 'Any', ...output }))
    if (outputs && typeof outputs === 'object') return Object.entries(outputs).map(([name, value]) => ({ name, type: 'Any', value }))
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

  function normalizeImageConfig(config: any) {
    const normalized = { ...defaultNodeConfig('image'), ...(config || {}) }
    if (!Object.prototype.hasOwnProperty.call(config || {}, 'size')) delete normalized.size
    return normalized
  }

  function normalizeHumanConfig(config: any) {
    const normalized = { ...defaultNodeConfig('human'), ...(config || {}) }
    normalized.form_content = config?.form_content || config?.instructions || ''
    normalized.submission_methods = Array.isArray(config?.submission_methods) && config.submission_methods.length ? config.submission_methods : ['studio']
    normalized.actions = Array.isArray(config?.actions) && config.actions.length ? config.actions : defaultNodeConfig('human').actions
    return normalized
  }

  return {
    classifierBranchLabel,
    createClassifierCategory,
    defaultNodeConfig,
    normalizeClassifierConfig,
    normalizeConditionConfig,
    normalizeEndOutputs,
    normalizeExecutionPolicy,
    normalizeHumanConfig,
    normalizeImageConfig,
    normalizeLlmConfig,
    normalizeStartField,
  }
}
