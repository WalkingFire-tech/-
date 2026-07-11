import re


def verify_code_response(query: str, response: str) -> dict:
    issues = []
    code_blocks = re.findall(r'```[\w]*\n(.*?)```', response, re.DOTALL)

    if not code_blocks:
        standalone_code = re.findall(r'(?:def |class |import |from |if |for |while |return |print\(|console\.log|function |var |let |const )', response)
        if standalone_code:
            issues.append("代码未使用代码块格式")

    for i, block in enumerate(code_blocks):
        block_issues = _check_code_block(block, i + 1)
        issues.extend(block_issues)

    if code_blocks:
        for i, block in enumerate(code_blocks):
            lines = block.strip().split('\n')
            if len(lines) < 3:
                issues.append(f"代码块{i+1}过短({len(lines)}行)，可能不完整")

    query_lower = query.lower()
    if any(kw in query_lower for kw in ["python", "py", "函数", "def"]):
        if code_blocks and not any('def ' in b or 'import ' in b for b in code_blocks):
            issues.append("请求Python代码但未包含函数定义或导入")
    elif any(kw in query_lower for kw in ["javascript", "js", "前端"]):
        if code_blocks and not any('function ' in b or 'const ' in b or 'let ' in b or 'var ' in b for b in code_blocks):
            issues.append("请求JavaScript代码但未包含函数定义")

    if issues:
        return {"passed": False, "detail": "; ".join(issues[:3])}

    if code_blocks:
        return {"passed": True, "detail": f"{len(code_blocks)}个代码块语法检查通过"}

    return {"passed": True, "detail": "代码相关回复，无代码块需验证"}


def _check_code_block(code: str, block_num: int) -> list:
    issues = []
    lines = code.strip().split('\n')

    open_parens = code.count('(') - code.count(')')
    open_brackets = code.count('[') - code.count(']')
    open_braces = code.count('{') - code.count('}')

    if open_parens != 0:
        issues.append(f"代码块{block_num}括号不匹配(差{open_parens})")
    if open_brackets != 0:
        issues.append(f"代码块{block_num}方括号不匹配(差{open_brackets})")
    if open_braces != 0:
        issues.append(f"代码块{block_num}花括号不匹配(差{open_braces})")

    if ':' in code and not any(kw in code for kw in ['def ', 'if ', 'for ', 'while ', 'class ', 'elif ', 'else:', 'try:', 'except', 'with ']):
        pass

    if code.strip().endswith(('(', '[', '{', ',', '&&', '||', '+', '-', '*', '/')):
        issues.append(f"代码块{block_num}末尾不完整")

    if 'def ' in code:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('def ') and stripped.endswith(':'):
                if not stripped.endswith('):') and '(' in stripped:
                    pass
                break

    return issues