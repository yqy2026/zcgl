import { z } from 'zod';

export const assetFormSchema = z
  .object({
    property_name: z.string().min(1, '物业名称不能为空'),
    ownership_entity: z.string().min(1, '权属方不能为空'),
    management_entity: z.string().optional(),
    address: z.string().min(1, '所在地址不能为空'),
    land_area: z.number().min(0, '土地面积不能为负数').optional(),
    actual_property_area: z.number().min(0, '实际房产面积不能为负数').optional(),
    rentable_area: z.number().min(0, '可出租面积不能为负数').optional(),
    rented_area: z.number().min(0, '已出租面积不能为负数').optional(),
    unrented_area: z.number().min(0, '未出租面积不能为负数').optional(),
    non_commercial_area: z.number().min(0, '非经营物业面积不能为负数').optional(),
    ownership_status: z.enum(['已确权', '未确权', '部分确权']),
    certificated_usage: z.string().optional(),
    actual_usage: z.string().optional(),
    business_category: z.string().optional(),
    usage_status: z.enum(['出租', '闲置', '自用', '公房', '其他']),
    is_litigated: z.boolean().optional(),
    property_nature: z.enum(['经营类', '非经营类']),
    business_model: z.string().optional(),
    include_in_occupancy_rate: z.boolean().optional(),
    occupancy_rate: z.string().optional(),
    lease_contract: z.string().optional(),
    current_contract_start_date: z.string().optional(),
    current_contract_end_date: z.string().optional(),
    tenant_name: z.string().optional(),
    ownership_category: z.string().optional(),
    current_lease_contract: z.string().optional(),
    wuyang_project_name: z.string().optional(),
    agreement_start_date: z.string().optional(),
    agreement_end_date: z.string().optional(),
    current_terminal_contract: z.string().optional(),
    description: z.string().optional(),
    notes: z.string().optional(),
  })
  .refine(
    data => {
      // 验证已出租面积不能大于可出租面积
      const rentedArea = data.rented_area;
      const rentableArea = data.rentable_area;
      if (
        rentedArea !== null &&
        rentedArea !== undefined &&
        rentedArea !== 0 &&
        rentableArea !== null &&
        rentableArea !== undefined &&
        rentableArea !== 0
      ) {
        return rentedArea <= rentableArea;
      }
      return true;
    },
    {
      message: '已出租面积不能大于可出租面积',
      path: ['rented_area'],
    }
  )
  .refine(
    data => {
      // 验证合同结束日期必须晚于开始日期
      if (
        data.current_contract_end_date !== null &&
        data.current_contract_end_date !== undefined &&
        data.current_contract_start_date !== null &&
        data.current_contract_start_date !== undefined
      ) {
        return (
          new Date(data.current_contract_end_date) > new Date(data.current_contract_start_date)
        );
      }
      return true;
    },
    {
      message: '合同结束日期必须晚于开始日期',
      path: ['current_contract_end_date'],
    }
  );

export type AssetFormData = z.infer<typeof assetFormSchema>;
