import { useState, useEffect } from 'react'
import axios from 'axios'
import UploadStep from './components/UploadStep'
import OptionsStep from './components/OptionsStep'
import ResultStep from './components/ResultStep'

const STEPS = ['upload', 'options', 'result']

export default function App() {
  const [step, setStep] = useState('upload')
  const [analysis, setAnalysis] = useState(null)   // from /api/analyze
  const [options, setOptions] = useState(null)      // from /api/options
  const [result, setResult] = useState(null)        // from /api/generate
  const [error, setError] = useState(null)

  useEffect(() => {
    axios.get('/api/options')
      .then(r => setOptions(r.data))
      .catch(() => {})
  }, [])

  function handleAnalyzeDone(data) {
    setAnalysis(data)
    setError(null)
    setStep('options')
  }

  function handleGenerateDone(data) {
    setResult(data)
    setError(null)
    setStep('result')
  }

  function handleReset() {
    setStep('upload')
    setAnalysis(null)
    setResult(null)
    setError(null)
  }

  const stepIndex = STEPS.indexOf(step)

  return (
    <div className="min-h-screen bg-gradient-to-br from-linkedin-light via-white to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-9 h-9 bg-linkedin-blue rounded flex items-center justify-center">
            <span className="text-white font-bold text-lg leading-none">in</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">LinkedIn Photo Maker</h1>
            <p className="text-xs text-gray-500">Generate your professional profile photo</p>
          </div>
        </div>
      </header>

      {/* Step indicator */}
      <div className="max-w-4xl mx-auto px-4 pt-6">
        <div className="flex items-center gap-2 mb-8">
          {[
            { key: 'upload', label: 'Upload Photo' },
            { key: 'options', label: 'Customize' },
            { key: 'result', label: 'Your Result' },
          ].map((s, i) => (
            <div key={s.key} className="flex items-center gap-2">
              <div className={`flex items-center gap-2 ${i <= stepIndex ? 'opacity-100' : 'opacity-40'}`}>
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold
                    ${i < stepIndex ? 'bg-green-500 text-white' :
                      i === stepIndex ? 'bg-linkedin-blue text-white' :
                      'bg-gray-200 text-gray-500'}`}
                >
                  {i < stepIndex ? '✓' : i + 1}
                </div>
                <span className={`text-sm font-medium hidden sm:block
                  ${i === stepIndex ? 'text-linkedin-blue' : 'text-gray-500'}`}>
                  {s.label}
                </span>
              </div>
              {i < 2 && (
                <div className={`w-8 h-0.5 mx-1 ${i < stepIndex ? 'bg-green-400' : 'bg-gray-200'}`} />
              )}
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">
          {step === 'upload' && (
            <UploadStep onDone={handleAnalyzeDone} />
          )}
          {step === 'options' && analysis && (
            <OptionsStep
              analysis={analysis}
              options={options}
              onDone={handleGenerateDone}
              onBack={handleReset}
            />
          )}
          {step === 'result' && result && (
            <ResultStep
              result={result}
              onReset={handleReset}
              sessionId={analysis?.session_id}
            />
          )}
        </div>
      </div>
    </div>
  )
}
