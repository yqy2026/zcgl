/**
 * 字典缓存服务 - 枚举类型缓存与解析
 *
 * @description 管理枚举类型的 ID/Code 双向缓存，支持 TTL 过期与自动刷新
 * @module dictionaryCache
 */

import type { EnumFieldType } from './dictionaryTypes';

/**
 * 枚举类型缓存解析结果
 */
export interface EnumTypeResolveResult {
  id: string;
  code?: string;
}

/**
 * 枚举类型缓存管理器
 *
 * 维护 code→id 和 id→code 的双向映射，带 TTL 自动过期。
 * 当缓存过期时，通过注入的 fetcher 回调刷新数据。
 */
export class EnumTypeCache {
  private readonly ttlMs: number;
  private idByCode = new Map<string, string>();
  private codeById = new Map<string, string>();
  private cachedAt: number | null = null;

  constructor(ttlMs: number = 5 * 60 * 1000) {
    this.ttlMs = ttlMs;
  }

  /**
   * 刷新缓存：用最新的枚举类型列表重建双向映射
   */
  refresh(types: EnumFieldType[]): void {
    this.idByCode.clear();
    this.codeById.clear();

    for (const type of types) {
      if (type.code !== undefined && type.code !== null && type.code !== '') {
        this.idByCode.set(type.code, type.id);
      }
      if (type.id !== undefined && type.id !== null && type.id !== '') {
        this.codeById.set(type.id, type.code);
      }
    }

    this.cachedAt = Date.now();
  }

  /**
   * 检查缓存是否仍在有效期内
   */
  isFresh(): boolean {
    if (this.cachedAt === null) {
      return false;
    }

    return Date.now() - this.cachedAt < this.ttlMs;
  }

  /**
   * 解析枚举类型标识（可能是 ID 或 Code），返回标准化的 { id, code }
   *
   * 解析顺序：
   * 1. 尝试从 code→id 缓存查找
   * 2. 尝试从 id→code 缓存查找
   * 3. 如果缓存过期，调用 fetcher 刷新后重试
   * 4. 都未命中则原样返回
   *
   * @param typeIdOrCode - 枚举类型的 ID 或 Code
   * @param fetcher - 获取最新枚举类型列表的回调（用于缓存过期时刷新）
   */
  async resolve(
    typeIdOrCode: string,
    fetcher: () => Promise<EnumFieldType[]>
  ): Promise<EnumTypeResolveResult> {
    if (typeIdOrCode === '') {
      return { id: typeIdOrCode };
    }

    const cachedId = this.idByCode.get(typeIdOrCode);
    if (cachedId !== undefined) {
      return { id: cachedId, code: typeIdOrCode };
    }

    const cachedCode = this.codeById.get(typeIdOrCode);
    if (cachedCode !== undefined) {
      return { id: typeIdOrCode, code: cachedCode };
    }

    if (this.isFresh() === false) {
      const types = await fetcher();
      // fetcher 内部应调用 refresh()，但防御性地在这里也刷新
      this.refresh(types);

      const matchByCode = types.find(type => type.code === typeIdOrCode);
      if (matchByCode !== undefined) {
        return { id: matchByCode.id, code: matchByCode.code };
      }

      const matchById = types.find(type => type.id === typeIdOrCode);
      if (matchById !== undefined) {
        return { id: matchById.id, code: matchById.code };
      }
    }

    return { id: typeIdOrCode };
  }
}
