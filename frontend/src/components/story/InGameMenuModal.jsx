import { Link } from 'react-router-dom'

export default function InGameMenuModal({ isOpen, onClose, story = null, onSave = () => {} }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div onClick={onClose} className="fixed inset-0 bg-black/80 backdrop-blur-md" />

      <div className="relative z-10 w-full max-w-md overflow-hidden rounded-2xl border border-white/10 bg-[#14191E] text-[#F1EEE8] shadow-2xl p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <h2 className="font-cinematic text-2xl font-semibold text-[#F1EEE8]">
              Sanctuary Menu
            </h2>
            <p className="text-xs text-[#858A8D] mt-0.5">
              {story?.title || 'Active Chronicle'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 p-2 text-[#858A8D] hover:text-[#F1EEE8] transition"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => {
              onSave()
              onClose()
            }}
            className="flex w-full items-center justify-between rounded-xl border border-[#C4AD88]/30 bg-[#1B2228] p-4 text-left transition hover:border-[#C4AD88] hover:bg-[#C4AD88]/10"
          >
            <div>
              <span className="font-cinematic text-lg font-medium text-[#F1EEE8] block">Save Progress</span>
              <span className="text-xs text-[#858A8D]">Record current turn and emotional state</span>
            </div>
            <span className="text-xs text-[#C4AD88]">💾 Save</span>
          </button>

          <Link
            to="/dashboard"
            className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-[#101317] p-4 text-left transition hover:border-white/20 hover:bg-[#1B2228]"
          >
            <div>
              <span className="font-cinematic text-lg font-medium text-[#F1EEE8] block">Return to Story Library</span>
              <span className="text-xs text-[#858A8D]">Exit to your personal chronicle archive</span>
            </div>
            <span className="text-xs text-[#858A8D]">← Archive</span>
          </Link>
        </div>

        <div className="border-t border-white/10 pt-4 flex justify-between items-center text-xs text-[#858A8D]">
          <span>Yūgen Mayoiga · Story Engine</span>
          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-[#101317] px-4 py-2 text-xs text-[#F1EEE8] hover:border-white/20 transition"
          >
            Resume Story
          </button>
        </div>
      </div>
    </div>
  )
}
