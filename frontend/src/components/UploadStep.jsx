import { useState, useRef } from 'react'
import axios from 'axios'

export default function UploadStep({ onDone }) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)
  const inputRef = useRef()

  async function handleFile(file) {
    if (!file) return
    setError(null)

    // Local preview
    const reader = new FileReader()
    reader.onload = e => setPreview(e.target.result)
    reader.readAsDataURL(file)

    const formData = new FormData()
    formData.append('file', file)

    setLoading(true)
    try {
      const res = await axios.post('/api/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      onDone(res.data)
    } catch (err) {
      const detail = err.response?.data?.detail
      if (detail && typeof detail === 'object') {
        setError(detail.message || 'No face detected in the photo.')
      } else {
        setError(detail || 'Failed to analyze image. Please try again.')
      }
      setPreview(null)
    } finally {
      setLoading(false)
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="max-w-xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-1">Upload Your Photo</h2>
      <p className="text-gray-500 text-sm mb-6">
        Upload a clear photo with your face visible. We'll detect your face and generate a professional LinkedIn profile photo.
      </p>

      {/* Drop zone */}
      <div
        className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer
          ${dragging ? 'border-linkedin-blue bg-linkedin-light' : 'border-gray-300 hover:border-linkedin-blue hover:bg-gray-50'}
          ${loading ? 'opacity-60 pointer-events-none' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={e => handleFile(e.target.files[0])}
        />

        {preview ? (
          <div className="flex flex-col items-center gap-3">
            <img src={preview} alt="Preview" className="w-40 h-40 object-cover rounded-xl shadow" />
            <p className="text-sm text-gray-500">Click or drop to change photo</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-linkedin-light flex items-center justify-center">
              <svg className="w-8 h-8 text-linkedin-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-gray-700">Drop your photo here</p>
              <p className="text-sm text-gray-400 mt-1">or click to browse — JPEG, PNG, WebP up to 10MB</p>
            </div>
          </div>
        )}
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="mt-4 flex items-center justify-center gap-3 text-linkedin-blue">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm font-medium">Analyzing photo...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-4 flex gap-3 items-start">
          <svg className="w-5 h-5 text-red-500 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
            <path fillRule="evenodd" d="M12 2a10 10 0 100 20A10 10 0 0012 2zM11 7h2v6h-2V7zm0 8h2v2h-2v-2z"
              clipRule="evenodd" />
          </svg>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Tips */}
      <div className="mt-6 grid grid-cols-3 gap-3 text-center">
        {[
          { icon: '🙂', label: 'Clear face visible' },
          { icon: '💡', label: 'Good lighting' },
          { icon: '👤', label: 'Single person' },
        ].map(tip => (
          <div key={tip.label} className="bg-gray-50 rounded-lg p-3">
            <div className="text-2xl mb-1">{tip.icon}</div>
            <p className="text-xs text-gray-500">{tip.label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
