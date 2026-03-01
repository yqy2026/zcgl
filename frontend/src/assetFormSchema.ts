import { z } from 'zod';

export const assetFormSchema = z
  .object({
    property_name: z.string().min(1, '物业名称不能为空'),
    owner_party_id: z.string().min(1, '权属主体不能为空'),
    manager_party_id: z.string().optional(),
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
    ownership_category: z.string().optional(),
    project_name: z.string().optional(),
    operation_agreement_start_date: z.string().optional(),
    operation_agreement_end_date: z.string().optional(),
    operation_agreement_attachments: z.string().optional(),
    terminal_contract_files: z.string().optional(),
    notes: z.string().optional(),
  })
  .refine(
    data => {
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
  );

export type AssetFormData = z.infer<typeof assetFormSchema>;
