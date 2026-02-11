import React from 'react';
import { Typography, Button, Empty } from 'antd';
import { MessageManager } from '@/utils/messageManager';
import { useAnalyticsFiltersContext } from './FiltersContext';
import styles from './Filters.module.css';

const { Text } = Typography;

/**
 * Filter history list and save filter input
 */
const FilterHistorySection: React.FC = () => {
  const {
    showHistory,
    saveName,
    setSaveName,
    handleSaveFilters,
    searchHistory,
    handleApplyHistory,
    removeSearchHistory,
  } = useAnalyticsFiltersContext();

  return (
    <>
      {/* Save filter input */}
      {saveName !== undefined && (
        <div className={styles.sectionPanel}>
          <div className={styles.historySaveRow}>
            <input
              type="text"
              placeholder="输入保存名称"
              className={styles.historyInput}
              value={saveName}
              onChange={e => setSaveName(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  handleSaveFilters();
                }
              }}
            />
            <Button type="primary" onClick={handleSaveFilters} className={styles.sectionButton}>
              保存
            </Button>
            <Button onClick={() => setSaveName('')} className={styles.sectionButton}>
              取消
            </Button>
          </div>
        </div>
      )}

      {/* Filter history */}
      {showHistory && (
        <div className={styles.sectionPanel}>
          <Text strong className={styles.sectionTitleText}>
            筛选历史
          </Text>
          {searchHistory.length > 0 ? (
            <div className={styles.historyList}>
              {searchHistory.slice(0, 5).map(history => (
                <div
                  key={history.id}
                  role="button"
                  tabIndex={0}
                  className={styles.historyItem}
                  onClick={() => handleApplyHistory(history.id)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleApplyHistory(history.id);
                    }
                  }}
                >
                  <div className={styles.historyMeta}>
                    <div className={styles.historyName}>{history.name}</div>
                    <div className={styles.historyDate}>
                      {new Date(history.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                  <Button
                    type="text"
                    size="small"
                    danger
                    className={styles.historyDeleteButton}
                    onClick={e => {
                      e.stopPropagation();
                      removeSearchHistory(history.id);
                      MessageManager.success('历史记录已删除');
                    }}
                  >
                    删除
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <Empty description="暂无筛选历史" className={styles.historyEmpty} />
          )}
        </div>
      )}
    </>
  );
};

export default FilterHistorySection;
