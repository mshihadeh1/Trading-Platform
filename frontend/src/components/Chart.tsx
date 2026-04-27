import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import type { CandleData as LDChartData, ISeriesLineSeries } from 'lightweight-charts';
import type { CandleData } from '../types';

interface Props {
  candles: CandleData[];
  symbol: string;
  height?: number;
}

export function Chart({ candles, symbol, height = 500 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height });

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: dimensions.width,
      height: dimensions.height,
      layout: {
        background: { type: ColorType.Solid, color: '#161b22' },
        textColor: '#d1d5dc',
      },
      grid: {
        vertLines: { color: '#21262d' },
        horzLines: { color: '#21262d' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#484f58', width: 1, style: 2 },
        horzLine: { color: '#484f58', width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: '#30363d',
      },
      timeScale: {
        borderColor: '#30363d',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    chartRef.current = { chart, candleSeries };

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
        setDimensions({ width: containerRef.current.clientWidth, height });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [height]);

  useEffect(() => {
    if (!chartRef.current) return;

    const data: LDChartData[] = candles.map((c) => ({
      time: Math.floor(c.timestamp / 1000),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    chartRef.current.candleSeries.setData(data);

    if (data.length > 0) {
      chartRef.current.chart.timeScale().fitContent();
    }
  }, [candles]);

  return (
    <div ref={containerRef} style={{ width: '100%', height }} />
  );
}
