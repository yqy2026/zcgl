/**
 * 合同终止原因配置
 *
 * @description 提供常用的合同终止原因选项
 * @module constants/reasons
 */

export const TERMINATION_REASONS = [
  { value: '协议解除', label: '协议解除' },
  { value: '租户违约', label: '租户违约' },
  { value: '欠租', label: '欠租' },
  { value: '资产收回', label: '资产收回' },
  { value: '不可抗力', label: '不可抗力' },
  { value: '其他', label: '其他' },
];

/**
 * 获取终止原因显示文本
 */
export const getTerminationReasonLabel = (value: string): string => {
  const reason = TERMINATION_REASONS.find(r => r.value === value);
  return reason?.label || value;
};
