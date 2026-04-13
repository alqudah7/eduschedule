import { Button } from './Button'

type EmptyStateProps = {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      {icon && <div className="w-12 h-12 text-gray-300 mb-4">{icon}</div>}
      <h3 className="text-sm font-syne font-semibold text-gray-700 mb-1">{title}</h3>
      {description && <p className="text-xs text-gray-500 mb-6 max-w-xs">{description}</p>}
      {action && <Button variant="secondary" size="sm" onClick={action.onClick}>{action.label}</Button>}
    </div>
  )
}
