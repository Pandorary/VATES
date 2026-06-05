# 提示词管理页面 UI 优化

## 优化目标
对提示词管理页面进行字体、颜色、风格统一优化。

## 优化内容

### 1. 字体统一

| 元素 | 样式 |
|------|------|
| 页面标题 | `text-2xl` |
| 副标题 | `text-sm` |
| 表头 | `h-10 px-4 text-sm font-semibold` |
| 表格内容 | `text-sm` |
| Badge | `text-xs` |
| 序号 | `text-sm` |
| 分页 | `text-sm` |

### 2. 颜色与样式统一

| 元素 | 样式 |
|------|------|
| 主标题 | `text-primary` |
| 表头背景 | `bg-primary/5 text-primary` |
| 悬停效果 | `hover:bg-muted/50` |
| 按钮间距 | `gap-2` |

### 3. 对齐优化

| 元素 | 样式 |
|------|------|
| 状态列 | `text-center` |
| 操作列 | `text-center justify-center` |

### 4. 间距优化

| 位置 | 样式 |
|------|------|
| 表头高度 | `h-10` |
| 表头内边距 | `px-4` |

### 5. 交互优化

| 优化 | 说明 |
|------|------|
| 点击角色编码/名称 | 展示详情 |
| 点击 Switch | 切换激活状态 |

### 6. Markdown 预览

| 元素 | 样式 |
|------|------|
| h2 | mt-6 mb-3 |
| h3 | mt-4 mb-2 |
| p | my-2 |
| ul/li | my-2 |

## 文件位置
`frontend/src/pages/PromptManager.tsx`
