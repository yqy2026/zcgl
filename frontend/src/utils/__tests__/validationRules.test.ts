/**
 * 验证规则测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

import {
  validationRules,
  userValidationRules,
  roleValidationRules,
  organizationValidationRules,
  assetValidationRules,
  customValidators,
  asyncValidators,
} from '../validationRules';

describe('validationRules', () => {
  describe('required', () => {
    it('应该返回必填规则对象', () => {
      const rule = validationRules.required();
      expect(rule.required).toBe(true);
      expect(rule.message).toBe('此字段为必填项');
    });

    it('应该支持自定义消息', () => {
      const rule = validationRules.required('请填写用户名');
      expect(rule.message).toBe('请填写用户名');
    });
  });

  describe('email', () => {
    it('应该有正确的类型和消息', () => {
      expect(validationRules.email.type).toBe('email');
      expect(validationRules.email.message).toBe('请输入有效的邮箱地址');
    });
  });

  describe('phone', () => {
    it('应该匹配有效的手机号', () => {
      expect(validationRules.phone.pattern.test('13800138000')).toBe(true);
      expect(validationRules.phone.pattern.test('15912345678')).toBe(true);
    });

    it('应该拒绝无效的手机号', () => {
      expect(validationRules.phone.pattern.test('12345678901')).toBe(false);
      expect(validationRules.phone.pattern.test('1380013800')).toBe(false);
      expect(validationRules.phone.pattern.test('138001380001')).toBe(false);
    });
  });

  describe('username', () => {
    it('应该匹配有效的用户名', () => {
      expect(validationRules.username.pattern.test('user123')).toBe(true);
      expect(validationRules.username.pattern.test('test_user')).toBe(true);
      expect(validationRules.username.pattern.test('abc')).toBe(true);
    });

    it('应该拒绝无效的用户名', () => {
      expect(validationRules.username.pattern.test('ab')).toBe(false);
      expect(validationRules.username.pattern.test('user@name')).toBe(false);
      expect(validationRules.username.pattern.test('用户名')).toBe(false);
    });
  });

  describe('password', () => {
    it('应该有正确的长度限制', () => {
      expect(validationRules.password.min).toBe(6);
      expect(validationRules.password.max).toBe(20);
    });
  });

  describe('strongPassword', () => {
    it('应该匹配强密码', () => {
      expect(validationRules.strongPassword.pattern.test('Abc12345')).toBe(true);
      expect(validationRules.strongPassword.pattern.test('Password1')).toBe(true);
    });

    it('应该拒绝弱密码', () => {
      expect(validationRules.strongPassword.pattern.test('abc12345')).toBe(false);
      expect(validationRules.strongPassword.pattern.test('ABCD1234')).toBe(false);
      expect(validationRules.strongPassword.pattern.test('Abcdefgh')).toBe(false);
    });
  });

  describe('idCard', () => {
    it('应该匹配有效的身份证号', () => {
      expect(validationRules.idCard.pattern.test('110101199001011234')).toBe(true);
      expect(validationRules.idCard.pattern.test('11010119900101123X')).toBe(true);
    });

    it('应该拒绝无效的身份证号', () => {
      expect(validationRules.idCard.pattern.test('12345678901234567')).toBe(false);
      expect(validationRules.idCard.pattern.test('1101011990010112345')).toBe(false);
    });
  });

  describe('number', () => {
    it('应该匹配数字', () => {
      expect(validationRules.number.pattern.test('123')).toBe(true);
      expect(validationRules.number.pattern.test('0')).toBe(true);
    });

    it('应该拒绝非数字', () => {
      expect(validationRules.number.pattern.test('abc')).toBe(false);
      expect(validationRules.number.pattern.test('12.34')).toBe(false);
    });
  });

  describe('positiveNumber', () => {
    it('应该匹配正整数', () => {
      expect(validationRules.positiveNumber.pattern.test('1')).toBe(true);
      expect(validationRules.positiveNumber.pattern.test('123')).toBe(true);
    });

    it('应该拒绝零和负数', () => {
      expect(validationRules.positiveNumber.pattern.test('0')).toBe(false);
      expect(validationRules.positiveNumber.pattern.test('-1')).toBe(false);
    });
  });

  describe('amount', () => {
    it('应该匹配有效金额', () => {
      expect(validationRules.amount.pattern.test('100')).toBe(true);
      expect(validationRules.amount.pattern.test('100.5')).toBe(true);
      expect(validationRules.amount.pattern.test('100.50')).toBe(true);
    });

    it('应该拒绝超过两位小数的金额', () => {
      expect(validationRules.amount.pattern.test('100.123')).toBe(false);
    });
  });

  describe('roleCode', () => {
    it('应该匹配有效的角色编码', () => {
      expect(validationRules.roleCode.pattern.test('admin')).toBe(true);
      expect(validationRules.roleCode.pattern.test('super_admin')).toBe(true);
      expect(validationRules.roleCode.pattern.test('role123')).toBe(true);
    });

    it('应该拒绝无效的角色编码', () => {
      expect(validationRules.roleCode.pattern.test('Admin')).toBe(false);
      expect(validationRules.roleCode.pattern.test('123role')).toBe(false);
    });
  });

  describe('orgCode', () => {
    it('应该匹配有效的组织编码', () => {
      expect(validationRules.orgCode.pattern.test('ORG001')).toBe(true);
      expect(validationRules.orgCode.pattern.test('DEPT-01')).toBe(true);
    });

    it('应该拒绝小写字母', () => {
      expect(validationRules.orgCode.pattern.test('org001')).toBe(false);
    });
  });
});

describe('userValidationRules', () => {
  it('应该有用户名规则', () => {
    expect(userValidationRules.username).toHaveLength(2);
  });

  it('应该有邮箱规则', () => {
    expect(userValidationRules.email).toHaveLength(2);
  });

  it('应该有姓名规则', () => {
    expect(userValidationRules.fullName).toHaveLength(2);
  });

  it('应该有手机号规则', () => {
    expect(userValidationRules.phone).toHaveLength(1);
  });

  it('应该有密码规则', () => {
    expect(userValidationRules.password).toHaveLength(2);
  });

  it('应该有确认密码验证器', () => {
    const rule = userValidationRules.confirmPassword('password');
    expect(rule.validator).toBeDefined();
  });
});

describe('roleValidationRules', () => {
  it('应该有角色名称规则', () => {
    expect(roleValidationRules.roleName).toHaveLength(2);
  });

  it('应该有角色编码规则', () => {
    expect(roleValidationRules.roleCode).toHaveLength(2);
  });

  it('应该有描述规则', () => {
    expect(roleValidationRules.description).toHaveLength(2);
  });
});

describe('organizationValidationRules', () => {
  it('应该有组织名称规则', () => {
    expect(organizationValidationRules.orgName).toHaveLength(2);
  });

  it('应该有组织编码规则', () => {
    expect(organizationValidationRules.orgCode).toHaveLength(2);
  });

  it('应该有组织类型规则', () => {
    expect(organizationValidationRules.orgType).toHaveLength(1);
  });
});

describe('assetValidationRules', () => {
  it('应该有物业名称规则', () => {
    expect(assetValidationRules.propertyName).toHaveLength(2);
  });

  it('应该有物业地址规则', () => {
    expect(assetValidationRules.propertyAddress).toHaveLength(2);
  });

  it('应该有面积规则', () => {
    expect(assetValidationRules.totalArea).toHaveLength(2);
    expect(assetValidationRules.rentableArea).toHaveLength(2);
  });
});

describe('customValidators', () => {
  describe('passwordMatch', () => {
    it('应该创建密码匹配验证器', () => {
      const mockForm = { getFieldValue: vi.fn().mockReturnValue('password123') };
      const validator = customValidators.passwordMatch(() => mockForm);
      expect(validator.validator).toBeDefined();
    });

    it('应该通过匹配的密码', async () => {
      const mockForm = { getFieldValue: vi.fn().mockReturnValue('password123') };
      const validator = customValidators.passwordMatch(() => mockForm);
      await expect(validator.validator({}, 'password123')).resolves.toBeUndefined();
    });

    it('应该拒绝不匹配的密码', async () => {
      const mockForm = { getFieldValue: vi.fn().mockReturnValue('password123') };
      const validator = customValidators.passwordMatch(() => mockForm);
      await expect(validator.validator({}, 'differentPassword')).rejects.toThrow(
        '两次输入的密码不一致'
      );
    });
  });

  describe('numberRange', () => {
    it('应该通过范围内的数字', async () => {
      const validator = customValidators.numberRange(1, 100);
      await expect(validator.validator({}, 50)).resolves.toBeUndefined();
    });

    it('应该拒绝范围外的数字', async () => {
      const validator = customValidators.numberRange(1, 100);
      await expect(validator.validator({}, 150)).rejects.toThrow('数值应在1-100之间');
    });

    it('应该支持自定义消息', async () => {
      const validator = customValidators.numberRange(1, 100, '自定义消息');
      await expect(validator.validator({}, 150)).rejects.toThrow('自定义消息');
    });

    it('应该忽略 undefined', async () => {
      const validator = customValidators.numberRange(1, 100);
      await expect(validator.validator({}, undefined as unknown as number)).resolves.toBeUndefined();
    });
  });

  describe('stringLength', () => {
    it('应该通过正确长度的字符串', async () => {
      const validator = customValidators.stringLength(2, 10);
      await expect(validator.validator({}, 'hello')).resolves.toBeUndefined();
    });

    it('应该拒绝太短的字符串', async () => {
      const validator = customValidators.stringLength(5, 10);
      await expect(validator.validator({}, 'hi')).rejects.toThrow('长度应在5-10个字符之间');
    });

    it('应该拒绝太长的字符串', async () => {
      const validator = customValidators.stringLength(2, 5);
      await expect(validator.validator({}, 'hello world')).rejects.toThrow('长度应在2-5个字符之间');
    });

    it('应该忽略空字符串', async () => {
      const validator = customValidators.stringLength(2, 10);
      await expect(validator.validator({}, '')).resolves.toBeUndefined();
    });
  });

  describe('fileType', () => {
    it('应该通过允许的文件类型', async () => {
      const validator = customValidators.fileType(['image/png', '.jpg']);
      const file = new File([''], 'test.png', { type: 'image/png' });
      await expect(validator.validator({}, file)).resolves.toBeUndefined();
    });

    it('应该通过允许的扩展名', async () => {
      const validator = customValidators.fileType(['.pdf']);
      const file = new File([''], 'document.pdf', { type: 'application/pdf' });
      await expect(validator.validator({}, file)).resolves.toBeUndefined();
    });

    it('应该拒绝不允许的文件类型', async () => {
      const validator = customValidators.fileType(['.pdf']);
      const file = new File([''], 'image.png', { type: 'image/png' });
      await expect(validator.validator({}, file)).rejects.toThrow('只支持.pdf格式的文件');
    });
  });

  describe('fileSize', () => {
    it('应该通过小于限制的文件', async () => {
      const validator = customValidators.fileSize(5);
      const file = new File(['x'.repeat(1024)], 'small.txt');
      await expect(validator.validator({}, file)).resolves.toBeUndefined();
    });

    it('应该拒绝大于限制的文件', async () => {
      const validator = customValidators.fileSize(0.001);
      const file = new File(['x'.repeat(10000)], 'large.txt');
      await expect(validator.validator({}, file)).rejects.toThrow('文件大小不能超过0.001MB');
    });
  });
});

describe('asyncValidators', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('uniqueUsername', () => {
    it('应该通过空值', async () => {
      await expect(asyncValidators.uniqueUsername({}, '')).resolves.toBeUndefined();
    });

    it('应该在用户名存在时拒绝', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve({ exists: true }),
      });

      await expect(asyncValidators.uniqueUsername({}, 'existingUser')).rejects.toThrow(
        '用户名已存在'
      );
    });

    it('应该在用户名不存在时通过', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve({ exists: false }),
      });

      await expect(asyncValidators.uniqueUsername({}, 'newUser')).resolves.toBeUndefined();
    });

    it('应该在 API 错误时通过', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(asyncValidators.uniqueUsername({}, 'testUser')).resolves.toBeUndefined();
    });
  });

  describe('uniqueEmail', () => {
    it('应该通过空值', async () => {
      await expect(asyncValidators.uniqueEmail({}, '')).resolves.toBeUndefined();
    });

    it('应该在邮箱存在时拒绝', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve({ exists: true }),
      });

      await expect(asyncValidators.uniqueEmail({}, 'existing@example.com')).rejects.toThrow(
        '邮箱已被使用'
      );
    });

    it('应该在邮箱不存在时通过', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve({ exists: false }),
      });

      await expect(asyncValidators.uniqueEmail({}, 'new@example.com')).resolves.toBeUndefined();
    });
  });
});
