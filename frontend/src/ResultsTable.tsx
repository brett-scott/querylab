import type { ResultSet } from './api';
export default function ResultsTable({ result, label = 'SQL results' }: { result: ResultSet; label?: string }) {
  const format = (value: unknown) => value === null ? <span className="null-value">NULL</span> : typeof value === 'object' ? JSON.stringify(value) : String(value);
  if (!result.columns.length) return <p className="result-message">Statement executed. {result.affected_rows ?? 0} rows affected.</p>;
  return <><div className="table-scroll" tabIndex={0} aria-label={`${label}, scroll horizontally if needed`}><table><caption className="sr-only">{label}</caption><thead><tr>{result.columns.map((column, index) => <th key={`${column}-${index}`} scope="col">{column}</th>)}</tr></thead><tbody>{result.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{format(cell)}</td>)}</tr>)}</tbody></table></div>
    {result.rows.length === 0 && <p className="result-message">The query returned no rows.</p>}
    {result.truncated && <p className="truncation-notice">Result limit reached. More rows exist; narrow your query to inspect them.</p>}
  </>;
}
