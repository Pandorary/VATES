# Switch 组件问题复盘 (2026-05-21)

### 问题描述
提示词管理页面中，状态列的 Switch 组件无法切换状态，编辑页面的 Switch 也无法切换。

### 问题本质

#### 1. reka-ui 的 SwitchRoot 使用非标准接口

```vue
<!-- reka-ui 的实际接口 -->
<SwitchRoot :checked="value" @update:checked="handler" />

<!-- 标准 Vue v-model 接口应该是 -->
<CustomComponent :model-value="value" @update:modelValue="handler" />
```

Switch 组件做了转换：
- 接收 `modelValue` prop → 转为 `checked`
- 发出 `update:modelValue` 事件 → 从 `update:checked` 转换而来

#### 2. 事件转换链断裂

**原始代码**：
```vue
@update:checked="(val) => emit('update:modelValue', val)"
```

**问题**：`@update:checked` 事件可能没有被正确触发，或者传递的值格式不匹配。

#### 3. 最终解决方案

添加 `@click` 直接处理：
```vue
<SwitchRoot
  @update:checked="handleUpdate"  <!-- 主事件 -->
  @click="handleClick"             <!-- 备用事件 -->
>
```

**为什么有效**：
- `@click` 是原生 DOM 事件，保证能触发
- 直接取反 `!props.modelValue` 简化逻辑
- 绕过了 reka-ui 内部的事件系统

### 根本原因分析

| 层次 | 原因 |
|------|------|
| **表层** | Switch 不能切换 |
| **中间层** | `update:checked` 事件未触发或传递问题 |
| **根本层** | reka-ui 的非标准接口与 Vue v-model 机制的兼容性问题 |

### 第一性原理
当封装的第三方组件事件不稳定时，回退到原生事件作为兜底。

### 最终实现

```vue
<script setup lang="ts">
import { cn } from '@/lib/utils'
import { SwitchRoot, SwitchThumb } from 'reka-ui'
import { type HTMLAttributes } from 'vue'

interface Props {
  class?: HTMLAttributes['class']
  modelValue?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function handleClick() {
  console.log('Switch clicked:', props.modelValue)
  emit('update:modelValue', !props.modelValue)
}

function handleUpdate(val: boolean) {
  console.log('Switch update:', props.modelValue, '->', val)
  emit('update:modelValue', val)
}
</script>

<template>
  <SwitchRoot
    :checked="modelValue"
    :disabled="disabled"
    :class="cn(...)"
    @update:checked="handleUpdate"
    @click="handleClick"
  >
    <SwitchThumb :class="cn(...)" />
  </SwitchRoot>
</template>
```

### 文件位置
`frontend/src/components/ui/switch.tsx`