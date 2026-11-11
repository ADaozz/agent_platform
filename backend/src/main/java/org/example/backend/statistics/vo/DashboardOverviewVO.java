package org.example.backend.statistics.vo;

import lombok.Data;
import org.example.backend.statistics.vo.chart.CategoryChartVO;
import org.example.backend.statistics.vo.chart.PieChartVO;

/**
 * 仪表盘首屏聚合：KPI + 各图表数据，字段名与 ECharts option 一一对应。
 */
@Data
public class DashboardOverviewVO {

    private DashboardKpiVO kpi;

    /** 虚机 lifecycle_status 构成 */
    private PieChartVO vmByLifecycle;

    /** 虚机 env 构成 */
    private PieChartVO vmByEnv;

    /** 虚机 network_zone 构成 */
    private PieChartVO vmByNetworkZone;

    /** 应用 app_status 构成（mine 时按虚机 owner 过滤） */
    private PieChartVO appByStatus;

    /** 虚机按月新增趋势（折线/柱状） */
    private CategoryChartVO vmCreateTrend;

    /** 仅 scope=all：owner 虚机数 Top10 */
    private CategoryChartVO ownerRank;

    /** 仅 scope=all：宿主机虚机分布 Top10 */
    private CategoryChartVO physicalHostDistribution;
}
