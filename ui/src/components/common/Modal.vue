<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-150"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 overflow-y-auto"
        @click.self="closeOnBackdrop && close()"
      >
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50" />

        <!-- Modal container -->
        <div class="flex min-h-full items-center justify-center p-4">
          <Transition
            enter-active-class="transition-all duration-200"
            leave-active-class="transition-all duration-150"
            enter-from-class="opacity-0 scale-95"
            leave-to-class="opacity-0 scale-95"
          >
            <div
              v-if="modelValue"
              :class="[
                'relative bg-white dark:bg-gray-800 rounded-xl shadow-xl',
                sizeClasses
              ]"
              @click.stop
            >
              <!-- Header -->
              <div v-if="title || $slots.header" class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <slot name="header">
                  <div class="flex items-center justify-between">
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                      {{ title }}
                    </h3>
                    <button
                      v-if="showClose"
                      @click="close"
                      class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <XMarkIcon class="w-5 h-5 text-gray-500" />
                    </button>
                  </div>
                </slot>
              </div>

              <!-- Body -->
              <div :class="['px-6 py-4', bodyClass]">
                <slot />
              </div>

              <!-- Footer -->
              <div v-if="$slots.footer" class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3">
                <slot name="footer" />
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, watch } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  modelValue: Boolean,
  title: String,
  size: {
    type: String,
    default: 'md',
    validator: v => ['sm', 'md', 'lg', 'xl', 'full'].includes(v)
  },
  showClose: { type: Boolean, default: true },
  closeOnBackdrop: { type: Boolean, default: true },
  bodyClass: String
})

const emit = defineEmits(['update:modelValue', 'close'])

const sizeClasses = computed(() => {
  const sizes = {
    sm: 'w-full max-w-sm',
    md: 'w-full max-w-md',
    lg: 'w-full max-w-lg',
    xl: 'w-full max-w-xl',
    full: 'w-full max-w-4xl'
  }
  return sizes[props.size]
})

function close() {
  emit('update:modelValue', false)
  emit('close')
}

// Handle escape key
watch(() => props.modelValue, (open) => {
  if (open) {
    const handleEscape = (e) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }
})
</script>
