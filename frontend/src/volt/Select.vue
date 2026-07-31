<script setup lang="ts">
import { computed, nextTick, onMounted, onUpdated, ref, useAttrs, watch } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

export type SelectOption = {
  label: string
  value: string | number
  disabled?: boolean
}

defineOptions({ inheritAttrs: false })
const props = withDefaults(defineProps<{
  modelValue?: string | number | null
  options?: SelectOption[]
  editable?: boolean
  allowCustomValue?: boolean
  filterOptions?: boolean
  highlightMatches?: boolean
  highlightFirstMatch?: boolean
  openOnFocus?: boolean
  openOnOptionsChange?: boolean
  placeholder?: string
  disabled?: boolean
  required?: boolean
  controlClass?: string
  showOptionsLabel?: string
  optionsLabel?: string
  maxMenuHeight?: string
}>(), {
  modelValue: '',
  options: () => [],
  editable: false,
  allowCustomValue: false,
  filterOptions: true,
  highlightMatches: true,
  highlightFirstMatch: true,
  openOnFocus: true,
  openOnOptionsChange: false,
  placeholder: '',
  disabled: false,
  required: false,
  controlClass: '',
  showOptionsLabel: 'Show options',
  optionsLabel: 'Options',
  maxMenuHeight: '14rem',
})
const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  change: [event: Event]
}>()

const attrs = useAttrs()
const forwardedAttrs = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
const menuId = `select-options-${Math.random().toString(36).slice(2, 9)}`
const open = ref(false)
const query = ref('')
const activeIndex = ref(-1)
const optionsElement = ref<HTMLElement | null>(null)
const nativeSelectElement = ref<HTMLSelectElement | null>(null)
const slotOptions = ref<SelectOption[]>([])
function syncSlotOptions() {
  const nextOptions = Array.from(nativeSelectElement.value?.options || []).map((option) => ({
    value: option.value,
    label: option.label || option.textContent || option.value,
    disabled: option.disabled,
  }))
  const unchanged = nextOptions.length === slotOptions.value.length && nextOptions.every((option, index) => (
    option.value === slotOptions.value[index]?.value
    && option.label === slotOptions.value[index]?.label
    && option.disabled === slotOptions.value[index]?.disabled
  ))
  if (!unchanged) {
    slotOptions.value = nextOptions
    if (!props.editable) query.value = optionLabel(props.modelValue)
  }
}
onMounted(syncSlotOptions)
onUpdated(syncSlotOptions)
const effectiveOptions = computed(() => props.options.length ? props.options : slotOptions.value)

function optionLabel(value: string | number | null | undefined) {
  const option = effectiveOptions.value.find((item) => String(item.value) === String(value ?? ''))
  return option?.label ?? String(value ?? '')
}
watch(() => props.modelValue, (value) => {
  query.value = optionLabel(value)
}, { immediate: true })

const visibleOptions = computed(() => {
  if (!props.editable || !props.filterOptions) return effectiveOptions.value
  const needle = query.value.trim().toLocaleLowerCase()
  if (!needle) return effectiveOptions.value
  return effectiveOptions.value.filter((option) => option.label.toLocaleLowerCase().includes(needle))
})

function matchingSegments(label: string) {
  if (!props.editable || !props.highlightMatches) return [{ text: label, match: false }]
  const needle = query.value.trim().toLocaleLowerCase()
  if (!needle) return [{ text: label, match: false }]
  const lowerLabel = label.toLocaleLowerCase()
  const segments: Array<{ text: string; match: boolean }> = []
  let cursor = 0
  let matchAt = lowerLabel.indexOf(needle)
  while (matchAt >= 0) {
    if (matchAt > cursor) segments.push({ text: label.slice(cursor, matchAt), match: false })
    const matchEnd = matchAt + needle.length
    segments.push({ text: label.slice(matchAt, matchEnd), match: true })
    cursor = matchEnd
    matchAt = lowerLabel.indexOf(needle, cursor)
  }
  if (cursor < label.length) segments.push({ text: label.slice(cursor), match: false })
  return segments.length ? segments : [{ text: label, match: false }]
}

function emitChange(value: string | number) {
  emit('update:modelValue', value)
  const event = new Event('change')
  Object.defineProperty(event, 'target', { value: { value: String(value) } })
  emit('change', event)
}

async function syncActiveOption() {
  if (!visibleOptions.value.length) {
    activeIndex.value = -1
    return
  }
  const needle = query.value.trim().toLocaleLowerCase()
  const matchingIndex = needle
    ? visibleOptions.value.findIndex((option) => option.label.toLocaleLowerCase().includes(needle))
    : 0
  const selectedIndex = visibleOptions.value.findIndex((option) => (
    String(option.value) === String(props.modelValue ?? '')
  ))
  activeIndex.value = props.highlightFirstMatch
    ? matchingIndex
    : (selectedIndex >= 0 ? selectedIndex : matchingIndex)
  await nextTick()
  if (activeIndex.value < 0) return
  optionsElement.value?.querySelector<HTMLElement>(`[data-option-index="${activeIndex.value}"]`)
    ?.scrollIntoView?.({ block: 'nearest' })
}

function openMenu() {
  if (props.disabled || !effectiveOptions.value.length) return
  open.value = true
  void syncActiveOption()
}
function closeMenu() {
  open.value = false
}
function toggleMenu() {
  if (open.value) closeMenu()
  else openMenu()
}
function selectOption(option: SelectOption) {
  if (option.disabled) return
  query.value = option.label
  emitChange(option.value)
  closeMenu()
}
function handleInput(value: string) {
  query.value = value
  if (props.allowCustomValue) emitChange(value)
  openMenu()
  void syncActiveOption()
}
function handleFocusOut(event: FocusEvent) {
  const container = event.currentTarget as HTMLElement
  const next = event.relatedTarget as Node | null
  if (next && container.contains(next)) return
  if (!props.allowCustomValue) {
    const exact = effectiveOptions.value.find((option) => (
      option.label.toLocaleLowerCase() === query.value.trim().toLocaleLowerCase()
    ))
    if (exact) selectOption(exact)
    else query.value = optionLabel(props.modelValue)
  }
  closeMenu()
}
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeMenu()
    return
  }
  if (!visibleOptions.value.length) return
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    open.value = true
    const step = event.key === 'ArrowDown' ? 1 : -1
    const current = activeIndex.value < 0 ? (step > 0 ? -1 : 0) : activeIndex.value
    activeIndex.value = (current + step + visibleOptions.value.length) % visibleOptions.value.length
    void nextTick().then(() => {
      optionsElement.value?.querySelector<HTMLElement>(`[data-option-index="${activeIndex.value}"]`)
        ?.scrollIntoView?.({ block: 'nearest' })
    })
  } else if (event.key === 'Enter' && open.value && activeIndex.value >= 0) {
    event.preventDefault()
    selectOption(visibleOptions.value[activeIndex.value])
  }
}
function nativeChange(event: Event) {
  emit('update:modelValue', (event.target as HTMLSelectElement).value)
  emit('change', event)
}

watch(() => effectiveOptions.value.length, (length, previous) => {
  if (props.editable && props.openOnOptionsChange && length > previous) openMenu()
})

defineExpose({ open: openMenu, close: closeMenu })
</script>

<template>
  <div class="app-select relative inline-flex w-full" :class="$attrs.class" @focusout="handleFocusOut">
    <select
      v-if="!editable"
      ref="nativeSelectElement"
      :value="modelValue ?? ''"
      :disabled="disabled"
      class="hidden"
      aria-hidden="true"
      tabindex="-1"
      @change="nativeChange"
    ><slot /></select>

    <button
      v-if="!editable"
      v-bind="forwardedAttrs"
      type="button"
      role="combobox"
      aria-haspopup="listbox"
      :aria-controls="menuId"
      :aria-expanded="open"
      :aria-activedescendant="activeIndex >= 0 ? `${menuId}-${activeIndex}` : undefined"
      :aria-required="required || undefined"
      :disabled="disabled"
      class="app-select-control focus-ring flex h-full w-full items-center border border-[var(--border)] bg-[var(--input-bg)] px-3 pr-10 text-left text-[var(--text)] hover:border-[color-mix(in_srgb,var(--primary),var(--border)_65%)] disabled:cursor-not-allowed disabled:bg-[var(--panel-subtle)] disabled:text-[var(--muted)] disabled:opacity-100"
      :class="controlClass"
      @click="toggleMenu"
      @keydown="handleKeydown"
    ><span class="truncate">{{ query || placeholder }}</span><ChevronDown class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" :size="16" /></button>

    <input
      v-else
      v-bind="forwardedAttrs"
      :value="query"
      :placeholder="placeholder"
      :disabled="disabled"
      :required="required"
      role="combobox"
      aria-autocomplete="list"
      :aria-controls="menuId"
      :aria-expanded="open"
      :aria-activedescendant="activeIndex >= 0 ? `${menuId}-${activeIndex}` : undefined"
      class="app-select-control focus-ring h-full w-full border border-[var(--border)] bg-[var(--input-bg)] px-3 pr-10 text-[var(--text)] placeholder:text-[var(--muted)] disabled:cursor-not-allowed disabled:bg-[var(--panel-subtle)] disabled:text-[var(--muted)] disabled:opacity-100"
      :class="controlClass"
      @focus="openOnFocus && openMenu()"
      @input="handleInput(($event.target as HTMLInputElement).value)"
      @keydown="handleKeydown"
    >
    <button
      v-if="editable"
      type="button"
      class="focus-ring absolute right-1 top-1 flex h-8 w-8 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--panel-subtle)] hover:text-[var(--text)] disabled:opacity-40"
      :aria-label="showOptionsLabel"
      :disabled="disabled || !effectiveOptions.length"
      @click="toggleMenu"
    ><ChevronDown :size="16" /></button>
    <div
      v-if="open && visibleOptions.length"
      :id="menuId"
      ref="optionsElement"
      class="surface absolute inset-x-0 top-full z-20 mt-1 scroll-py-2 overflow-y-auto rounded-lg border border-[var(--border)] px-1 py-2 shadow-xl"
      :style="{ maxHeight: maxMenuHeight }"
      role="listbox"
      :aria-label="optionsLabel"
    >
      <button
        v-for="(option, index) in visibleOptions"
        :id="`${menuId}-${index}`"
        :key="String(option.value)"
        :data-option-index="index"
        type="button"
        role="option"
        class="focus-ring block w-full rounded-md px-3 py-2 text-left text-sm hover:bg-[var(--panel-subtle)] disabled:cursor-not-allowed disabled:opacity-50"
        :class="index === activeIndex ? 'bg-[var(--primary-soft)] text-[var(--primary)]' : ''"
        :aria-selected="String(option.value) === String(modelValue ?? '')"
        :disabled="option.disabled"
        @click="selectOption(option)"
      ><template v-for="(segment, segmentIndex) in matchingSegments(option.label)" :key="segmentIndex"><strong v-if="segment.match" class="font-bold text-[var(--text)]">{{ segment.text }}</strong><span v-else>{{ segment.text }}</span></template></button>
    </div>
  </div>
</template>

<style scoped>
.app-select { height: var(--control-height, 2.5rem); font-size: var(--control-font-size, 0.875rem); }
.app-select-control { border-radius: var(--control-radius, 0.5rem); font-size: inherit; }
</style>
