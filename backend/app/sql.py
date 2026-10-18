"""SQL client-script handling and result comparison (not a security sandbox).

Database grants are the security boundary; lexical restrictions reduce abuse of
costly primitives available even to unprivileged MySQL users.
"""
from datetime import date, datetime, time
from decimal import Decimal
import re
import sqlparse
from sqlparse import tokens as T


class SQLPolicyError(ValueError):
    pass


def split_script(script: str) -> list[str]:
    if not script.strip():
        raise SQLPolicyError("Enter SQL before running or submitting.")
    if len(script.encode("utf-8")) > 32000:
        raise SQLPolicyError("SQL scripts are limited to 32 KB.")
    # DELIMITER is a mysql-client directive, never a server statement. Segments
    # without a directive use sqlparse's stored-routine-aware statement splitter.
    delimiter = ";"
    buffer = []
    statements = []
    custom = False
    for line in script.splitlines(keepends=True):
        match = re.fullmatch(r"\s*DELIMITER\s+(\S+)\s*", line, re.I)
        if match:
            if "".join(buffer).strip():
                statements.extend(_split_segment("".join(buffer), delimiter))
            buffer = []
            delimiter = match[1]
            if len(delimiter) > 8 or any(c in delimiter for c in "'\"`\\"):
                raise SQLPolicyError("Use a simple DELIMITER such as $$ or //.")
            custom = True
        else:
            buffer.append(line)
    statements.extend(_split_segment("".join(buffer), delimiter))
    statements = [s.strip() for s in statements if s.strip()]
    if not statements:
        raise SQLPolicyError("Enter an executable SQL statement.")
    if len(statements) > 30:
        raise SQLPolicyError("Run at most 30 statements per script.")
    return statements


def _split_segment(script: str, delimiter: str) -> list[str]:
    if delimiter == ";":
        return [query for segment in sqlparse.split(script)
                for query in _split_read_queries(segment.rstrip().removesuffix(";"))]
    # Walk strings/comments using sqlparse's lexer so delimiter-like text inside
    # quoted SQL or comments cannot split a routine body.
    from sqlparse.lexer import tokenize
    pieces, buffer = [], ""
    for kind, value in tokenize(script):
        protected = kind in T.Literal.String or kind in T.Comment or kind in T.Name
        if protected:
            buffer += value
            continue
        buffer += value
        while delimiter in buffer:
            # The delimiter may span punctuation tokens; protect all earlier
            # string/comment content by replacing only trailing delimiters.
            if not buffer.endswith(delimiter):
                break
            pieces.append(buffer[:-len(delimiter)])
            buffer = ""
    if buffer.strip():
        pieces.append(buffer)
    return pieces


def _split_read_queries(script: str) -> list[str]:
    """Allow adjacent SELECT/CTE queries on new lines without changing their SQL.

    Explicit delimiters are handled first. Do not infer boundaries in routines,
    DML, strings, comments, nested queries or compound SELECT operands.
    """
    from sqlparse.lexer import tokenize
    tokens = list(tokenize(script))
    significant = [(kind, value) for kind, value in tokens
                   if kind not in T.Whitespace and kind not in T.Comment]
    if not significant or significant[0][1].upper() not in {"SELECT", "WITH"}:
        return [script]
    pieces = []
    start = offset = depth = 0
    seen_select = union_operand = False
    line_start = True
    for index, (kind, value) in enumerate(tokens):
        if kind in T.Whitespace or kind in T.Comment:
            if "\n" in value or "\r" in value:
                line_start = True
        else:
            word = value.upper()
            select = kind in T.Keyword.DML and word == "SELECT"
            cte = kind in T.Keyword.CTE and word == "WITH"
            if cte:
                following = next((tokens[j][1].upper() for j in range(index + 1, len(tokens))
                                  if tokens[j][0] not in T.Whitespace and tokens[j][0] not in T.Comment), "")
                cte = following != "ROLLUP"
            if depth == 0:
                if not seen_select and kind in T.Keyword.DML and not select:
                    return [script]
                if seen_select and line_start and (select or cte) and not union_operand:
                    pieces.append(script[start:offset].rstrip())
                    start = offset
                    seen_select = False
                if select:
                    seen_select = True
                    union_operand = False
                elif kind in T.Keyword and word.split()[0] in {"UNION", "INTERSECT", "EXCEPT"}:
                    union_operand = True
            if kind in T.Punctuation:
                if value == "(":
                    depth += 1
                elif value == ")":
                    depth -= 1
                    if depth == 0:
                        union_operand = False
            line_start = False
        offset += len(value)
    pieces.append(script[start:].strip())
    return pieces


def policy_tokens(script: str) -> str:
    # Executable MySQL comments can conceal privileged or resource-heavy SQL.
    if re.search(r"/\*\s*!", script):
        raise SQLPolicyError("Executable MySQL comments are not supported.")
    flattened = []
    for parsed in sqlparse.parse(script):
        for token in parsed.flatten():
            if token.ttype in T.Comment or token.ttype in T.Literal.String:
                continue
            flattened.append(token.value.strip("`"))
    return " ".join(flattened).upper()


def validate_script(script: str, *, grading_type: str | None = None) -> list[str]:
    statements = split_script(script)
    for statement in statements:
        clean = sqlparse.format(statement, strip_comments=True).strip()
        clause = re.match(r"^(GROUP\s+BY|ORDER\s+BY|WHERE|HAVING|LIMIT|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|JOIN)\b", clean, re.I)
        if clause:
            name = re.sub(r"\s+", " ", clause.group(1).upper())
            raise SQLPolicyError(f"{name} is part of a query, not a separate statement. Remove the semicolon before {name} and run the complete query.")
    plain = policy_tokens(script)
    denied = r"\b(?:DEFINER|OUTFILE|DUMPFILE|LOAD_FILE|LOAD\s+DATA|SLEEP|BENCHMARK|GET_LOCK|RELEASE_LOCK|PREPARE|EXECUTE\s+IMMEDIATE|FLUSH|SHUTDOWN|INSTALL|UNINSTALL|GRANT|REVOKE|CREATE\s+USER|ALTER\s+USER|SET\s+(?:GLOBAL|PERSIST)|INFORMATION_SCHEMA|PERFORMANCE_SCHEMA|SYS|MYSQL)\b"
    if re.search(denied, plain):
        raise SQLPolicyError("This statement uses an operation outside the QueryLab workspace policy.")
    if grading_type == "query":
        if len(statements) != 1 or not re.match(r"^\s*(SELECT|WITH)\b", sqlparse.format(statements[0], strip_comments=True), re.I):
            raise SQLPolicyError("Submit one SELECT or WITH query for a query challenge.")
    if grading_type in {"function", "procedure"}:
        for statement in statements:
            clean = sqlparse.format(statement, strip_comments=True).strip()
            if not re.match(rf"^(CREATE\s+{grading_type}|DROP\s+{grading_type}\s+(?:IF\s+EXISTS\s+)?)\b", clean, re.I):
                raise SQLPolicyError(f"Submit only the CREATE {grading_type.upper()} definition and optional DROP statement.")
    return statements


def json_value(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime, time)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def normalized(value):
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return Decimal(str(value)).normalize()
    return json_value(value)


def same_result(actual: dict, expected: dict) -> bool:
    return (actual["columns"] == expected["columns"]
            and len(actual["rows"]) == len(expected["rows"])
            and [[normalized(v) for v in row] for row in actual["rows"]]
            == [[normalized(v) for v in row] for row in expected["rows"]])
