"""
Grep tool integration for code analysis
支持在代码库中搜索，并返回带上下文的代码片段
"""
import subprocess
import re
from typing import Optional, List, Tuple
from pathlib import Path


class GrepTool:
    """Tool for executing grep commands safely with context"""
    
    @staticmethod
    def extract_grep_command(text: str) -> Optional[str]:
        """
        从模型响应中提取 grep 命令
        只提取明确标记在 <grep_command> 标签中的命令，避免误解析
        
        Extract grep command from model response
        Only extract commands explicitly marked in <grep_command> tags to avoid false positives
        
        Args:
            text: Model response text
            
        Returns:
            Grep command if found, None otherwise
        """
        # 优先查找 <grep_command> 标签内的命令（最可靠）
        tag_match = re.search(r'<grep_command>\s*(.*?)\s*</grep_command>', text, re.DOTALL | re.IGNORECASE)
        if tag_match:
            cmd = tag_match.group(1).strip()
            # 验证确实是 grep 命令
            if cmd.lower().startswith('grep'):
                return cmd
        
        # 查找代码块中的 grep 命令（次优先）
        code_block_match = re.search(r'```(?:bash|sh)?\s*\n(grep[^`]+)\n```', text, re.IGNORECASE | re.MULTILINE)
        if code_block_match:
            cmd = code_block_match.group(1).strip()
            if cmd.lower().startswith('grep'):
                return cmd
        
        # 不提取反引号或普通文本中的 grep，避免误解析
        # 只接受明确标记的命令
        
        return None
    
    @staticmethod
    def execute_grep(command: str, codebase_path: str = ".") -> Tuple[bool, str]:
        """
        执行 grep 命令，返回带上下文的代码片段
        自动添加 -C 2 参数以包含上下2行代码
        
        Execute grep command safely with context lines
        
        Args:
            command: Grep command to execute (e.g., "grep -rn 'pattern' path" or "grep 'pattern' file.c")
            codebase_path: Path to codebase root (待修复项目的根目录)
            
        Returns:
            Tuple of (success, formatted_output)
        """
        # 清理命令
        sanitized = command.strip()
        
        # 检查是否是 grep 命令
        if not sanitized.lower().startswith('grep'):
            return False, "Error: Not a grep command"
        
        # 确保 codebase_path 存在
        codebase = Path(codebase_path).resolve()
        if not codebase.exists():
            return False, f"Error: Codebase path does not exist: {codebase_path}"
        
        # 解析命令
        parts = sanitized.split()
        if len(parts) < 2:
            return False, "Error: Invalid grep command"
        
        # 构建安全的 grep 命令
        grep_args = ['grep']
        
        # 检查是否已有上下文参数
        has_context = any(flag in parts for flag in ['-C', '-A', '-B', '--context', '--after-context', '--before-context'])
        
        # 如果没有上下文参数，添加 -C 2（上下各2行）
        if not has_context:
            grep_args.append('-C')
            grep_args.append('2')
        
        # 解析标志和参数
        i = 1
        pattern = None
        search_paths = []
        
        # 跳过 'grep' 本身
        while i < len(parts):
            part = parts[i]
            
            # 如果是标志
            if part.startswith('-'):
                # 跳过已处理的上下文标志
                if part in ['-C', '-A', '-B', '--context', '--after-context', '--before-context']:
                    i += 2  # 跳过标志和值
                    continue
                elif part in ['-n', '-r', '-E', '-i', '-w']:
                    grep_args.append(part)
                    i += 1
                    continue
                else:
                    # 其他标志，添加到命令中
                    grep_args.append(part)
                    i += 1
                    continue
            
            # 如果是模式（还没有找到模式）
            if pattern is None:
                # 移除引号
                pattern = part.strip('\'"')
                grep_args.append(pattern)
                i += 1
            else:
                # 这是搜索路径
                search_paths.append(part)
                i += 1
        
        # 如果没有指定搜索路径，默认搜索整个代码库
        if not search_paths:
            grep_args.append('-r')
            grep_args.append('.')
        else:
            # 将相对路径转换为绝对路径（相对于 codebase_path）
            for path in search_paths:
                abs_path = (codebase / path).resolve()
                if abs_path.exists() and codebase in abs_path.parents or abs_path == codebase:
                    grep_args.append(str(abs_path.relative_to(codebase)))
                else:
                    # 如果路径不存在，尝试作为模式匹配
                    grep_args.append(path)
        
        # 执行 grep 命令
        try:
            result = subprocess.run(
                grep_args,
                cwd=str(codebase),
                capture_output=True,
                text=True,
                timeout=30,  # 增加超时时间
                errors='ignore'
            )
            
            if result.returncode == 0:
                # 格式化输出，使其更易读
                formatted = GrepTool._format_grep_output(result.stdout, codebase)
                return True, formatted
            elif result.returncode == 1:
                return True, "No matches found for the search pattern."
            else:
                return False, f"Grep error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Error: Command timeout (exceeded 30 seconds)"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def _format_grep_output(output: str, codebase_path: Path) -> str:
        """
        格式化 grep 输出，使其更易读
        将输出组织为：文件名 -> 匹配行（带上下文）
        保留所有上下文行（-C 2 的前后2行）
        
        Format grep output for better readability
        Preserves all context lines (2 lines before and after from -C 2)
        
        grep -n -C 输出格式：
        - 上下文行：file-line-content（用 "-" 分隔）
        - 匹配行：file:line:content（用 ":" 分隔）
        - 分隔符：--（不同匹配块之间）
        """
        if not output.strip():
            return "No matches found."
        
        lines = output.split('\n')
        formatted_lines = []
        current_file = None
        file_matches = []
        files_seen = set()
        
        for line in lines:
            if not line.strip():
                # 保留空行作为分隔
                if current_file and file_matches:
                    file_matches.append("")
                continue
            
            # grep -C 输出中的分隔符（表示不同匹配块之间的分隔）
            if line.strip() == '--':
                if current_file and file_matches:
                    file_matches.append("  ---")
                continue
            
            # grep -n -C 输出格式：
            # 上下文行：file-line-content（用 "-" 分隔，如 "41-    UA_Subscription *sub"）
            # 匹配行：file:line:content（用 ":" 分隔，如 "43:        UA_Session_deleteSubscription"）
            
            # 先尝试匹配行格式（file:line:content）
            if ':' in line:
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    file_part = parts[0]
                    line_num = parts[1]
                    content = parts[2]
                    
                    # 检查是否是新的文件
                    if file_part != current_file:
                        # 保存上一个文件的结果
                        if current_file and file_matches:
                            formatted_lines.append(f"\n=== File: {current_file} ===")
                            formatted_lines.extend(file_matches)
                        
                        current_file = file_part
                        file_matches = []
                        files_seen.add(file_part)
                    
                    # 这是匹配行（用 ":" 分隔）
                    file_matches.append(f"  Line {line_num}:>>> {content}")
                    continue
            
            # 再尝试上下文行格式（file-line-content）
            if '-' in line:
                # 尝试解析 file-line-content 格式
                # 需要找到第一个 "-" 的位置，它分隔文件名和行号
                # 但文件名本身可能包含 "-"，所以需要更智能的解析
                # 简单方法：找到第一个 "数字-" 模式
                import re
                match = re.match(r'^([^:]+?)-(\d+)-(.*)$', line)
                if match:
                    file_part = match.group(1)
                    line_num = match.group(2)
                    content = match.group(3)
                    
                    # 检查是否是新的文件
                    if file_part != current_file:
                        # 保存上一个文件的结果
                        if current_file and file_matches:
                            formatted_lines.append(f"\n=== File: {current_file} ===")
                            formatted_lines.extend(file_matches)
                        
                        current_file = file_part
                        file_matches = []
                        files_seen.add(file_part)
                    
                    # 这是上下文行（用 "-" 分隔）
                    file_matches.append(f"  Line {line_num}:    {content}")
                    continue
        
        # 添加最后一个文件的结果
        if current_file and file_matches:
            formatted_lines.append(f"\n=== File: {current_file} ===")
            formatted_lines.extend(file_matches)
        
        # 如果没有格式化成功，返回原始输出（保留所有上下文）
        if not formatted_lines:
            return output
        
        result = "\n".join(formatted_lines)
        # 添加总结
        file_count = len(files_seen)
        if file_count > 0:
            result = f"Found matches in {file_count} file(s):{result}"
        
        return result
    
    @staticmethod
    def is_grep_request(text: str) -> bool:
        """
        Check if text contains a grep command request
        
        Args:
            text: Text to check
            
        Returns:
            True if grep command is requested
        """
        grep_patterns = [
            r'grep\s+',
            r'use\s+grep',
            r'search\s+for',
            r'find\s+.*\s+in\s+.*\s+file',
            r'need\s+to\s+.*grep',
        ]
        
        text_lower = text.lower()
        for pattern in grep_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False

