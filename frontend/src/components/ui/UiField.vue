<script setup>
defineProps({ field: { type: Object, required: true }, modelValue: [String, Number, Boolean], options: { type: Array, default: () => [] } })
defineEmits(['update:modelValue'])
</script>
<template>
  <label :class="{ 'full-width': field.type === 'textarea', 'checkbox-label': field.type === 'checkbox' }">
    <template v-if="field.type === 'checkbox'"><input :checked="modelValue" type="checkbox" :name="field.key" @change="$emit('update:modelValue', $event.target.checked)" />{{ field.label }}</template>
    <template v-else>{{ field.label }}<span v-if="field.required" class="required" aria-hidden="true"> *</span>
      <textarea v-if="field.type === 'textarea'" :value="modelValue" :name="field.key" :maxlength="field.maxlength || (field.key === 'address' ? 2000 : 10000)" rows="3" @input="$emit('update:modelValue', $event.target.value)"></textarea>
      <select v-else-if="field.type === 'select'" :value="modelValue" :name="field.key" :required="field.required" @change="$emit('update:modelValue', $event.target.value)"><option v-for="[value, label] in field.options" :key="value" :value="value">{{ label }}</option></select>
      <select v-else-if="field.type === 'relation'" :value="modelValue ?? ''" :name="field.key" :required="field.required" @change="$emit('update:modelValue', $event.target.value)"><option value="">{{ field.required ? 'Choose…' : 'None' }}</option><option v-for="option in options" :key="option.id" :value="option.id" :disabled="option.inactive">{{ option.name }}</option></select>
      <input v-else :value="modelValue" :name="field.key" :type="field.type || 'text'" :required="field.required" :maxlength="field.maxlength || (field.key === 'email' ? 254 : 200)" :min="field.min ?? (field.type === 'number' ? 0 : undefined)" :max="field.max" :step="field.step" @input="$emit('update:modelValue', $event.target.value)" />
    </template>
    <small v-if="field.help" class="field-help">{{ field.help }}</small>
  </label>
</template>
