/**
 * 数据图表组件
 *
 * 基于 ECharts 的交互式数据可视化，支持折线图、柱状图、饼图等。
 * 后端通过 A2UI 协议下发 ECharts 配置项。
 */

import React, { useMemo, useRef, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'

type DataWidgetProps = {
  title?: string
  chartType?: 'line' | 'bar' | 'pie' | 'scatter'
  xAxis?: string[]
  seriesData?: number[] | Array<{ name: string; data: number[] }>
  echartsOption?: Record<string, any> // 直接传入完整 ECharts option
}

function DataWidget({
  title,
  chartType = 'bar',
  xAxis,
  seriesData,
  echartsOption,
}: DataWidgetProps) {
  const option = useMemo(() => {
    // 如果直接传入完整 option，优先使用
    if (echartsOption) return echartsOption

    // 否则根据 props 构建
    const isMultiSeries =
      seriesData?.length && typeof seriesData[0] === 'object' && 'data' in (seriesData[0] as any)
    const series = isMultiSeries
      ? (seriesData as Array<{ name: string; data: number[] }>).map((s) => ({
          ...s,
          type: s.type || chartType,
        }))
      : [{ data: seriesData, type: chartType }]

    return {
      title: title ? { text: title, left: 'center' } : undefined,
      tooltip: { trigger: 'axis' },
      xAxis: chartType !== 'pie' ? { type: 'category', data: xAxis } : undefined,
      yAxis: chartType !== 'pie' ? { type: 'value' } : undefined,
      series:
        chartType === 'pie'
          ? [
              {
                type: 'pie',
                data: (xAxis || []).map((name, i) => {
                  let value = 0
                  if (Array.isArray(seriesData)) {
                    const first = seriesData[0]
                    if (typeof first === 'object' && first !== null && Array.isArray((first as any).data)) {
                      value = (first as any).data[i] ?? 0
                    } else {
                      value = (seriesData[i] as number) ?? 0
                    }
                  }
                  return { name, value }
                }),
              },
            ]
          : series,
    }
  }, [title, chartType, xAxis, seriesData, echartsOption])

  const chartRef = useRef<any>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const observer = new ResizeObserver(() => {
      chartRef.current?.getEchartsInstance()?.resize()
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  return (
    <div className="data-widget" ref={containerRef}>
      <ReactECharts ref={chartRef} option={option} style={{ height: 360 }} />
    </div>
  )
}

export default DataWidget
