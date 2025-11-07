import React, { useState, useEffect, useCallback } from "react";
import {
  Form,
  Input,
  Select,
  InputNumber,
  DatePicker,
  Button,
  Space,
  Card,
  Row,
  Col,
  Progress,
  Divider,
  Typography,
  Switch,
  message,
  Upload,
  List,
  Tag,
  Tooltip,
} from "antd";
import {
  SaveOutlined,
  ReloadOutlined,
  UploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { DictionarySelect } from "../Dictionary";
import { useDictionaries } from "../../hooks/useDictionary";
import OwnershipSelect from "../Ownership/OwnershipSelect";
import ProjectSelect from "../Project/ProjectSelect";
import GroupedSelectSingle from "../Common/GroupedSelect";
import {
  PropertyNatureGroups,
  UsageStatusGroups,
  OwnershipStatusOptions,
  BusinessModelOptions,
  TenantTypeOptions,
} from "../../utils/enumHelpers";
import { assetService } from "../../services/assetService";
import { rentContractService } from "../../services/rentContractService";
import type { RentContract } from "../../types/rentContract";
import type { UploadFile } from "antd/es/upload/interface";

const { Option } = Select;
const { TextArea } = Input;
const { Title, Text } = Typography;

interface AssetFormProps {
  initialData?: Record<string, unknown>;
  onSubmit?: (data: Record<string, unknown>) => Promise<void>;
  onCancel?: () => void;
  loading?: boolean;
  mode?: "create" | "edit";
}

const AssetForm: React.FC<AssetFormProps> = ({
  initialData,
  onSubmit,
  onCancel,
  loading = false,
  mode = "create",
}) => {
  const [form] = Form.useForm();
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [completionRate, setCompletionRate] = useState(0);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [terminalContractFileList, setTerminalContractFileList] = useState<UploadFile[]>([]);
  const [rentContracts, setRentContracts] = useState<RentContract[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<string>("");
  const [loadingContracts, setLoadingContracts] = useState(false);

  // 批量加载所需的字典数据
  useDictionaries([
    "property_nature",
    "usage_status",
    "ownership_status",
    "ownership_category",
    "business_category",
    "certificated_usage",
    "actual_usage",
    "tenant_type",
    "business_model",
  ]);

  // 接收协议文件上传配置
  const uploadProps = {
    multiple: true,
    accept: ".pdf",
    beforeUpload: (file: File) => {
      const isPDF = file.type === "application/pdf";
      if (!isPDF) {
        message.error("只能上传PDF文件");
        return false;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error("文件大小不能超过10MB");
        return false;
      }
      return false; // 阻止自动上传，等待表单提交时统一处理
    },
    onChange: (info: { fileList: UploadFile[] }) => {
      setFileList(info.fileList);
    },
    fileList: fileList,
  };

  // 终端合同文件上传配置
  const terminalContractUploadProps = {
    multiple: true,
    accept: ".pdf",
    beforeUpload: (file: File) => {
      const isPDF = file.type === "application/pdf";
      if (!isPDF) {
        message.error("只能上传PDF文件");
        return false;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error("文件大小不能超过10MB");
        return false;
      }
      return false; // 阻止自动上传，等待表单提交时统一处理
    },
    onChange: (info: { fileList: UploadFile[] }) => {
      setTerminalContractFileList(info.fileList);
    },
    fileList: terminalContractFileList,
  };

  // 监听表单值变化，计算完成度
  const handleValuesChange = (
    changedValues: Record<string, unknown>,
    allValues: Record<string, unknown>,
  ) => {
    const requiredFields = [
      "property_name",
      "ownership_entity",
      "address",
      "ownership_status",
      "property_nature",
      "usage_status",
    ];

    const filledFields = requiredFields.filter((field) => allValues[field]);
    const rate = (filledFields.length / requiredFields.length) * 100;
    setCompletionRate(rate);

    // 自动计算逻辑
    if (changedValues.rentable_area || changedValues.rented_area) {
      const rentableArea = Number(allValues.rentable_area) || 0;
      const rentedArea = Number(allValues.rented_area) || 0;

      if (rentableArea > 0) {
        const occupancyRate = ((rentedArea / rentableArea) * 100).toFixed(2);
        const unrentedArea = rentableArea - rentedArea;

        form.setFieldsValue({
          occupancy_rate: parseFloat(occupancyRate),
          unrented_area: unrentedArea,
        });
      }
    }
  };

  // 加载租赁合同数据
  const loadRentContracts = useCallback(async (assetId?: string) => {
    if (!assetId) {
      setRentContracts([]);
      return;
    }

    setLoadingContracts(true);
    try {
      const response = await rentContractService.getAssetContracts(assetId);
      setRentContracts(response);
    } catch (error) {
      message.error("加载租赁合同数据失败");
      console.error("加载租赁合同数据失败:", error);
    } finally {
      setLoadingContracts(false);
    }
  }, []);

  // 处理合同选择变化
  const handleContractChange = (contractId: string) => {
    setSelectedContractId(contractId);
    const selectedContract = rentContracts.find((contract) => contract.id === contractId);

    if (selectedContract) {
      // 自动填充租户信息和合同信息
      form.setFieldsValue({
        tenant_name: selectedContract.tenant_name,
        tenant_contact: selectedContract.tenant_contact,
        tenant_type: selectedContract.tenant_id ? "enterprise" : "individual",
        lease_contract_number: selectedContract.contract_number,
        contract_start_date: selectedContract.start_date
          ? dayjs(selectedContract.start_date)
          : undefined,
        contract_end_date: selectedContract.end_date ? dayjs(selectedContract.end_date) : undefined,
        monthly_rent: selectedContract.monthly_rent_base,
        deposit: selectedContract.total_deposit,
      });
    } else {
      // 清空相关字段
      form.setFieldsValue({
        tenant_name: undefined,
        tenant_contact: undefined,
        tenant_type: undefined,
        lease_contract_number: undefined,
        contract_start_date: undefined,
        contract_end_date: undefined,
        monthly_rent: undefined,
        deposit: undefined,
      });
    }
  };

  // 初始化表单数据
  useEffect(() => {
    if (initialData) {
      const formData = {
        ...initialData,
        contract_start_date: initialData.contract_start_date
          ? dayjs(String(initialData.contract_start_date))
          : undefined,
        contract_end_date: initialData.contract_end_date
          ? dayjs(String(initialData.contract_end_date))
          : undefined,
        operation_agreement_start_date: initialData.operation_agreement_start_date
          ? dayjs(String(initialData.operation_agreement_start_date))
          : undefined,
        operation_agreement_end_date: initialData.operation_agreement_end_date
          ? dayjs(String(initialData.operation_agreement_end_date))
          : undefined,
      };
      form.setFieldsValue(formData);

      // 初始化附件列表
      if (initialData.operation_agreement_attachments) {
        const fileNames = String(initialData.operation_agreement_attachments)
          .split(",")
          .filter(Boolean);
        const initialFileList = fileNames.map((name: string, index: number) => ({
          uid: `-${index}`,
          name: name,
          status: "done" as const,
          url: `/assets/attachments/${name}`,
          size: 0,
        }));
        setFileList(initialFileList);
      }

      // 初始化终端合同文件列表
      if (initialData.terminal_contract_files) {
        const fileNames = String(initialData.terminal_contract_files).split(",").filter(Boolean);
        const initialTerminalFileList = fileNames.map((name: string, index: number) => ({
          uid: `terminal-${index}`,
          name: name,
          status: "done" as const,
          url: `/assets/terminal-contracts/${name}`,
          size: 0,
        }));
        setTerminalContractFileList(initialTerminalFileList);
      }
    }
  }, [initialData, form]);

  // 监听资产ID变化，加载相关租赁合同
  useEffect(() => {
    const assetId = String(initialData?.id || form.getFieldValue("id"));
    if (assetId && assetId !== "undefined") {
      loadRentContracts(assetId);
    }
  }, [initialData?.id, form, loadRentContracts]);

  // 监听表单中资产ID变化（编辑模式）
  const handleValuesChangeWithContract = (
    changedValues: Record<string, unknown>,
    allValues: Record<string, unknown>,
  ) => {
    handleValuesChange(changedValues, allValues);

    // 如果资产ID发生变化，重新加载租赁合同
    if (changedValues.id && typeof changedValues.id === "string") {
      loadRentContracts(changedValues.id);
    }
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      // 处理日期字段
      const submitData = {
        ...values,
        contract_start_date: (values.contract_start_date as any)?.format("YYYY-MM-DD"),
        contract_end_date: (values.contract_end_date as any)?.format("YYYY-MM-DD"),
        operation_agreement_start_date: (values.operation_agreement_start_date as any)?.format(
          "YYYY-MM-DD",
        ),
        operation_agreement_end_date: (values.operation_agreement_end_date as any)?.format(
          "YYYY-MM-DD",
        ),
        // 处理附件信息，存储文件名列表
        operation_agreement_attachments: fileList.map((file) => file.name).join(","),
        // 处理终端合同文件信息
        terminal_contract_files: terminalContractFileList.map((file) => file.name).join(","),
      };

      // 提交基本数据
      if (onSubmit) {
        await onSubmit(submitData);
      }

      // 如果是编辑模式且有附件文件，上传附件
      // TODO: 实现附件上传功能
      // if (mode === "edit" && initialData?.id && fileList.length > 0) {
      //   const filesToUpload = fileList.filter((file) => file.originFileObj);
      //   if (filesToUpload.length > 0) {
      //     try {
      //       await assetService.uploadAssetAttachments(
      //         initialData.id,
      //         filesToUpload.map((file) => file.originFileObj as File),
      //       );
      //       message.success("附件上传成功");
      //     } catch {
      //       message.error("附件上传失败，请重试");
      //     }
      //   }
      // }
    } catch {
      message.error("提交失败，请重试");
    }
  };

  const handleReset = () => {
    form.resetFields();
    setCompletionRate(0);
    setFileList([]);
    setTerminalContractFileList([]);
  };

  return (
    <div>
      {/* 完成度指示器 */}
      <Card style={{ marginBottom: "16px" }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Text>表单完成度</Text>
          </Col>
          <Col flex="auto" style={{ marginLeft: "16px" }}>
            <Progress
              percent={completionRate}
              size="small"
              strokeColor={completionRate === 100 ? "#52c41a" : "#1890ff"}
            />
          </Col>
          <Col>
            <Text strong>{completionRate.toFixed(0)}%</Text>
          </Col>
        </Row>
      </Card>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        onValuesChange={handleValuesChangeWithContract}
      >
        {/* 基本信息 */}
        <Card title="基本信息" style={{ marginBottom: "16px" }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="权属方"
                name="ownership_entity"
                rules={[{ required: true, message: "请选择权属方" }]}
              >
                <OwnershipSelect
                  placeholder="请选择权属方"
                  allowClear={false}
                  showCreateButton={true}
                  onChange={(_, ownership) => {
                    // 当选择权属方时，可以自动填充其他相关信息
                    if (ownership) {
                      // 可以在这里添加自动填充逻辑，比如填充联系人信息等
                    }
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="权属类别" name="ownership_category">
                <DictionarySelect dictType="ownership_category" placeholder="请选择权属类别" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="项目名称" name="project_name">
                <ProjectSelect
                  placeholder="请选择项目"
                  allowClear={false}
                  showCreateButton={true}
                  onChange={(value, project) => {
                    // 当选择项目时，可以自动填充其他相关信息
                    if (project) {
                      // 可以在这里添加自动填充逻辑，比如填充项目相关信息
                      // Project selection changed
                    }
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="物业名称"
                name="property_name"
                rules={[{ required: true, message: "请输入物业名称" }]}
              >
                <Input placeholder="请输入物业名称" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="物业地址"
            name="address"
            rules={[{ required: true, message: "请输入物业地址" }]}
          >
            <Input placeholder="请输入详细地址" />
          </Form.Item>
        </Card>

        {/* 面积信息 */}
        <Card title="面积信息" style={{ marginBottom: "16px" }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="土地面积(㎡)" name="land_area">
                <InputNumber placeholder="请输入土地面积" style={{ width: "100%" }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="实际房产面积(㎡)" name="actual_property_area">
                <InputNumber placeholder="请输入实际房产面积" style={{ width: "100%" }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="非经营物业面积(㎡)" name="non_commercial_area">
                <InputNumber placeholder="请输入非经营物业面积" style={{ width: "100%" }} min={0} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="可出租面积(㎡)" name="rentable_area">
                <InputNumber placeholder="请输入可出租面积" style={{ width: "100%" }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="已出租面积(㎡)" name="rented_area">
                <InputNumber placeholder="请输入已出租面积" style={{ width: "100%" }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="未出租面积(㎡)" name="unrented_area">
                <InputNumber placeholder="自动计算" style={{ width: "100%" }} disabled />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 状态信息 */}
        <Card title="状态信息" style={{ marginBottom: "16px" }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="确权状态"
                name="ownership_status"
                rules={[{ required: true, message: "请选择确权状态" }]}
              >
                <GroupedSelectSingle
                  groups={[{ label: "确权状态", options: OwnershipStatusOptions }]}
                  placeholder="请选择确权状态"
                  showGroupLabel={false}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="证载用途" name="certificated_usage">
                <DictionarySelect dictType="certificated_usage" placeholder="请选择证载用途" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="实际用途" name="actual_usage">
                <DictionarySelect dictType="actual_usage" placeholder="请选择实际用途" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="业态类别" name="business_category">
                <DictionarySelect dictType="business_category" placeholder="请选择业态类别" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="使用状态"
                name="usage_status"
                rules={[{ required: true, message: "请选择使用状态" }]}
              >
                <GroupedSelectSingle
                  groups={UsageStatusGroups}
                  placeholder="请选择使用状态"
                  showSearch={true}
                  maxDisplayCount={20}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="是否涉诉" name="is_litigated">
                <Select placeholder="请选择是否涉诉">
                  <Option value={false}>否</Option>
                  <Option value={true}>是</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="物业性质"
                name="property_nature"
                rules={[{ required: true, message: "请选择物业性质" }]}
              >
                <GroupedSelectSingle
                  groups={PropertyNatureGroups}
                  placeholder="请选择物业性质"
                  showSearch={true}
                  maxDisplayCount={25}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="是否计入出租率" name="include_in_occupancy_rate">
                <Select placeholder="请选择">
                  <Option value={true}>是</Option>
                  <Option value={false}>否</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="出租率" name="occupancy_rate">
                <Input placeholder="自动计算" disabled />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 接收信息 */}
        <Card style={{ marginBottom: "16px" }}>
          <Title level={5}>接收信息</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="接收模式" name="business_model">
                <GroupedSelectSingle
                  groups={[{ label: "接收模式", options: BusinessModelOptions }]}
                  placeholder="请选择接收模式"
                  showGroupLabel={false}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="(当前)接收协议开始日期" name="operation_agreement_start_date">
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="(当前)接收协议结束日期" name="operation_agreement_end_date">
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item label="接收协议文件" name="operation_agreement_attachments">
                <div>
                  <Upload {...uploadProps}>
                    <Button icon={<UploadOutlined />}>上传PDF接收协议文件</Button>
                  </Upload>
                  <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
                    支持多文件上传，每个文件不超过10MB，仅支持PDF格式
                  </div>
                  {fileList.length > 0 && (
                    <List
                      size="small"
                      header={<div>已选择的附件</div>}
                      bordered
                      dataSource={fileList}
                      renderItem={(file: UploadFile) => (
                        <List.Item
                          actions={[
                            <Button
                              key="view"
                              type="link"
                              size="small"
                              icon={<EyeOutlined />}
                              onClick={() => {
                                if (file.url) {
                                  window.open(file.url, "_blank");
                                }
                              }}
                            >
                              查看
                            </Button>,
                            <Button
                              key="delete"
                              type="link"
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => {
                                setFileList(fileList.filter((f) => f.uid !== file.uid));
                              }}
                            >
                              删除
                            </Button>,
                          ]}
                        >
                          <List.Item.Meta
                            avatar={<Tag color="blue">PDF</Tag>}
                            title={file.name}
                            description={`文件大小: ${file.size ? (file.size / 1024 / 1024).toFixed(2) + "MB" : "未知"}`}
                          />
                        </List.Item>
                      )}
                      style={{ marginTop: 16 }}
                    />
                  )}
                </div>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 高级选项 */}
        <Card
          title={
            <Space>
              <span>高级选项</span>
              <Switch checked={showAdvanced} onChange={setShowAdvanced} size="small" />
            </Space>
          }
          style={{ marginBottom: "16px" }}
        >
          {showAdvanced && (
            <>
              {/* 租户信息 */}
              <Title level={5}>
                租户信息
                <Tooltip title="租户信息来自合同管理模块，只能查看不能编辑">
                  <InfoCircleOutlined style={{ marginLeft: 8, color: "#666" }} />
                </Tooltip>
              </Title>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item label="选择租赁合同" name="selected_contract_id">
                    <Select
                      placeholder="请选择租赁合同"
                      allowClear
                      loading={loadingContracts}
                      onChange={handleContractChange}
                      optionFilterProp="children"
                      showSearch
                      filterOption={(input, option) =>
                        (option?.children as unknown as string)
                          ?.toLowerCase()
                          .includes(input.toLowerCase())
                      }
                    >
                      {rentContracts.map((contract) => (
                        <Option key={contract.id} value={contract.id}>
                          {contract.contract_number} - {contract.tenant_name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item label="租户名称" name="tenant_name">
                    <Input placeholder="自动从合同获取" readOnly />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="租户联系方式" name="tenant_contact">
                    <Input placeholder="自动从合同获取" readOnly />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="租户类型" name="tenant_type">
                    <GroupedSelectSingle
                      groups={[{ label: "租户类型", options: TenantTypeOptions }]}
                      placeholder="自动从合同获取"
                      disabled
                      showGroupLabel={false}
                    />
                  </Form.Item>
                </Col>
              </Row>

              {/* 合同信息 */}
              <Title level={5}>
                合同信息
                <Tooltip title="合同信息来自合同管理模块，只能查看不能编辑">
                  <InfoCircleOutlined style={{ marginLeft: 8, color: "#666" }} />
                </Tooltip>
              </Title>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item label="租赁合同编号" name="lease_contract_number">
                    <Input placeholder="自动从合同获取" readOnly />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="合同开始日期" name="contract_start_date">
                    <DatePicker style={{ width: "100%" }} disabled />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="合同结束日期" name="contract_end_date">
                    <DatePicker style={{ width: "100%" }} disabled />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item label="月租金(元)" name="monthly_rent">
                    <InputNumber
                      placeholder="自动从合同获取"
                      style={{ width: "100%" }}
                      min={0}
                      precision={2}
                      disabled
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="押金(元)" name="deposit">
                    <InputNumber
                      placeholder="自动从合同获取"
                      style={{ width: "100%" }}
                      min={0}
                      precision={2}
                      disabled
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item label="是否分租/转租" name="is_sublease">
                    <Select placeholder="请选择" disabled>
                      <Option value={false}>否</Option>
                      <Option value={true}>是</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item label="分租/转租备注" name="sublease_notes">
                    <TextArea rows={2} placeholder="请输入分租/转租备注" />
                  </Form.Item>
                </Col>
              </Row>

              {/* 终端合同文件 */}
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item label="终端合同文件" name="terminal_contract_files">
                    <div>
                      <Upload {...terminalContractUploadProps}>
                        <Button icon={<UploadOutlined />}>上传PDF终端合同文件</Button>
                      </Upload>
                      <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
                        支持多文件上传，每个文件不超过10MB，仅支持PDF格式
                      </div>
                      {terminalContractFileList.length > 0 && (
                        <List
                          size="small"
                          header={<div>已选择的终端合同文件</div>}
                          bordered
                          dataSource={terminalContractFileList}
                          renderItem={(file: UploadFile) => (
                            <List.Item
                              actions={[
                                <Button
                                  key="view"
                                  type="link"
                                  size="small"
                                  icon={<EyeOutlined />}
                                  onClick={() => {
                                    if (file.url) {
                                      window.open(file.url, "_blank");
                                    }
                                  }}
                                >
                                  查看
                                </Button>,
                                <Button
                                  key="delete"
                                  type="link"
                                  size="small"
                                  danger
                                  icon={<DeleteOutlined />}
                                  onClick={() => {
                                    setTerminalContractFileList(
                                      terminalContractFileList.filter((f) => f.uid !== file.uid),
                                    );
                                  }}
                                >
                                  删除
                                </Button>,
                              ]}
                            >
                              <List.Item.Meta
                                avatar={<Tag color="green">PDF</Tag>}
                                title={file.name}
                                description={`文件大小: ${file.size ? (file.size / 1024 / 1024).toFixed(2) + "MB" : "未知"}`}
                              />
                            </List.Item>
                          )}
                          style={{ marginTop: 16 }}
                        />
                      )}
                    </div>
                  </Form.Item>
                </Col>
              </Row>

              <Divider />

              {/* 备注信息 */}
              <Title level={5}>备注信息</Title>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="管理责任人(网格员)" name="manager_name">
                    <Input placeholder="请输入管理责任人" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="其他备注" name="notes">
                    <TextArea rows={4} placeholder="请输入其他备注信息" />
                  </Form.Item>
                </Col>
              </Row>
            </>
          )}
        </Card>

        {/* 操作按钮 */}
        <Card>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading} icon={<SaveOutlined />}>
              {mode === "create" ? "创建资产" : "更新资产"}
            </Button>
            <Button onClick={onCancel || (() => {})}>取消</Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置
            </Button>
          </Space>
        </Card>
      </Form>
    </div>
  );
};

export default AssetForm;
