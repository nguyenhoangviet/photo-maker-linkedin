export default function ResultStep({ result, onReset, sessionId }) {
  function handleDownload() {
    const link = document.createElement('a')
    link.href = result.result       // base64 data URI
    link.download = `linkedin_photo_${sessionId?.slice(0, 8) || 'result'}.jpg`
    link.click()
  }

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="mb-4">
        <div className="inline-flex items-center gap-2 bg-green-100 text-green-700 px-3 py-1.5 rounded-full text-sm font-semibold mb-3">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path fillRule="evenodd" d="M12 2a10 10 0 100 20A10 10 0 0012 2zm4.707 7.293a1 1 0 00-1.414 0L10 14.586l-2.293-2.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l6-6a1 1 0 000-1.414z" clipRule="evenodd" />
          </svg>
          Photo Generated!
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Your LinkedIn Photo is Ready</h2>
        {result.outfit_applied && (
          <p className="text-xs text-linkedin-blue mt-1 font-medium">✨ Outfit changed with local AI</p>
        )}
        {!result.outfit_applied && (
          <p className="text-xs text-gray-400 mt-1">Background removed and replaced with professional color</p>
        )}
      </div>

      {/* Result image */}
      <div className="relative inline-block mb-6">
        <img
          src={result.result}
          alt="Generated LinkedIn photo"
          className="w-64 h-64 object-cover rounded-full border-4 border-linkedin-blue shadow-xl mx-auto"
        />
        <div className="absolute -bottom-2 -right-2 bg-linkedin-blue text-white text-xs px-2 py-0.5 rounded-full font-semibold shadow">
          800 × 800px
        </div>
      </div>

      {/* Raw result (full square preview) */}
      <div className="mb-6">
        <p className="text-xs text-gray-400 mb-2">Full square preview</p>
        <img
          src={result.result}
          alt="Full preview"
          className="w-48 h-48 object-cover rounded-xl border border-gray-200 shadow-sm mx-auto"
        />
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          onClick={handleDownload}
          className="flex items-center justify-center gap-2 bg-linkedin-blue hover:bg-linkedin-dark text-white
            font-semibold py-3 px-6 rounded-xl transition-all active:scale-[0.98]"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download JPEG
        </button>
        <button
          onClick={onReset}
          className="flex items-center justify-center gap-2 border border-gray-200 hover:border-gray-400
            text-gray-600 font-semibold py-3 px-6 rounded-xl transition-all"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Start Over
        </button>
      </div>

      {/* Tips */}
      <div className="mt-6 bg-linkedin-light rounded-xl p-4 text-left">
        <p className="text-xs font-semibold text-linkedin-blue mb-2">LinkedIn Upload Tips</p>
        <ul className="text-xs text-gray-600 space-y-1">
          <li>• Recommended size: 400×400 to 7680×4320 px (we output 800×800)</li>
          <li>• Square crop works best — LinkedIn displays circular for profile</li>
          <li>• File under 8MB — our output is well under this limit</li>
        </ul>
      </div>
    </div>
  )
}
