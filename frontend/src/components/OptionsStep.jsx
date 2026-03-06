import { useState } from 'react'
import axios from 'axios'
import { API_BASE } from '../lib/api'

// Professional preset colors with hex
const BG_PRESETS = [
  { value: 'classic_gray',   label: 'Classic Gray',    hex: '#F0F0F0' },
  { value: 'off_white',      label: 'Off White',       hex: '#F5F5F5' },
  { value: 'white',          label: 'Pure White',      hex: '#FFFFFF' },
  { value: 'corporate_blue', label: 'Corporate Blue',  hex: '#1F4E79' },
  { value: 'navy',           label: 'Navy',            hex: '#00203F' },
  { value: 'light_blue',     label: 'Light Blue',      hex: '#ADD8E6' },
  { value: 'slate',          label: 'Slate',           hex: '#708090' },
  { value: 'dark_gray',      label: 'Dark Gray',       hex: '#404040' },
  { value: 'teal',           label: 'Teal',            hex: '#008080' },
  { value: 'forest_green',   label: 'Forest Green',    hex: '#225522' },
]

const OUTFIT_LABELS = {
  business_suit:    'Business Suit',
  business_casual:  'Business Casual',
  formal_suit:      'Formal Suit',
  blazer:           'Blazer',
}

const OUTFIT_ICONS = {
  business_suit:   '👔',
  business_casual: '👕',
  formal_suit:     '🎩',
  blazer:          '🧥',
}

function GenderBadge({ gender, confidence }) {
  if (gender === 'unknown') return null
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold
      ${gender === 'male' ? 'bg-blue-100 text-blue-700' : 'bg-pink-100 text-pink-700'}`}>
      {gender === 'male' ? '♂' : '♀'} {gender.charAt(0).toUpperCase() + gender.slice(1)}
      {confidence > 0 && <span className="opacity-60">· {Math.round(confidence)}%</span>}
    </span>
  )
}

export default function OptionsStep({ analysis, options, onDone, onBack }) {
  const detected = analysis.gender !== 'unknown' ? analysis.gender : 'male'
  const [gender, setGender] = useState(detected)
  const [bgColor, setBgColor] = useState('classic_gray')
  const [customColor, setCustomColor] = useState('#E0E0E0')
  const [useCustom, setUseCustom] = useState(false)
  const [outfit, setOutfit] = useState('business_suit')
  const [changeOutfit, setChangeOutfit] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const sdAvailable = analysis.sd_available ?? false

  const outfitOptions = [
    { value: 'business_suit', label: 'Business Suit' },
    { value: 'business_casual', label: 'Business Casual' },
    { value: 'formal_suit', label: 'Formal Suit' },
    { value: 'blazer', label: 'Blazer' },
  ]

  function hexToRgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return { r, g, b }
  }

  async function handleGenerate() {
    setError(null)
    setLoading(true)

    const formData = new FormData()
    // Stateless: send the image back as base64 (no session file on Vercel)
    formData.append('image_b64', analysis.image_b64 || analysis.preview)
    formData.append('gender', gender)
    formData.append('outfit_style', outfit)
    formData.append('change_outfit', changeOutfit.toString())

    if (useCustom) {
      const { r, g, b } = hexToRgb(customColor)
      formData.append('background_color', 'classic_gray')
      formData.append('custom_color_r', r.toString())
      formData.append('custom_color_g', g.toString())
      formData.append('custom_color_b', b.toString())
    } else {
      formData.append('background_color', bgColor)
    }

    try {
      const res = await axios.post(`${API_BASE}/api/generate`, formData)
      onDone(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Generation failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Customize Your Photo</h2>
          <p className="text-gray-500 text-sm mt-0.5">Choose background, outfit, and style options</p>
        </div>
        <button onClick={onBack} className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1">
          ← Back
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: preview */}
        <div className="flex flex-col gap-4">
          <div className="rounded-xl overflow-hidden border border-gray-200 bg-gray-50 aspect-square flex items-center justify-center">
            <img
              src={analysis.preview}
              alt="Your photo"
              className="w-full h-full object-cover"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500">Detected:</span>
            <GenderBadge gender={analysis.gender} confidence={analysis.gender_confidence * 100} />
            {analysis.face_count > 0 && (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                ✓ Face detected
              </span>
            )}
          </div>
        </div>

        {/* Right: options */}
        <div className="flex flex-col gap-5">
          {/* Gender override */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Gender</label>
            <div className="flex gap-2">
              {['male', 'female'].map(g => (
                <button
                  key={g}
                  onClick={() => setGender(g)}
                  className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-all
                    ${gender === g
                      ? 'border-linkedin-blue bg-linkedin-light text-linkedin-blue'
                      : 'border-gray-200 text-gray-600 hover:border-gray-400'}`}
                >
                  {g === 'male' ? '♂ Male' : '♀ Female'}
                  {g === detected && analysis.gender !== 'unknown' && (
                    <span className="ml-1 text-xs opacity-60">(detected)</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Background color */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Background Color</label>
            <div className="grid grid-cols-5 gap-2 mb-2">
              {BG_PRESETS.map(bg => (
                <button
                  key={bg.value}
                  title={bg.label}
                  onClick={() => { setBgColor(bg.value); setUseCustom(false) }}
                  className={`w-full aspect-square rounded-lg border-2 transition-all
                    ${!useCustom && bgColor === bg.value
                      ? 'border-linkedin-blue scale-110 shadow-md'
                      : 'border-transparent hover:border-gray-300'}`}
                  style={{ backgroundColor: bg.hex }}
                />
              ))}
            </div>
            {/* Custom color */}
            <div className="flex items-center gap-2 mt-2">
              <input
                type="color"
                value={customColor}
                onChange={e => { setCustomColor(e.target.value); setUseCustom(true) }}
                className="w-8 h-8 rounded cursor-pointer border border-gray-300"
              />
              <button
                onClick={() => setUseCustom(true)}
                className={`text-xs px-2 py-1 rounded border transition-all
                  ${useCustom ? 'border-linkedin-blue text-linkedin-blue bg-linkedin-light' : 'border-gray-200 text-gray-500'}`}
              >
                Custom color
              </button>
            </div>
          </div>

          {/* Outfit */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Outfit <span className="text-xs font-normal text-gray-400">(AI required)</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              {outfitOptions.map(o => (
                <button
                  key={o.value}
                  onClick={() => setOutfit(o.value)}
                  className={`py-2 px-3 rounded-lg border text-sm font-medium transition-all flex items-center gap-2
                    ${outfit === o.value
                      ? 'border-linkedin-blue bg-linkedin-light text-linkedin-blue'
                      : 'border-gray-200 text-gray-600 hover:border-gray-400'}`}
                >
                  <span>{OUTFIT_ICONS[o.value]}</span>
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Change outfit toggle */}
          <div className={`rounded-lg p-3 border ${sdAvailable ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200 opacity-60'}`}>
            <label className={`flex items-start gap-3 ${sdAvailable ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
              <input
                type="checkbox"
                checked={changeOutfit}
                disabled={!sdAvailable}
                onChange={e => setChangeOutfit(e.target.checked)}
                className="mt-0.5 accent-linkedin-blue"
              />
              <div>
                <p className="text-sm font-semibold text-gray-800">
                  Change Outfit with Local AI
                  {sdAvailable && <span className="ml-2 text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-medium">Available</span>}
                  {!sdAvailable && <span className="ml-2 text-xs bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded font-medium">Install diffusers</span>}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {sdAvailable
                    ? 'Uses Stable Diffusion inpainting on your machine. First use downloads the model (~3.4GB). No internet needed after that.'
                    : 'Run: pip install diffusers transformers accelerate  — then restart the backend.'}
                </p>
              </div>
            </label>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={loading}
        className={`mt-6 w-full py-3 rounded-xl font-semibold text-white transition-all
          ${loading
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-linkedin-blue hover:bg-linkedin-dark active:scale-[0.99]'}`}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {changeOutfit ? 'Running local AI (may take 1–3 min on CPU)…' : 'Processing…'}
          </span>
        ) : (
          'Generate Professional Photo →'
        )}
      </button>
    </div>
  )
}
