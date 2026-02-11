import React, { useState, useEffect } from 'react';
import { Input, Alert, Typography, Space, Button, Tag, Divider } from 'antd';
import {
  InfoCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { createLogger } from '@/utils/logger';
import styles from './FilenameValidator.module.css';

const componentLogger = createLogger('FilenameValidator');
const { Text } = Typography;

interface FilenameValidationResult {
  valid: boolean;
  issues: string[];
  suggestions: string[];
  severity: 'low' | 'medium' | 'high';
}

interface FilenameValidatorProps {
  filename: string;
  onValidationChange?: (isValid: boolean, sanitizedFilename?: string) => void;
  onFilenameChange?: (newFilename: string) => void;
  showSuggestions?: boolean;
  className?: string;
}

export const FilenameValidator: React.FC<FilenameValidatorProps> = ({
  filename,
  onValidationChange,
  onFilenameChange,
  showSuggestions = true,
  className = '',
}) => {
  const [validationResult, setValidationResult] = useState<FilenameValidationResult | null>(null);
  const [suggestedFilename, setSuggestedFilename] = useState<string>('');
  const [_loading, setLoading] = useState<boolean>(false);
  const [editing, setEditing] = useState<boolean>(false);
  const [customFilename, setCustomFilename] = useState<string>(filename);

  // 中文特殊字符映射
  const chineseSpecialCharsMap: { [key: string]: string } = {
    '【': '[',
    '】': ']',
    '（': '(',
    '）': ')',
    '《': '<',
    '》': '>',
    '\u201C': '"', // Left double quotation mark
    '\u201D': '"', // Right double quotation mark
    '\u2018': "'", // Left single quotation mark
    '\u2019': "'", // Right single quotation mark
    '：': ':',
    '，': ',',
    '。': '.',
    '；': ';',
    '！': '!',
    '？': '?',
    '…': '...',
  };

  // 本地文件名验证
  const validateLocalFilename = (fname: string): FilenameValidationResult => {
    const issues: string[] = [];
    const suggestions: string[] = [];
    let severity: 'low' | 'medium' | 'high' = 'low';

    // 长度检查
    if (fname.length > 200) {
      issues.push(`文件名过长 (${fname.length} > 200)`);
      suggestions.push('建议缩短文件名');
      severity = 'high';
    } else if (fname.length > 150) {
      issues.push(`文件名较长 (${fname.length} > 150)`);
      suggestions.push('考虑缩短文件名以提高兼容性');
      severity = 'medium';
    }

    // 中文特殊字符检查
    const hasChineseSpecial = Object.keys(chineseSpecialCharsMap).some(char =>
      fname.includes(char)
    );
    if (hasChineseSpecial !== undefined && hasChineseSpecial !== null) {
      issues.push('包含中文特殊字符');
      suggestions.push('建议将中文特殊字符替换为标准字符');
      if (severity === 'low') severity = 'medium';
    }

    // Unicode字符检查
    const hasUnicode = [...fname].some(char => char.charCodeAt(0) > 127);
    if (hasUnicode !== undefined && hasUnicode !== null) {
      issues.push('包含Unicode字符');
      suggestions.push('确保系统支持Unicode字符');
    }

    // 扩展名检查
    if (!fname.toLowerCase().endsWith('.pdf')) {
      issues.push('缺少PDF扩展名');
      suggestions.push('确保文件扩展名为.pdf');
      severity = 'medium';
    }

    // 危险字符检查
    const dangerousChars = /[<>:"/\\|?*]/;
    if (dangerousChars.test(fname)) {
      issues.push('包含系统不兼容字符');
      suggestions.push('移除或替换特殊字符');
      severity = 'high';
    }

    return {
      valid: issues.length === 0,
      issues,
      suggestions,
      severity,
    };
  };

  // 生成本地建议文件名
  const generateLocalSuggestedFilename = (fname: string): string => {
    let suggested = fname;

    // 替换中文特殊字符
    Object.entries(chineseSpecialCharsMap).forEach(([chinese, standard]) => {
      suggested = suggested.replace(new RegExp(chinese, 'g'), standard);
    });

    // 移除危险字符
    suggested = suggested.replace(/[<>:"/\\|?*]/g, '_');

    // 合并连续的下划线
    suggested = suggested.replace(/_{2,}/g, '_');

    // 移除开头和结尾的特殊字符
    suggested = suggested.replace(/^[._-]+|[._-]+$/g, '');

    // 确保有PDF扩展名
    if (!suggested.toLowerCase().endsWith('.pdf')) {
      suggested += '.pdf';
    }

    return suggested;
  };

  const validateFilename = async (fname: string) => {
    if (!fname) {
      setValidationResult(null);
      setSuggestedFilename('');
      return;
    }

    setLoading(true);

    try {
      // 首先进行本地验证（快速响应）
      const localResult = validateLocalFilename(fname);
      setValidationResult(localResult);

      // 生成本地建议文件名
      const localSuggested = generateLocalSuggestedFilename(fname);
      setSuggestedFilename(localSuggested);

      // 如果需要服务器验证（可选）
      if (
        showSuggestions !== undefined &&
        showSuggestions !== null &&
        localResult.issues.length > 0
      ) {
        try {
          // const response = await validateFilenameAPI(fname);
          // setSuggestedFilename(response.suggested_filename || localSuggested);
        } catch (error) {
          componentLogger.warn(`服务器验证失败: ${String(error)}`);
        }
      }
    } catch (error) {
      componentLogger.error('文件名验证失败:', error as Error);
      setValidationResult({
        valid: false,
        issues: ['验证过程中发生错误'],
        suggestions: ['请稍后重试'],
        severity: 'high',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    validateFilename(filename);
    setCustomFilename(filename);
  }, [filename]);

  useEffect(() => {
    if (validationResult !== undefined && validationResult !== null && onValidationChange) {
      onValidationChange(
        validationResult.valid,
        validationResult.valid ? undefined : suggestedFilename
      );
    }
  }, [validationResult, suggestedFilename, onValidationChange]);

  const handleCustomFilenameChange = (value: string) => {
    setCustomFilename(value);
    validateFilename(value);
    if (onFilenameChange !== undefined && onFilenameChange !== null) {
      onFilenameChange(value);
    }
  };

  const acceptSuggestion = () => {
    setCustomFilename(suggestedFilename);
    if (onFilenameChange !== undefined && onFilenameChange !== null) {
      onFilenameChange(suggestedFilename);
    }
  };

  const getStatusIcon = () => {
    if (!validationResult) return <InfoCircleOutlined className={styles.statusInfoIcon} />;
    if (validationResult.valid) return <CheckCircleOutlined className={styles.statusSuccessIcon} />;
    if (validationResult.severity === 'high')
      return <ExclamationCircleOutlined className={styles.statusErrorIcon} />;
    return <ExclamationCircleOutlined className={styles.statusWarningIcon} />;
  };

  const getStatusTextClass = () => {
    if (!validationResult) return styles.statusInfoText;
    if (validationResult.valid) return styles.statusSuccessText;
    if (validationResult.severity === 'high') return styles.statusErrorText;
    return styles.statusWarningText;
  };

  const getStatusText = () => {
    if (!validationResult) return '正在验证...';
    if (validationResult.valid) return '文件名符合要求';
    if (validationResult.severity === 'high') return '文件名存在问题，建议修改';
    return '文件名可以优化';
  };

  const isFilenameInvalid = validationResult != null && validationResult.valid === false;

  return (
    <div className={`filename-validator ${className}`}>
      <Space orientation="vertical" size="small" className={styles.fullWidthStack}>
        {/* 状态显示 */}
        <div className={styles.statusRow}>
          {getStatusIcon()}
          <Text strong className={getStatusTextClass()}>
            {getStatusText()}
          </Text>
          {validationResult && (
            <Tag
              color={
                validationResult.valid
                  ? 'success'
                  : validationResult.severity === 'high'
                    ? 'error'
                    : 'warning'
              }
            >
              {validationResult.severity === 'high'
                ? '严重'
                : validationResult.severity === 'medium'
                  ? '警告'
                  : '轻微'}
            </Tag>
          )}
        </div>

        {/* 文件名输入 */}
        <div>
          <div className={styles.sectionHeaderRow}>
            <Text strong>文件名:</Text>
            {!editing && (
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => setEditing(true)}
              >
                编辑
              </Button>
            )}
          </div>
          {editing ? (
            <Input
              value={customFilename}
              onChange={e => handleCustomFilenameChange(e.target.value)}
              onBlur={() => setEditing(false)}
              placeholder="输入文件名"
              status={validationResult && !validationResult.valid ? 'error' : undefined}
            />
          ) : (
            <div
              className={`${styles.filenamePreviewBox} ${isFilenameInvalid ? styles.filenamePreviewBoxError : ''}`}
            >
              <Text code className={styles.filenamePreviewText}>
                {customFilename}
              </Text>
            </div>
          )}
        </div>

        {/* 验证结果详情 */}
        {validationResult && (
          <>
            {validationResult.issues.length > 0 && (
              <Alert
                type={validationResult.severity === 'high' ? 'error' : 'warning'}
                showIcon
                title="发现以下问题:"
                description={
                  <ul className={styles.issueList}>
                    {validationResult.issues.map(issue => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                }
                className={styles.issuesAlert}
              />
            )}

            {/* 建议的文件名 */}
            {showSuggestions && suggestedFilename !== filename && (
              <div>
                <Divider className={styles.sectionDivider} />
                <div className={styles.sectionHeaderRow}>
                  <Text strong>建议的文件名:</Text>
                  <Button type="primary" size="small" onClick={acceptSuggestion}>
                    采用建议
                  </Button>
                </div>
                <div className={styles.suggestedFilenameBox}>
                  <Text code className={styles.suggestedFilenameText}>
                    {suggestedFilename}
                  </Text>
                </div>
              </div>
            )}

            {/* 改进建议 */}
            {validationResult.suggestions.length > 0 && (
              <div>
                <Divider className={styles.sectionDivider} />
                <Text strong>改进建议:</Text>
                <ul className={styles.suggestionList}>
                  {validationResult.suggestions.map(suggestion => (
                    <li key={suggestion}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {/* 使用提示 */}
        <div className={styles.usageTipsBox}>
          <Text className={styles.usageTipsText}>
            <InfoCircleOutlined className={styles.usageTipsIcon} />
            <strong>文件名最佳实践:</strong>
            <br />
            • 避免使用中文特殊字符【】（）
            <br />
            • 文件名长度建议在150字符以内
            <br />
            • 确保以.pdf结尾
            <br />• 避免使用&lt;&gt;:&quot;/\\|?*等特殊字符
          </Text>
        </div>
      </Space>
    </div>
  );
};

export default FilenameValidator;
