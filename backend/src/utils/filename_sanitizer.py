"""
文件名清理和标准化工具
处理PDF上传时的文件名兼容性问题
"""

import logging
import os
import re
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)


class FilenameSanitizer:
    """文件名清理器"""

    # 中文特殊字符到标准字符的映射
    CHINESE_SPECIAL_CHARS = {
        "【": "[",
        "】": "]",
        "（": "(",
        "）": ")",
        "《": "<",
        "》": ">",
        '"': '"',
        '"': '"',
        """: "'", """: "'",
        "：": ":",
        "，": ",",
        "。": ".",
        "；": ";",
        "！": "!",
        "？": "?",
        "·": "·",
        "…": "...",
        "—": "-",
        "–": "-",
        "℃": "C",
        "％": "%",
        "‰": "%",
        "§": "S",
        "©": "(C)",
        "®": "(R)",
        "™": "(TM)",
    }

    # 危险字符模式（需要移除或替换）
    DANGEROUS_PATTERNS = [
        r'[<>:"/\\|?*]',  # Windows不允许的字符
        r"[\x00-\x1f\x7f]",  # 控制字符
        r'[^\w\u4e00-\u9fff\-_.()\\[\\]{}:,.!?\'"%;@#&+$~= `~]',  # 只保留安全字符
    ]

    def __init__(self):
        # 预编译正则表达式以提高性能
        self._compiled_patterns = [
            re.compile(pattern) for pattern in self.DANGEROUS_PATTERNS
        ]

    def sanitize_filename(
        self, filename: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        清理文件名，确保跨平台兼容性

        Args:
            filename: 原始文件名
            options: 清理选项
                - max_length: 最大长度限制 (默认200)
                - preserve_original: 是否保留原始文件名信息 (默认True)
                - allow_unicode: 是否允许Unicode字符 (默认True)
                - replacement: 替换字符 (默认'_')

        Returns:
            清理结果字典 {
                'success': bool,
                'sanitized_filename': str,
                'original_filename': str,
                'changes_made': list,
                'warnings': list,
                'is_safe': bool
            }
        """
        if options is None:
            options = {}

        max_length = options.get("max_length", 200)
        preserve_original = options.get("preserve_original", True)
        allow_unicode = options.get("allow_unicode", True)
        replacement = options.get("replacement", "_")

        original_filename = filename
        changes_made = []
        warnings = []

        try:
            # 分离文件名和扩展名
            name, ext = os.path.splitext(filename)

            # 1. Unicode规范化
            normalized_name = unicodedata.normalize("NFKC", name)
            if normalized_name != name:
                changes_made.append("Unicode规范化 (NFKC)")
                name = normalized_name

            # 2. 替换中文特殊字符
            cleaned_name = name
            for chinese_char, standard_char in self.CHINESE_SPECIAL_CHARS.items():
                if chinese_char in cleaned_name:
                    cleaned_name = cleaned_name.replace(chinese_char, standard_char)
                    changes_made.append(
                        f"替换中文特殊字符: {chinese_char} → {standard_char}"
                    )

            # 3. 处理危险字符
            for pattern in self._compiled_patterns:
                matches = pattern.findall(cleaned_name)
                if matches:
                    changes_made.append(f"移除危险字符: {', '.join(matches)}")
                    cleaned_name = pattern.sub(replacement, cleaned_name)

            # 4. 处理连续的替换字符
            consecutive_replacement = re.compile(rf"{re.escape(replacement)}{{2,}}")
            if consecutive_replacement.search(cleaned_name):
                changes_made.append("合并连续的特殊字符")
                cleaned_name = consecutive_replacement.sub(replacement, cleaned_name)

            # 5. 移除开头和结尾的特殊字符
            trimmed_name = cleaned_name.strip("._-")
            if trimmed_name != cleaned_name:
                changes_made.append("移除开头/结尾的特殊字符")
                cleaned_name = trimmed_name

            # 6. 长度检查和截断
            if len(cleaned_name) > max_length - len(ext):
                original_length = len(cleaned_name)
                # 智能截断：保留开头和结尾重要信息
                if allow_unicode and len(cleaned_name) > 50:
                    # 对于长文件名，保留开头部分和结尾部分
                    keep_start = max_length - len(ext) - 15  # 保留结尾15个字符
                    cleaned_name = (
                        cleaned_name[:keep_start] + "..." + cleaned_name[-12:]
                    )
                else:
                    # 简单截断
                    cleaned_name = cleaned_name[: max_length - len(ext)]

                changes_made.append(
                    f"文件名截断: {original_length} → {len(cleaned_name)}"
                )
                warnings.append("文件名已被截断以符合系统限制")

            # 7. 确保文件名不为空
            if not cleaned_name:
                cleaned_name = "untitled_document"
                changes_made.append("文件名为空，使用默认名称")
                warnings.append("原始文件名无效，已使用默认名称")

            # 8. 重新组合文件名
            sanitized_filename = cleaned_name + ext

            # 9. 最终安全检查
            is_safe = self._is_filename_safe(sanitized_filename)

            # 10. 验证扩展名
            if not ext.lower().endswith(".pdf"):
                sanitized_filename += ".pdf"
                changes_made.append("添加PDF扩展名")
                warnings.append("文件缺少PDF扩展名，已自动添加")

            return {
                "success": True,
                "sanitized_filename": sanitized_filename,
                "original_filename": original_filename if preserve_original else None,
                "changes_made": changes_made,
                "warnings": warnings,
                "is_safe": is_safe,
                "length": len(sanitized_filename),
            }

        except Exception as e:
            logger.error(f"文件名清理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_filename": original_filename,
                "sanitized_filename": f"sanitized_{hash(original_filename) % 10000}.pdf",
                "changes_made": ["文件名清理失败，使用随机名称"],
                "warnings": ["文件名清理过程中发生错误"],
                "is_safe": False,
            }

    def _is_filename_safe(self, filename: str) -> bool:
        """检查文件名是否安全"""
        try:
            # 检查是否包含危险字符
            for pattern in self._compiled_patterns:
                if pattern.search(filename):
                    return False

            # 检查长度
            if len(filename) > 260:  # Windows MAX_PATH限制
                return False

            # 检查是否为空
            if not filename or filename.strip() == "":
                return False

            # 检查是否包含保留名称（Windows）
            reserved_names = {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                "COM1",
                "COM2",
                "COM3",
                "COM4",
                "COM5",
                "COM6",
                "COM7",
                "COM8",
                "COM9",
                "LPT1",
                "LPT2",
                "LPT3",
                "LPT4",
                "LPT5",
                "LPT6",
                "LPT7",
                "LPT8",
                "LPT9",
            }

            name_without_ext = os.path.splitext(filename)[0].upper()
            if name_without_ext in reserved_names:
                return False

            return True

        except Exception as e:
            logger.error(f"文件名安全检查失败: {e}")
            return False

    def validate_filename(self, filename: str) -> dict[str, Any]:
        """
        验证文件名

        Args:
            filename: 要验证的文件名

        Returns:
            验证结果 {
                'valid': bool,
                'issues': list,
                'suggestions': list,
                'severity': 'low' | 'medium' | 'high'
            }
        """
        issues = []
        suggestions = []
        severity = "low"

        # 长度检查
        if len(filename) > 200:
            issues.append(f"文件名过长 ({len(filename)} > 200)")
            suggestions.append("建议缩短文件名")
            severity = "high"
        elif len(filename) > 150:
            issues.append(f"文件名较长 ({len(filename)} > 150)")
            suggestions.append("考虑缩短文件名以提高兼容性")
            severity = "medium"

        # 特殊字符检查
        has_chinese_special = any(
            char in self.CHINESE_SPECIAL_CHARS for char in filename
        )
        if has_chinese_special:
            issues.append("包含中文特殊字符")
            suggestions.append("建议将中文特殊字符替换为标准字符")
            severity = "medium"

        # Unicode字符检查
        has_unicode = any(ord(char) > 127 for char in filename)
        if has_unicode:
            issues.append("包含Unicode字符")
            suggestions.append("确保系统支持Unicode字符")
            if severity == "low":
                severity = "low"

        # 危险字符检查
        has_dangerous = any(
            pattern.search(filename) for pattern in self._compiled_patterns
        )
        if has_dangerous:
            issues.append("包含系统不兼容字符")
            suggestions.append("移除或替换特殊字符")
            severity = "high"

        # 扩展名检查
        if not filename.lower().endswith(".pdf"):
            issues.append("缺少PDF扩展名")
            suggestions.append("确保文件扩展名为.pdf")
            severity = "medium"

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "severity": severity,
        }

    def generate_suggested_filename(self, filename: str) -> str:
        """
        生成建议的文件名

        Args:
            filename: 原始文件名

        Returns:
            建议的文件名
        """
        result = self.sanitize_filename(filename)
        return result["sanitized_filename"]

    def get_filename_info(self, filename: str) -> dict[str, Any]:
        """
        获取文件名详细信息

        Args:
            filename: 文件名

        Returns:
            文件名信息字典
        """
        name, ext = os.path.splitext(filename)

        return {
            "filename": filename,
            "name": name,
            "extension": ext,
            "length": len(filename),
            "name_length": len(name),
            "has_unicode": any(ord(char) > 127 for char in filename),
            "has_chinese": any("\u4e00" <= char <= "\u9fff" for char in filename),
            "has_chinese_special": any(
                char in self.CHINESE_SPECIAL_CHARS for char in filename
            ),
            "extension_is_pdf": ext.lower() == ".pdf",
            "is_safe": self._is_filename_safe(filename),
        }


# 创建全局实例
filename_sanitizer = FilenameSanitizer()


# 便捷函数
def sanitize_filename(filename: str, **kwargs) -> dict[str, Any]:
    """便捷的文件名清理函数"""
    return filename_sanitizer.sanitize_filename(filename, kwargs)


def validate_filename(filename: str) -> dict[str, Any]:
    """便捷的文件名验证函数"""
    return filename_sanitizer.validate_filename(filename)


def get_suggested_filename(filename: str) -> str:
    """便捷的建议文件名生成函数"""
    return filename_sanitizer.generate_suggested_filename(filename)
