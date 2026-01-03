import React from 'react';
import { Typography, Button, Empty, message } from 'antd';
import { useAnalyticsFiltersContext } from './FiltersContext';

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
        removeSearchHistory
    } = useAnalyticsFiltersContext();

    return (
        <>
            {/* Save filter input */}
            {saveName !== undefined && (
                <div style={{ marginBottom: 16, padding: '12px', background: '#f5f5f5', borderRadius: 6 }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <input
                            type="text"
                            placeholder="输入保存名称"
                            value={saveName}
                            onChange={(e) => setSaveName(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    handleSaveFilters();
                                }
                            }}
                            style={{ flex: 1, padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }}
                            autoFocus
                        />
                        <Button type="primary" onClick={handleSaveFilters}>
                            保存
                        </Button>
                        <Button onClick={() => setSaveName('')}>
                            取消
                        </Button>
                    </div>
                </div>
            )}

            {/* Filter history */}
            {showHistory && (
                <div style={{ marginBottom: 16, padding: '12px', background: '#f5f5f5', borderRadius: 6 }}>
                    <Text strong style={{ marginBottom: 8, display: 'block' }}>筛选历史</Text>
                    {searchHistory.length > 0 ? (
                        <div>
                            {searchHistory.slice(0, 5).map(history => (
                                <div
                                    key={history.id}
                                    style={{
                                        padding: '8px 12px',
                                        background: 'white',
                                        border: '1px solid #e8e8e8',
                                        borderRadius: 4,
                                        marginBottom: 8,
                                        cursor: 'pointer',
                                        transition: 'all 0.2s',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center'
                                    }}
                                    onClick={() => handleApplyHistory(history.id)}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.backgroundColor = '#f0f0f0';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.backgroundColor = 'white';
                                    }}
                                >
                                    <div>
                                        <div style={{ fontWeight: 'bold' }}>{history.name}</div>
                                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                                            {new Date(history.createdAt).toLocaleDateString()}
                                        </div>
                                    </div>
                                    <Button
                                        type="text"
                                        size="small"
                                        danger
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            removeSearchHistory(history.id);
                                            message.success('历史记录已删除');
                                        }}
                                    >
                                        删除
                                    </Button>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <Empty description="暂无筛选历史" imageStyle={{ height: 60 }} />
                    )}
                </div>
            )}
        </>
    );
};

export default FilterHistorySection;
