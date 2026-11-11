package org.example.backend.statistics.vo;

import lombok.Data;

/**
 * KPI 数字卡片。
 */
@Data
public class DashboardKpiVO {

    /** mine | all */
    private String scope;

    private Long vmHostCount;

    private Long vmHostRunningCount;

    private Long vmAppCount;

    private Long cpuCoresTotal;

    private Long memoryGbTotal;

    /** 仅 scope=all 时有值 */
    private Long userCount;
}
