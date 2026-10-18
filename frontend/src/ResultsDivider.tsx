import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { KeyboardEvent, PointerEvent, RefObject } from 'react';

export const RESULTS_DIVIDER_HEIGHT = 12;
const MIN_EDITOR_HEIGHT = 200;
const MIN_RESULTS_HEIGHT = 148;
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export default function ResultsDivider({ panels, value, onChange }: {
  panels: RefObject<HTMLDivElement | null>;
  value: number;
  onChange: (value: number) => void;
}) {
  const [limits, setLimits] = useState({ min: 15, max: 80 });
  const [dragging, setDragging] = useState(false);
  const valueRef = useRef(value);
  valueRef.current = value;
  const handle = useRef<HTMLDivElement>(null);
  const drag = useRef<{ pointer: number; y: number; height: number; value: number } | null>(null);

  useLayoutEffect(() => {
    const host = panels.current;
    if (!host) return;
    const measure = () => {
      const available = Math.max(MIN_EDITOR_HEIGHT + MIN_RESULTS_HEIGHT, host.clientHeight - RESULTS_DIVIDER_HEIGHT);
      const min = MIN_RESULTS_HEIGHT / available * 100;
      const max = (available - MIN_EDITOR_HEIGHT) / available * 100;
      setLimits({ min, max });
      onChange(clamp(valueRef.current, min, max));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(host);
    return () => observer.disconnect();
  }, [panels, onChange]);

  const finishDrag = useCallback(() => {
    const pointer = drag.current?.pointer;
    drag.current = null;
    document.body.classList.remove('resizing-results');
    setDragging(false);
    if (pointer !== undefined && handle.current?.hasPointerCapture(pointer)) handle.current.releasePointerCapture(pointer);
  }, []);

  useEffect(() => {
    window.addEventListener('blur', finishDrag);
    return () => {
      window.removeEventListener('blur', finishDrag);
      document.body.classList.remove('resizing-results');
    };
  }, [finishDrag]);

  const startDrag = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || !event.isPrimary || drag.current || !panels.current) return;
    event.preventDefault();
    event.currentTarget.focus();
    event.currentTarget.setPointerCapture(event.pointerId);
    const available = panels.current.clientHeight - RESULTS_DIVIDER_HEIGHT;
    drag.current = { pointer: event.pointerId, y: event.clientY, height: available * value / 100, value };
    document.body.classList.add('resizing-results');
    setDragging(true);
  };

  const moveDrag = (event: PointerEvent<HTMLDivElement>) => {
    if (drag.current?.pointer !== event.pointerId || !panels.current) return;
    const available = panels.current.clientHeight - RESULTS_DIVIDER_HEIGHT;
    onChange(clamp((drag.current.height + drag.current.y - event.clientY) / available * 100, limits.min, limits.max));
  };

  const resizeWithKeyboard = (event: KeyboardEvent<HTMLDivElement>) => {
    let next: number;
    if (event.key === 'Escape' && drag.current) {
      next = drag.current.value;
      finishDrag();
    } else if (event.key === 'ArrowUp') next = value + (event.shiftKey ? 10 : 5);
    else if (event.key === 'ArrowDown') next = value - (event.shiftKey ? 10 : 5);
    else if (event.key === 'Home') next = limits.min;
    else if (event.key === 'End') next = limits.max;
    else return;
    event.preventDefault();
    onChange(clamp(next, limits.min, limits.max));
  };

  return <>
    <div ref={handle} className={`results-divider${dragging ? ' is-dragging' : ''}`}
      role="separator" tabIndex={0} aria-label="Resize results" aria-orientation="horizontal"
      aria-controls="sql-editor-panel results-panel" aria-describedby="results-resize-help"
      aria-valuemin={Math.round(limits.min)} aria-valuemax={Math.round(limits.max)}
      aria-valuenow={Math.round(value)} aria-valuetext={`${Math.round(value)}% results height`}
      title="Drag to resize results" onPointerDown={startDrag} onPointerMove={moveDrag}
      onPointerUp={finishDrag} onPointerCancel={finishDrag} onLostPointerCapture={finishDrag}
      onKeyDown={resizeWithKeyboard}/>
    <span id="results-resize-help" className="sr-only">Drag up to enlarge results or down to enlarge the editor. Use Up and Down arrows to resize, or Home and End for the smallest and largest results pane.</span>
  </>;
}
