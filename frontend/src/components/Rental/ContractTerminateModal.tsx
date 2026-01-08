/**
 * 合同终止确认对话框
 *
 * @description 用于处理合同提前终止的模态框组件，支持押金退还、抵扣、终止原因设置
 * @module components/Rental/ContractTerminateModal
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Modal,
  Form,
  InputNumber,
  Switch,
  Button,
  Alert,
  Descriptions,
  DatePicker,
  AutoComplete,
  message,
  Space,
} from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { RentContract } from '../../types/rentContract';
import { rentContractService } from '../../services/rentContractService';
import { TERMINATION_REASONS } from '../../constants/reasons';
import { createLogger } from '../../utils/logger';

const logger = createLogger('ContractTerminateModal');

interface ContractTerminateModalProps {
  visible: boolean;
  contract: RentContract;
  onCancel: () => void;
  onSuccess: () => void;
}

interface TerminateFormData {
  termination_date: dayjs.Dayjs;
  refund_deposit: boolean;
  deduction_amount: number;
  termination_reason: string;
}

/**
 * 合同终止确认对话框组件
 */
const ContractTerminateModal: React.FC<ContractTerminateModalProps> = ({
  visible,
  contract,
  onCancel,
  onSuccess,
}) => {
  const [form] = Form.useForm<TerminateFormData>();
  const queryClient = useQueryClient();
  const [showConfirm, setShowConfirm] = useState(false);

  // 实时计算应退押金
  const refundableAmount = useMemo(() => {
    // 确保 total_deposit 是数字类型
    const deposit = typeof contract.total_deposit === 'number'
      ? contract.total_deposit
      : parseFloat(contract.total_deposit as string) || 0;
    const deduction = form.getFieldValue('deduction_amount') || 0;
    return Math.max(0, deposit - deduction);
  }, [contract.total_deposit, form]);

  // 实时获取抵扣金额用于显示
  const deductionAmount = useMemo(() => {
    return form.getFieldValue('deduction_amount') || 0;
  }, [form]);

  // 初始化表单
  useEffect(() => {
    if (visible) {
      form.setFieldsValue({
        termination_date: dayjs(),
        refund_deposit: true,
        deduction_amount: 0,
        termination_reason: undefined,
      });
      setShowConfirm(false);
    }
  }, [visible, form]);

  // 表单验证
  const validateForm = async (): Promise<TerminateFormData> => {
    try {
      const values = await form.validateFields();

      // 验证终止日期不能早于合同开始日期
      const terminationDate = values.termination_date;
      const contractStart = dayjs(contract.start_date);

      if (terminationDate.isBefore(contractStart, 'day')) {
        throw new Error('终止日期不能早于合同开始日期');
      }

      // 验证抵扣金额不能超过押金余额
      if (values.deduction_amount > contract.total_deposit) {
        throw new Error('抵扣金额不能超过押金余额');
      }

      return values;
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      }
      throw error;
    }
  };

  // 终止合同mutation
  const terminateMutation = useMutation({
    mutationFn: (values: TerminateFormData) =>
      rentContractService.terminateContract(
        contract.id,
        values.termination_date.format('YYYY-MM-DD'),
        values.refund_deposit,
        values.deduction_amount,
        values.termination_reason
      ),
    onSuccess: () => {
      message.success('合同已成功终止');
      logger.info('合同终止成功', { contractId: contract.id });
      onSuccess();
    },
    onError: (error: Error) => {
      message.error(`终止失败: ${error.message}`);
      logger.error('合同终止失败', { contractId: contract.id, error });
    },
  });

  // 第一次确认：验证表单
  const handleFirstConfirm = async () => {
    try {
      await validateForm();
      setShowConfirm(true);
    } catch (error) {
      // 表单验证失败，错误信息已在validateForm中处理
    }
  };

  // 第二次确认：真正执行终止
  const handleFinalConfirm = () => {
    const values = form.getFieldsValue();
    terminateMutation.mutate(values);
  };

  // 取消二次确认
  const handleConfirmCancel = () => {
    setShowConfirm(false);
  };

  // 获取合同类型标签
  const getContractTypeLabel = (type: string): string => {
    const typeMap: Record<string, string> = {
      lease_upstream: '承租合同',
      lease_downstream: '租赁合同',
      entrusted: '委托运营协议',
    };
    return typeMap[type] || type;
  };

  return (
    <>
      {/* 主模态框 */}
      <Modal
        title="终止合同"
        open={visible && !showConfirm}
        onCancel={onCancel}
        width={600}
        footer={[
          <Button key="cancel" onClick={onCancel}>
            取消
          </Button>,
          <Button
            key="confirm"
            type="primary"
            danger
            onClick={handleFirstConfirm}
            loading={terminateMutation.isPending}
          >
            确认终止
          </Button>,
        ]}
      >
        {/* 原合同信息摘要 */}
        <Alert
          message="原合同信息"
          description={
            <Descriptions column={2} size="small" style={{ marginTop: 8 }}>
              <Descriptions.Item label="合同编号">
                {contract.contract_number}
              </Descriptions.Item>
              <Descriptions.Item label="合同类型">
                {getContractTypeLabel(contract.contract_type)}
              </Descriptions.Item>
              <Descriptions.Item label="原租期">
                {contract.start_date} ~ {contract.end_date}
              </Descriptions.Item>
              <Descriptions.Item label="押金余额">
                ¥{(typeof contract.total_deposit === 'number'
                  ? contract.total_deposit
                  : parseFloat(contract.total_deposit as string) || 0).toFixed(2)}
              </Descriptions.Item>
            </Descriptions>
          }
          type="info"
          style={{ marginBottom: 16 }}
        />

        {/* 终止表单 */}
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item
            label="终止日期"
            name="termination_date"
            rules={[{ required: true, message: '请选择终止日期' }]}
            tooltip="合同将在该日期正式终止"
          >
            <DatePicker
              style={{ width: '100%' }}
              placeholder="请选择终止日期"
              disabledDate={(current) => {
                // 禁用早于合同开始日期的日期
                const contractStart = dayjs(contract.start_date);
                return current && current.isBefore(contractStart, 'day');
              }}
            />
          </Form.Item>

          <Form.Item
            label="是否退还押金"
            name="refund_deposit"
            valuePropName="checked"
            tooltip="如果不退还，押金将保留在账上"
          >
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>

          <Form.Item
            label="抵扣金额（可选）"
            name="deduction_amount"
            tooltip="可用于扣除违约金、欠租等费用，不能超过押金余额"
          >
            <InputNumber
              min={0}
              max={typeof contract.total_deposit === 'number'
                ? contract.total_deposit
                : parseFloat(contract.total_deposit as string) || 0}
              precision={2}
              style={{ width: '100%' }}
              placeholder="违约金、欠租等抵扣金额"
              addonAfter="元"
            />
          </Form.Item>

          {/* 实时结算显示 */}
          {deductionAmount > 0 && (
            <Alert
              type="info"
              message={
                <>
                  应退押金: <strong>¥{refundableAmount.toFixed(2)}</strong>
                  &nbsp;(押金¥{(typeof contract.total_deposit === 'number'
                    ? contract.total_deposit
                    : parseFloat(contract.total_deposit as string) || 0).toFixed(2)} - 抵扣¥{deductionAmount.toFixed(2)})
                </>
              }
              style={{ marginBottom: 16 }}
            />
          )}

          <Form.Item
            label="终止原因"
            name="termination_reason"
            rules={[{ required: true, message: '请选择或输入终止原因' }]}
            tooltip="将记录在合同历史中"
          >
            <AutoComplete
              options={TERMINATION_REASONS.map(r => ({ value: r.value, label: r.label }))}
              placeholder="选择或输入终止原因"
              filterOption={(inputValue, option) =>
                option!.value.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
              }
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 二次确认模态框 */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
            确认终止合同
          </Space>
        }
        open={showConfirm}
        onOk={handleFinalConfirm}
        onCancel={handleConfirmCancel}
        okText="确认终止"
        cancelText="返回修改"
        okButtonProps={{ danger: true, loading: terminateMutation.isPending }}
        width={500}
      >
        <Alert
          message="此操作不可撤销"
          description={
            <div style={{ marginTop: 8 }}>
              <p>您即将终止以下合同：</p>
              <Descriptions column={1} size="small" bordered style={{ marginTop: 8 }}>
                <Descriptions.Item label="合同编号">
                  {contract.contract_number}
                </Descriptions.Item>
                <Descriptions.Item label="合同类型">
                  {getContractTypeLabel(contract.contract_type)}
                </Descriptions.Item>
                <Descriptions.Item label="终止日期">
                  {form.getFieldValue('termination_date')?.format('YYYY-MM-DD')}
                </Descriptions.Item>
                <Descriptions.Item label="终止原因">
                  {form.getFieldValue('termination_reason')}
                </Descriptions.Item>
                <Descriptions.Item label="押金处理">
                  {form.getFieldValue('refund_deposit') ? (
                    <>
                      应退: <strong>¥{refundableAmount.toFixed(2)}</strong>
                      {deductionAmount > 0 && (
                        <> (抵扣¥{deductionAmount.toFixed(2)})</>
                      )}
                    </>
                  ) : (
                    '不退还'
                  )}
                </Descriptions.Item>
              </Descriptions>
            </div>
          }
          type="warning"
          showIcon
        />
      </Modal>
    </>
  );
};

export default ContractTerminateModal;
