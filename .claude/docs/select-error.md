# Select 组件空字符串错误 (2026-05-21)

### 问题描述
```
Error: A <SelectItem /> must have a value prop that is not an empty string.
This is because a Select value can be set to an empty string to clear the selection and show the placeholder.
```

### 原因
reka-ui 的 Select 组件不允许 SelectItem 的 value 为空字符串。

### 解决方案

将空字符串改为 `'all'`：

```typescript
const roleOptions = [
  { label: '全部角色', value: 'all' },  // 改为 'all'
  { label: '分析师', value: '分析师' },
  // ...
]

const filterRole = ref('all')  // 初始化为 'all'

// 请求时判断
role: filterRole.value !== 'all' ? filterRole.value : undefined,
```

### 文件位置
`frontend/src/pages/PromptManager.tsx`