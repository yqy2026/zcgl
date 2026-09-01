import { useState } from 'react';
import { CheckOutlined, RightOutlined, SearchOutlined } from '@ant-design/icons';
import type { ProjectSummary } from '../prototypeData';
import styles from '../AssetOperationsPrototype.module.css';

interface VariantCProps {
  projects: ProjectSummary[];
  selectedProject: string;
  issueOnly: boolean;
  onProjectChange: (name: string) => void;
  onIssueOnlyChange: (value: boolean) => void;
}

export default function VariantC({
  projects,
  selectedProject,
  issueOnly,
  onProjectChange,
  onIssueOnlyChange,
}: VariantCProps) {
  const [query, setQuery] = useState('');
  const normalizedQuery = query.trim().toLowerCase();
  const visibleProjects = projects.filter(project => {
    if (issueOnly && project.openTasks === 0) {
      return false;
    }
    if (normalizedQuery === '') {
      return true;
    }
    return `${project.name}${project.region}${project.address}${project.owner}`
      .toLowerCase()
      .includes(normalizedQuery);
  });

  return (
    <div className={styles.directoryPage}>
      <header className={styles.directoryLead}>
        <div>
          <h1>运营项目</h1>
          <p>86 个小项目不做 86 个驾驶舱。搜索、定位、进入即可。</p>
        </div>
        <span>
          <strong>86</strong> 个项目 · <strong>312</strong> 个空间
        </span>
      </header>

      <div className={styles.directoryToolbar}>
        <label className={styles.directorySearch}>
          <SearchOutlined aria-hidden="true" />
          <input
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="搜索项目、区域、地址或负责人"
            aria-label="搜索运营项目"
          />
        </label>
        <label className={styles.issueToggle}>
          <input
            type="checkbox"
            checked={issueOnly}
            onChange={event => onIssueOnlyChange(event.target.checked)}
          />
          只看有待办的项目
        </label>
      </div>

      <div className={styles.directoryMeta}>
        <span>显示 {visibleProjects.length} 个演示项目</span>
        <span>按待办优先排序</span>
      </div>

      <ul className={styles.projectList}>
        {visibleProjects.map(project => {
          const isSelected = project.name === selectedProject;
          return (
            <li key={project.name} className={styles.projectEntry}>
              <button
                type="button"
                className={isSelected ? styles.projectRowSelected : styles.projectRow}
                onClick={() => onProjectChange(project.name)}
                aria-expanded={isSelected}
              >
                <span className={styles.projectIdentity}>
                  <strong>{project.name}</strong>
                  <small>
                    {project.region} · {project.address}
                  </small>
                </span>
                <span>
                  <strong>{project.spaces}</strong>
                  <small>空间</small>
                </span>
                <span>
                  <strong>{project.owner}</strong>
                  <small>负责人</small>
                </span>
                <span className={project.openTasks > 0 ? styles.projectIssue : styles.projectClear}>
                  {project.openTasks > 0 ? (
                    `${project.openTasks} 项待办`
                  ) : (
                    <>
                      <CheckOutlined /> 正常
                    </>
                  )}
                </span>
                <RightOutlined className={styles.rowChevron} aria-hidden="true" />
              </button>

              {isSelected ? (
                <div className={styles.projectDetail}>
                  <span>
                    <small>当前情况</small>
                    <strong>{project.note}</strong>
                  </span>
                  <span>
                    <small>项目范围</small>
                    <strong>
                      {project.spaces} 个空间 · {project.address}
                    </strong>
                  </span>
                  <button type="button" className={styles.quietAction}>
                    进入项目
                  </button>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      {visibleProjects.length === 0 ? (
        <div className={styles.emptyState}>没有符合条件的项目，请更换关键词或取消筛选。</div>
      ) : null}
    </div>
  );
}
