/**
 * 侧栏菜单徽标：本月未完成件数 + 档案缺件份数。
 *
 * 原型 v5 侧栏要求：本月（右侧显示未完成件数）、档案（右侧红字「缺 N 份」）。
 * 徽标是辅助信息：请求失败或无数据范围时不显示（页面自身会暴露真实错误，
 * 徽标静默降级不等于声称数字为 0）。
 */

import { useQuery } from '@tanstack/react-query';
import { monthlyWorkbenchService } from '@/services/monthlyWorkbenchService';
import { occupancyReportService } from '@/services/occupancyReportService';
import { archiveMatrixService } from '@/services/archiveMatrixService';

export interface AssetOpsMenuBadges {
  /** 本月未完成件数；null = 尚未加载或不可用 */
  monthlyLeft: number | null;
  /** 档案缺件总份数；null = 尚未加载或不可用 */
  archiveMissing: number | null;
}

export function useAssetOpsMenuBadges(): AssetOpsMenuBadges {
  const partiesQuery = useQuery({
    queryKey: ['occupancy-operator-parties'],
    queryFn: () => occupancyReportService.listOperatorParties(),
  });
  const operatorId = partiesQuery.data?.[0]?.id ?? null;

  const workbenchQuery = useQuery({
    queryKey: ['monthly-workbench', operatorId],
    queryFn: () => monthlyWorkbenchService.overview({ operatorPartyId: operatorId ?? '' }),
    enabled: operatorId != null,
  });

  const archiveQuery = useQuery({
    queryKey: ['archive-completion-badge'],
    queryFn: () => archiveMatrixService.completion({}),
  });

  const monthlyLeft = workbenchQuery.data
    ? Math.max(workbenchQuery.data.progress.total - workbenchQuery.data.progress.done, 0)
    : null;

  const archiveMissing = archiveQuery.data
    ? archiveQuery.data.categories.reduce(
        (sum, category) =>
          category.supported && (category.required ?? 0) > 0
            ? sum + (category.missing ?? 0)
            : sum,
        0,
      )
    : null;

  return { monthlyLeft, archiveMissing };
}
