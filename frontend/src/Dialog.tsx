import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { X } from 'lucide-react';

export default function Dialog({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const element = dialog.current;
    const previous = document.activeElement as HTMLElement | null;
    element?.showModal();
    const cancel = (event: Event) => { event.preventDefault(); closeRef.current(); };
    element?.addEventListener('cancel', cancel);
    return () => { element?.removeEventListener('cancel', cancel); element?.close(); previous?.focus(); };
  }, []);
  return <dialog ref={dialog} className={`dialog ${wide ? 'dialog-wide' : ''}`} aria-labelledby="dialog-title" onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="dialog-head"><h2 id="dialog-title">{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={20} /></button></div>
    {children}
  </dialog>;
}
