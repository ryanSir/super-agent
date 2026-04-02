/**
 * 执行步骤时间线
 */

import React from 'react'

type StepState = {
  stepId: string
  title: string
  status: 'running' | 'completed' | 'failed'
  detail?: string
}

type StepsTimelineProps = {
  steps: StepState[]
}

function StepsTimeline({ steps }: StepsTimelineProps) {
  if (steps.length === 0) return null

  return (
    <div className="steps-timeline">
      {steps.map((step) => (
        <div key={step.stepId} className={`step-item step-${step.status}`}>
          <span className="step-icon" />
          <span className="step-title">{step.title}</span>
          {step.detail && <span className="step-detail">{step.detail}</span>}
        </div>
      ))}
    </div>
  )
}

export default StepsTimeline
