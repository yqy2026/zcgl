import React from 'react';
import { describe, expect, it } from 'vitest';

import {
  calculateMatchScore,
  containsAnySearchTerm,
  containsSearchTerm,
  extractSearchTerms,
  highlightMultipleTerms,
  highlightText,
  sortByRelevance,
} from '../highlight';

describe('highlight utilities', () => {
  it('returns original text when input is empty', () => {
    expect(highlightText('资产A', '')).toBe('资产A');
    expect(highlightText('', '资产')).toBe('');
    expect(highlightMultipleTerms('资产A', [])).toBe('资产A');
  });

  it('highlights single term and escapes regex characters', () => {
    const result = highlightText('资产A+项目B', 'A+项目', 'asset-highlight');
    const parts = result as React.ReactNode[];
    const marks = parts.filter(
      (part): part is React.ReactElement =>
        React.isValidElement(part) && part.type === 'mark'
    );

    expect(marks).toHaveLength(1);
    expect(marks[0]?.props.className).toBe('asset-highlight');
    expect(marks[0]?.props.children).toBe('A+项目');
  });

  it('highlights multiple terms and ignores blank terms', () => {
    const result = highlightMultipleTerms('资产A 位于 上海', ['资产A', ' ', '上海'], 'hit');
    const parts = result as React.ReactNode[];
    const marks = parts.filter(
      (part): part is React.ReactElement =>
        React.isValidElement(part) && part.type === 'mark'
    );

    expect(marks).toHaveLength(2);
    expect(marks[0]?.props.className).toBe('hit');
    expect(marks[1]?.props.className).toBe('hit');
  });

  it('extracts and normalizes search terms', () => {
    expect(extractSearchTerms('  资产A   上海  商业  ')).toEqual(['资产A', '上海', '商业']);
    expect(extractSearchTerms('')).toEqual([]);
  });

  it('checks term containment with case-insensitive match', () => {
    expect(containsSearchTerm('Asset Center', 'asset')).toBe(true);
    expect(containsSearchTerm('Asset Center', 'hotel')).toBe(false);
    expect(containsAnySearchTerm('Asset Center', ['hotel', 'center'])).toBe(true);
    expect(containsAnySearchTerm('', ['center'])).toBe(false);
  });

  it('calculates relevance score by exact, prefix and contains rules', () => {
    expect(calculateMatchScore('asset', ['asset'])).toBe(100);
    expect(calculateMatchScore('asset center', ['asset', 'center', 'set'])).toBe(100);
    expect(calculateMatchScore('', ['asset'])).toBe(0);
  });

  it('sorts items by aggregated text-field relevance', () => {
    const items = [
      { id: '1', name: 'Asset Center', tags: 'office' },
      { id: '2', name: 'Warehouse', tags: 'asset storage' },
      { id: '3', name: 'Mall', tags: 'retail' },
    ];

    const sorted = sortByRelevance(items, ['asset', 'center'], item => [item.name, item.tags]);
    const passthrough = sortByRelevance(items, [], item => [item.name]);

    expect(sorted.map(item => item.id)).toEqual(['1', '2', '3']);
    expect(passthrough).toBe(items);
  });
});
