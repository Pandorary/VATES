# Disclaimer 弹窗问题 (2026-05-21)

### 问题描述
弹窗始终显示，无法关闭，影响页面操作。

### 原因
```vue
<!-- 原始代码 -->
<Dialog :open="true" :closable="false">
```
`:open="true"` 硬编码为始终打开，即使用户点击同意后 `disclaimerAgreed` 变为 true，组件内部的 `open` 仍然是 true。

### 解决方案

#### 1. 添加内部状态控制关闭

```vue
<template>
  <Dialog :open="open">
    <!-- 内容 -->
    <Button @click="handleAgree">同意</Button>
  </Dialog>
</template>

<script setup lang="ts">
const open = ref(true)

function handleAgree() {
  emit('agree')
  open.value = false  // 点击同意后关闭
}
</script>
```

#### 2. 添加点击遮罩不关闭

```vue
<Dialog :open="open" @update:open="handleCancel">
```

当用户点击遮罩层时，不允许关闭弹窗，必须点击同意按钮。

```typescript
function handleCancel() {
  // 点击遮罩不关闭，必须点击同意按钮
  // open.value = false
}
```

### 文件位置
`frontend/src/components/Disclaimer.tsx`