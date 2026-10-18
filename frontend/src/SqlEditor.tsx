import { useEffect, useImperativeHandle, useRef } from 'react';
import type { Ref } from 'react';
import { Compartment, EditorState, Prec } from '@codemirror/state';
import { EditorView, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, drawSelection, highlightActiveLine } from '@codemirror/view';
import { defaultKeymap, history, historyKeymap, indentLess, insertTab } from '@codemirror/commands';
import { autocompletion, closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete';
import { bracketMatching, syntaxHighlighting, HighlightStyle } from '@codemirror/language';
import { sql, MySQL } from '@codemirror/lang-sql';
import { tags } from '@lezer/highlight';

const theme = EditorView.theme({
  '&': { height: '100%', color: '#e2ebe8', backgroundColor: 'transparent', fontSize: '14px' },
  '.cm-content': { fontFamily: 'var(--font-mono)', padding: '18px 0', caretColor: '#8ae6bd' },
  '.cm-line': { padding: '0 20px 0 12px', lineHeight: '1.85' },
  '.cm-scroller': { fontFamily: 'var(--font-mono)', overflow: 'auto' },
  '.cm-gutters': { backgroundColor: 'transparent', color: '#6e8589', borderRight: '1px solid #263436' },
  '.cm-gutterElement': { padding: '0 12px 0 15px', lineHeight: '1.85' },
  '.cm-activeLineGutter': { backgroundColor: '#1a2828', color: '#9cbab0' },
  '.cm-activeLine': { backgroundColor: '#19272877' },
  '&.cm-focused': { outline: 'none' },
  '.cm-selectionBackground, &.cm-focused .cm-selectionBackground': { backgroundColor: '#36534d' },
  '.cm-cursor': { borderLeftColor: '#8ae6bd' },
  '.cm-tooltip': { backgroundColor: '#1d2a2c', border: '1px solid #3b5353', color: '#edf4f2' },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: '#36534d', color: '#edf4f2' },
}, { dark: true });
const colors = HighlightStyle.define([
  { tag: tags.keyword, color: '#c9a4f3' }, { tag: tags.string, color: '#dfca85' },
  { tag: tags.number, color: '#e8b185' }, { tag: tags.comment, color: '#7e9998', fontStyle: 'italic' },
  { tag: tags.operator, color: '#92c7d6' }, { tag: tags.typeName, color: '#92c7d6' },
  { tag: tags.standard(tags.name), color: '#8fcee7' },
]);

export type SqlEditorHandle = { getRunSql: () => string | null };

export default function SqlEditor({ value, onChange, onRun, onSubmit, onExit, schema, ref }: { value: string; onChange: (value: string) => void; onRun: () => void; onSubmit: () => void; onExit: () => void; schema: Record<string, string[]>; ref?: Ref<SqlEditorHandle> }) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const language = useRef(new Compartment());
  const callbacks = useRef({ onChange, onRun, onSubmit, onExit });
  callbacks.current = { onChange, onRun, onSubmit, onExit };
  useImperativeHandle(ref, () => ({ getRunSql: () => {
    const state = view.current?.state;
    if (!state) return null;
    // CodeMirror retains this selection when the Run button takes focus.
    const selection = state.selection.main;
    return selection.empty ? state.doc.toString() : state.sliceDoc(selection.from, selection.to);
  } }), []);
  useEffect(() => {
    if (!host.current) return;
    const editor = new EditorView({ parent: host.current, state: EditorState.create({ doc: value, extensions: [
      lineNumbers(), highlightActiveLineGutter(), highlightSpecialChars(), history(), drawSelection(), highlightActiveLine(), bracketMatching(), closeBrackets(), autocompletion(),
      language.current.of(sql({ dialect: MySQL, schema })), theme, syntaxHighlighting(colors),
      EditorView.contentAttributes.of({ 'aria-label': 'SQL editor', 'aria-describedby': 'editor-shortcuts', 'spellcheck': 'false' }),
      Prec.highest(keymap.of([{ key: 'Escape', run: () => { callbacks.current.onExit(); return true; } }, { key: 'Mod-Enter', run: () => { callbacks.current.onRun(); return true; } }, { key: 'Mod-Shift-Enter', run: () => { callbacks.current.onSubmit(); return true; } }])),
      keymap.of([...closeBracketsKeymap, ...defaultKeymap, ...historyKeymap, { key: 'Tab', run: insertTab, shift: indentLess }]),
      EditorView.updateListener.of(update => { if (update.docChanged) callbacks.current.onChange(update.state.doc.toString()); }),
    ] }) });
    view.current = editor;
    return () => { editor.destroy(); view.current = null; };
    // Keep the editor and its undo history mounted while drafts and schema change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    const editor = view.current;
    if (editor && value !== editor.state.doc.toString()) editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: value } });
  }, [value]);
  const schemaSignature = JSON.stringify(schema);
  useEffect(() => {
    view.current?.dispatch({ effects: language.current.reconfigure(sql({ dialect: MySQL, schema: JSON.parse(schemaSignature) as Record<string, string[]> })) });
  }, [schemaSignature]);
  return <div className="sql-editor" ref={host} onKeyDownCapture={event => {
    if (event.key === 'Escape') {
      // Completion plugins bind Escape at their own highest precedence. Handle
      // leaving the editor during capture so a popup cannot consume the exit.
      event.preventDefault();
      event.stopPropagation();
      callbacks.current.onExit();
    }
  }} />;
}
