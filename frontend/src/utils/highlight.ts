import React from 'react';

/**
 * 高亮搜索关键词
 */
export const highlightText = (
  text: string,
  searchTerm: string,
  className = 'highlight'
): React.ReactNode => {
  if (!searchTerm || !text) {
    return text;
  }

  // 转义特殊字符
  const escapedSearchTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  // 创建正则表达式，忽略大小写
  const regex = new RegExp(`(${escapedSearchTerm})`, 'gi');

  // 分割文本
  const parts = text.split(regex);

  return parts.map((part, index) => {
    if (regex.test(part)) {
      return React.createElement(
        'mark',
        {
          key: index,
          className,
          style: {
            backgroundColor: '#fff2b8',
            padding: '0 2px',
            borderRadius: '2px',
            fontWeight: 'bold',
          },
        },
        part
      );
    }
    return part;
  });
};

/**
 * 高亮多个关键词
 */
export const highlightMultipleTerms = (
  text: string,
  searchTerms: string[],
  className = 'highlight'
): React.ReactNode => {
  if (!searchTerms.length || !text) {
    return text;
  }

  // 过滤空的搜索词
  const validTerms = searchTerms.filter(term => term.trim());
  if (!validTerms.length) {
    return text;
  }

  // 转义特殊字符并合并搜索词
  const escapedTerms = validTerms.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

  // 创建正则表达式
  const regex = new RegExp(`(${escapedTerms.join('|')})`, 'gi');

  // 分割文本
  const parts = text.split(regex);

  return parts.map((part, index) => {
    if (regex.test(part)) {
      return React.createElement(
        'mark',
        {
          key: index,
          className,
          style: {
            backgroundColor: '#fff2b8',
            padding: '0 2px',
            borderRadius: '2px',
            fontWeight: 'bold',
          },
        },
        part
      );
    }
    return part;
  });
};

/**
 * 提取搜索关键词
 */
export const extractSearchTerms = (searchText: string): string[] => {
  if (!searchText) {
    return [];
  }

  // 按空格分割，过滤空字符串
  return searchText
    .split(/\s+/)
    .filter(term => term.trim())
    .map(term => term.trim());
};

/**
 * 检查文本是否包含搜索词
 */
export const containsSearchTerm = (text: string, searchTerm: string): boolean => {
  if (!searchTerm || !text) {
    return false;
  }

  return text.toLowerCase().includes(searchTerm.toLowerCase());
};

/**
 * 检查文本是否包含任一搜索词
 */
export const containsAnySearchTerm = (text: string, searchTerms: string[]): boolean => {
  if (!searchTerms.length || !text) {
    return false;
  }

  return searchTerms.some(term => containsSearchTerm(text, term));
};

/**
 * 计算匹配度分数
 */
export const calculateMatchScore = (text: string, searchTerms: string[]): number => {
  if (!searchTerms.length || !text) {
    return 0;
  }

  const lowerText = text.toLowerCase();
  let score = 0;

  searchTerms.forEach(term => {
    const lowerTerm = term.toLowerCase();

    // 完全匹配得分最高
    if (lowerText === lowerTerm) {
      score += 100;
    }
    // 开头匹配
    else if (lowerText.startsWith(lowerTerm)) {
      score += 50;
    }
    // 包含匹配
    else if (lowerText.includes(lowerTerm)) {
      score += 25;
    }
  });

  return score;
};

/**
 * 根据搜索词排序结果
 */
export const sortByRelevance = <T>(
  items: T[],
  searchTerms: string[],
  getTextFields: (item: T) => string[]
): T[] => {
  if (!searchTerms.length) {
    return items;
  }

  return items
    .map(item => ({
      item,
      score: getTextFields(item).reduce(
        (totalScore, text) => totalScore + calculateMatchScore(text, searchTerms),
        0
      ),
    }))
    .sort((a, b) => b.score - a.score)
    .map(({ item }) => item);
};
