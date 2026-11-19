import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null)
  const timeoutRef = useRef(null)

  const dismissToast = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
    setToast(null)
  }, [])

  const showToast = useCallback((message, type = 'info') => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    setToast({
      id: Date.now(),
      message,
      type,
    })

    timeoutRef.current = setTimeout(() => {
      setToast(null)
      timeoutRef.current = null
    }, 3500)
  }, [])

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return (
    <ToastContext.Provider value={{ showToast, dismissToast }}>
      {children}

      {toast && (
        <div
          className="fixed right-5 top-5 z-[100] w-[min( calc(100vw-2.5rem), 380px)]"
          aria-live={toast.type === 'error' ? 'assertive' : 'polite'}
          aria-atomic="true"
        >
          <div
            role={toast.type === 'error' ? 'alert' : 'status'}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 shadow-2xl backdrop-blur ${
              toast.type === 'success'
                ? 'border-emerald-500/30 bg-[#14251f] text-emerald-100'
                : toast.type === 'error'
                  ? 'border-red-500/30 bg-[#2a191b] text-red-100'
                  : 'border-amber-200/20 bg-[#202027] text-gray-100'
            }`}
          >
            <span className="mt-0.5 text-sm" aria-hidden="true">
              {toast.type === 'success'
                ? '✓'
                : toast.type === 'error'
                  ? '!'
                  : 'i'}
            </span>

            <p className="flex-1 text-sm leading-6">{toast.message}</p>

            <button
              type="button"
              onClick={dismissToast}
              className="text-lg leading-none opacity-60 transition hover:opacity-100"
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        </div>
      )}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)

  if (!context) {
    throw new Error('useToast must be used inside ToastProvider')
  }

  return context
}


