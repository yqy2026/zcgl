import React from 'react';
import OwnershipSelect from '@/components/Ownership/OwnershipSelect';

const TestOwnershipSelect: React.FC = () => {
  const handleChange = (value: string | string[], ownerships?: any) => {
    console.log('Selected:', value, ownerships);
  };

  return (
    <div style={{ padding: '24px' }}>
      <h2>测试 OwnershipSelect 组件</h2>
      <div style={{ marginBottom: '16px' }}>
        <h3>单选模式</h3>
        <OwnershipSelect
          placeholder="请选择权属方"
          onChange={handleChange}
          mode="single"
          style={{ width: '300px' }}
        />
      </div>
      <div>
        <h3>多选模式</h3>
        <OwnershipSelect
          placeholder="请选择多个权属方"
          onChange={handleChange}
          mode="multiple"
          style={{ width: '400px' }}
        />
      </div>
    </div>
  );
};

export default TestOwnershipSelect;