// 表单验证规则接口
interface FormValidationRule {
  field?: string
  fullField?: string
  type?: string
  validator?: (rule: FormValidationRule, value: unknown) => Promise<void>
}

// Response type for existence check APIs
interface ExistsCheckResponse {
  exists: boolean
}

// 通用验证规则
export const validationRules = {
  // 必填验证
  required: (message?: string) => ({
    required: true,
    message: message || '此字段为必填项'
  }),

  // 邮箱验证
  email: {
    type: 'email' as const,
    message: '请输入有效的邮箱地址'
  },

  // 手机号验证（中国大陆）
  phone: {
    pattern: /^1[3-9]\d{9}$/,
    message: '请输入有效的手机号码'
  },

  // 用户名验证
  username: {
    pattern: /^[a-zA-Z0-9_]{3,20}$/,
    message: '用户名只能包含字母、数字和下划线，长度3-20位'
  },

  // 密码验证
  password: {
    min: 6,
    max: 20,
    message: '密码长度应为6-20位'
  },

  // 强密码验证
  strongPassword: {
    pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$/,
    message: '密码必须包含大小写字母和数字，至少8位'
  },

  // 身份证验证
  idCard: {
    pattern: /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/,
    message: '请输入有效的身份证号码'
  },

  // 数字验证
  number: {
    pattern: /^\d+$/,
    message: '请输入有效的数字'
  },

  // 正数验证
  positiveNumber: {
    pattern: /^[1-9]\d*$/,
    message: '请输入正整数'
  },

  // 非负数验证
  nonNegativeNumber: {
    pattern: /^(0|[1-9]\d*)$/,
    message: '请输入非负整数'
  },

  // 金额验证（最多两位小数）
  amount: {
    pattern: /^\d+(\.\d{1,2})?$/,
    message: '请输入有效的金额，最多两位小数'
  },

  // URL验证
  url: {
    type: 'url' as const,
    message: '请输入有效的URL地址'
  },

  // 角色编码验证
  roleCode: {
    pattern: /^[a-z][a-z0-9_]*$/,
    message: '角色编码必须以小写字母开头，只能包含小写字母、数字和下划线'
  },

  // 组织编码验证
  orgCode: {
    pattern: /^[A-Z0-9_-]+$/,
    message: '组织编码只能包含大写字母、数字、下划线和连字符'
  }
}

// 用户相关验证规则
export const userValidationRules = {
  username: [
    validationRules.required('请输入用户名'),
    validationRules.username
  ],
  email: [
    validationRules.required('请输入邮箱'),
    validationRules.email
  ],
  fullName: [
    validationRules.required('请输入姓名'),
    { min: 2, max: 50, message: '姓名长度应在2-50个字符之间' }
  ],
  phone: [
    validationRules.phone
  ],
  password: [
    validationRules.required('请输入密码'),
    validationRules.password
  ],
  confirmPassword: (passwordFieldName: string = 'password') => ({
    validator: (_: FormValidationRule, value: string) => {
      if (!value) {
        return Promise.reject('请确认密码')
      }
      if (value !== document.querySelector(`[name="${passwordFieldName}"]`)?.getAttribute('value')) {
        return Promise.reject('两次输入的密码不一致')
      }
      return Promise.resolve()
    }
  })
}

// 角色相关验证规则
export const roleValidationRules = {
  roleName: [
    validationRules.required('请输入角色名称'),
    { min: 2, max: 50, message: '角色名称长度应在2-50个字符之间' }
  ],
  roleCode: [
    validationRules.required('请输入角色编码'),
    validationRules.roleCode
  ],
  description: [
    validationRules.required('请输入角色描述'),
    { min: 5, max: 200, message: '角色描述长度应在5-200个字符之间' }
  ]
}

// 组织相关验证规则
export const organizationValidationRules = {
  orgName: [
    validationRules.required('请输入组织名称'),
    { min: 2, max: 100, message: '组织名称长度应在2-100个字符之间' }
  ],
  orgCode: [
    validationRules.required('请输入组织编码'),
    validationRules.orgCode
  ],
  orgType: [
    validationRules.required('请选择组织类型')
  ],
  leaderPhone: [
    validationRules.phone
  ],
  leaderEmail: [
    validationRules.email
  ]
}

// 资产相关验证规则
export const assetValidationRules = {
  propertyName: [
    validationRules.required('请输入物业名称'),
    { min: 2, max: 200, message: '物业名称长度应在2-200个字符之间' }
  ],
  propertyAddress: [
    validationRules.required('请输入物业地址'),
    { min: 5, max: 500, message: '物业地址长度应在5-500个字符之间' }
  ],
  totalArea: [
    validationRules.required('请输入总面积'),
    validationRules.amount
  ],
  rentableArea: [
    validationRules.required('请输入可出租面积'),
    validationRules.amount
  ],
  annualIncome: [
    validationRules.amount
  ],
  annualExpense: [
    validationRules.amount
  ]
}

// 表单自定义验证器
export const customValidators = {
  // 验证两次密码是否一致
  passwordMatch: (getForm: () => { getFieldValue: (field: string) => unknown }) => ({
    validator: (_: FormValidationRule, value: string) => {
      if (!value || getForm().getFieldValue('password') === value) {
        return Promise.resolve()
      }
      return Promise.reject(new Error('两次输入的密码不一致'))
    }
  }),

  // 验证开始日期小于结束日期
  dateRange: (startDateField: string, _endDateField: string) => ({
    validator: (_: FormValidationRule, value: string) => {
      const form = document.querySelector('form')
      if (!form) return Promise.resolve()

      const startDate = (form.querySelector(`[name="${startDateField}"]`) as HTMLInputElement)?.value
      const endDate = value

      if (startDate && endDate && new Date(startDate) >= new Date(endDate)) {
        return Promise.reject(new Error('结束日期必须大于开始日期'))
      }
      return Promise.resolve()
    }
  }),

  // 验证数字范围
  numberRange: (min: number, max: number, message?: string) => ({
    validator: (_: FormValidationRule, value: number) => {
      if (value === undefined || value === null) return Promise.resolve()
      if (value < min || value > max) {
        return Promise.reject(new Error(message || `数值应在${min}-${max}之间`))
      }
      return Promise.resolve()
    }
  }),

  // 验证字符串长度
  stringLength: (min: number, max: number, message?: string) => ({
    validator: (_: FormValidationRule, value: string) => {
      if (!value) return Promise.resolve()
      if (value.length < min || value.length > max) {
        return Promise.reject(new Error(message || `长度应在${min}-${max}个字符之间`))
      }
      return Promise.resolve()
    }
  }),

  // 验证文件类型
  fileType: (allowedTypes: string[]) => ({
    validator: (_: FormValidationRule, file: File) => {
      const fileType = file.type
      const isAllowedType = allowedTypes.some(type => {
        if (type.startsWith('.')) {
          // 扩展名匹配
          return file.name.toLowerCase().endsWith(type.toLowerCase())
        }
        // MIME类型匹配
        return fileType === type
      })

      if (!isAllowedType) {
        return Promise.reject(new Error(`只支持${allowedTypes.join(', ')}格式的文件`))
      }
      return Promise.resolve()
    }
  }),

  // 验证文件大小
  fileSize: (maxSizeMB: number) => ({
    validator: (_: FormValidationRule, file: File) => {
      const maxSizeBytes = maxSizeMB * 1024 * 1024
      if (file.size > maxSizeBytes) {
        return Promise.reject(new Error(`文件大小不能超过${maxSizeMB}MB`))
      }
      return Promise.resolve()
    }
  })
}

// 异步验证器
export const asyncValidators = {
  // 验证用户名唯一性
  uniqueUsername: async (_: FormValidationRule, value: string) => {
    if (!value) return Promise.resolve()

    try {
      // 模拟API调用
      const response = await fetch(`/api/system/users/check-username?username=${value}`)
      const data: ExistsCheckResponse = await response.json() as ExistsCheckResponse

      if (data.exists) {
        return Promise.reject(new Error('用户名已存在'))
      }
      return Promise.resolve()
    } catch {
      // 验证失败时默认通过
      return Promise.resolve()
    }
  },

  // 验证邮箱唯一性
  uniqueEmail: async (_: FormValidationRule, value: string) => {
    if (!value) return Promise.resolve()

    try {
      const response = await fetch(`/api/system/users/check-email?email=${value}`)
      const data: ExistsCheckResponse = await response.json() as ExistsCheckResponse

      if (data.exists) {
        return Promise.reject(new Error('邮箱已被使用'))
      }
      return Promise.resolve()
    } catch {
      return Promise.resolve()
    }
  }
}
