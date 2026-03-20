/**
 * 将 id 值归一化：空值/空字符串 → undefined，有效值 → 去首尾空格后的字符串。
 */
export const normalizeOptionalId = (value: unknown): string | undefined => {
  if (value == null) return undefined;
  const str = String(value).trim();
  return str === '' ? undefined : str;
};
