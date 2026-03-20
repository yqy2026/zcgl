import React from 'react';
import { Form, Input, Modal } from 'antd';
import type { FormInstance } from 'antd/es/form';

import type { EnumFieldType } from '@/services/dictionary';
import type { SystemDictionary } from '@/types/dictionary';
import styles from './DictionaryPage.module.css';

interface DictionaryEditorProps {
  open: boolean;
  editingRecord: SystemDictionary | null;
  form: FormInstance<SystemDictionary>;
  activeType: string | undefined;
  activeEnumType: EnumFieldType | undefined;
  onSubmit: () => void;
  onCancel: () => void;
}

const DictionaryEditor: React.FC<DictionaryEditorProps> = ({
  open,
  editingRecord,
  form,
  activeType,
  activeEnumType,
  onSubmit,
  onCancel,
}) => (
  <Modal
    open={open}
    title={editingRecord ? '编辑枚举值' : '新增枚举值'}
    onOk={onSubmit}
    onCancel={onCancel}
    okText="保存"
    cancelText="取消"
    width={600}
  >
    <Form form={form} layout="vertical">
      <Form.Item name="dict_type" label="字典类型">
        <Input disabled placeholder="自动填充" />
      </Form.Item>

      <Form.Item
        name="dict_label"
        label="显示标签"
        rules={[{ required: true, message: '请输入显示标签' }]}
      >
        <Input placeholder="如：已确权、经营性等" />
      </Form.Item>

      <Form.Item
        name="dict_value"
        label="枚举值"
        rules={[{ required: true, message: '请输入枚举值' }]}
      >
        <Input placeholder="如：CONFIRMED、COMMERCIAL等" />
      </Form.Item>

      <Form.Item name="dict_code" label="编码">
        <Input placeholder="可选，如：confirmed、commercial等" />
      </Form.Item>

      <Form.Item name="description" label="描述">
        <Input.TextArea rows={2} placeholder="可选描述信息" />
      </Form.Item>

      <Form.Item name="sort_order" label="排序">
        <Input type="number" placeholder="排序，数值越小越靠前" />
      </Form.Item>

      {activeEnumType != null && (
        <div className={styles.typeInfoBlock}>
          <div>
            <strong>枚举类型：</strong>
            {activeEnumType.name}
          </div>
          <div>
            <strong>类型编码：</strong>
            {activeType}
          </div>
          <div>
            <strong>分类：</strong>
            {activeEnumType.category ?? '未分类'}
          </div>
          {activeEnumType.description != null && (
            <div>
              <strong>描述：</strong>
              {activeEnumType.description}
            </div>
          )}
        </div>
      )}
    </Form>
  </Modal>
);

export default DictionaryEditor;
