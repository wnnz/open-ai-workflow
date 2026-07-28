export type ModelProviderTemplate = {
  base_url: string
  model: string
  privateNetwork?: boolean
}

export const modelProviderTemplates: Record<string, ModelProviderTemplate> = {
  OpenAI: { base_url: 'https://api.openai.com/v1', model: 'gpt-4.1-mini' },
  DeepSeek: { base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  Qwen: { base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  Moonshot: { base_url: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k' },
  Ollama: { base_url: 'http://host.docker.internal:11434/v1', model: 'qwen3', privateNetwork: true },
  vLLM: { base_url: 'http://host.docker.internal:8000/v1', model: 'default', privateNetwork: true },
}
