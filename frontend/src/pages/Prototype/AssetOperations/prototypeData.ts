export type WorkId = 'collection-01' | 'leasing-01' | 'right-01' | 'cash-01' | 'property-01';

export type WorkTone = 'urgent' | 'attention' | 'normal';

export interface WorkItem {
  id: WorkId;
  kind: '催收' | '招商' | '权属' | '收款' | '物业';
  title: string;
  project: string;
  region: string;
  address: string;
  space: string;
  owner: string;
  due: string;
  tone: WorkTone;
  reason: string;
  nextAction: string;
  evidence: string;
}

export interface ProjectSummary {
  name: string;
  region: string;
  address: string;
  owner: string;
  spaces: number;
  openTasks: number;
  note: string;
}

export const workItems: WorkItem[] = [
  {
    id: 'collection-01',
    kind: '催收',
    title: '确认启辰科技欠款处置进度',
    project: '东城产业园',
    region: '东部片区',
    address: '环市东路 418 号',
    space: 'A301、车位 P18',
    owner: '李明',
    due: '已逾期 2 天',
    tone: 'urgent',
    reason: '欠款 18.60 万元，尚未留下本周处理证据。',
    nextAction: '记录联系结果，并明确下一次跟进日期',
    evidence: '上次记录：5 月 20 日电话承诺付款',
  },
  {
    id: 'leasing-01',
    kind: '招商',
    title: '完成 A301 正式报价',
    project: '东城产业园',
    region: '东部片区',
    address: '环市东路 418 号',
    space: '2 号楼 A301',
    owner: '李明',
    due: '今天 17:00',
    tone: 'attention',
    reason: '客户需求已明确，当前报价 85 元/㎡/月，高于底价。',
    nextAction: '确认客户主体后发送正式报价',
    evidence: '客户意向书已归档',
  },
  {
    id: 'right-01',
    kind: '权属',
    title: '确认仓库 07 的可经营边界',
    project: '西港仓储点',
    region: '西部片区',
    address: '港前路 72 号',
    space: '仓库 07',
    owner: '刘强',
    due: '明天',
    tone: 'attention',
    reason: '消防验收材料缺失，当前不能进入正式招商。',
    nextAction: '上传消防整改结论并标记可经营范围',
    evidence: '现场照片 6 张，整改通知书 1 份',
  },
  {
    id: 'cash-01',
    kind: '收款',
    title: '确认一笔银行流水匹配',
    project: '北站商业街',
    region: '北部片区',
    address: '站前横路 19 号',
    space: 'B105',
    owner: '王芳',
    due: '今天',
    tone: 'normal',
    reason: '银行到账 96,900.00 元，系统已匹配到对应账单。',
    nextAction: '出纳确认匹配并更新实收',
    evidence: '流水日期 5 月 23 日，尾号 4821',
  },
  {
    id: 'property-01',
    kind: '物业',
    title: '安排漏水整改复检',
    project: '河西社区商铺',
    region: '西部片区',
    address: '河西路 116 号',
    space: '沿街 03 号铺',
    owner: '陈敏',
    due: '周五',
    tone: 'normal',
    reason: '施工方已反馈完成，需要物业人员现场留证。',
    nextAction: '安排同片区巡检并上传复检照片',
    evidence: '整改工单 WY-240521-09',
  },
];

export const projects: ProjectSummary[] = [
  {
    name: '东城产业园',
    region: '东部片区',
    address: '环市东路 418 号',
    owner: '李明',
    spaces: 6,
    openTasks: 2,
    note: '1 笔催收、1 个报价待处理',
  },
  {
    name: '西港仓储点',
    region: '西部片区',
    address: '港前路 72 号',
    owner: '刘强',
    spaces: 3,
    openTasks: 1,
    note: '消防材料待补',
  },
  {
    name: '北站商业街',
    region: '北部片区',
    address: '站前横路 19 号',
    owner: '王芳',
    spaces: 5,
    openTasks: 1,
    note: '1 笔流水待确认',
  },
  {
    name: '河西社区商铺',
    region: '西部片区',
    address: '河西路 116 号',
    owner: '陈敏',
    spaces: 2,
    openTasks: 1,
    note: '漏水整改待复检',
  },
  {
    name: '南湖停车场',
    region: '南部片区',
    address: '南湖大道 8 号',
    owner: '周凯',
    spaces: 8,
    openTasks: 0,
    note: '运行正常',
  },
  {
    name: '江湾办公点',
    region: '东部片区',
    address: '江湾路 33 号',
    owner: '李明',
    spaces: 4,
    openTasks: 0,
    note: '运行正常',
  },
  {
    name: '高新孵化点',
    region: '北部片区',
    address: '科创路 6 号',
    owner: '王芳',
    spaces: 7,
    openTasks: 0,
    note: '运行正常',
  },
];
